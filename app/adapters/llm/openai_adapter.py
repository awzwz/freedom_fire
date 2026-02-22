"""OpenAI adapter — implements LLMPort using the OpenAI API."""

from __future__ import annotations

import json
import logging
import re

try:
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore

from app.application.ports.llm_port import LLMPort
from app.config import settings
from app.domain.entities.ai_analysis import AIAnalysis
from app.domain.value_objects.enums import Language, Sentiment, TicketType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert ticket classifier for a financial services company (Freedom Broker, Kazakhstan).

Analyze the customer ticket and return a JSON object with exactly these fields:

{
  "ticket_type": one of ["Жалоба", "Смена данных", "Консультация", "Претензия", "Неработоспособность приложения", "Мошеннические действия", "Спам"],
  "sentiment": one of ["Позитивный", "Нейтральный", "Негативный"],
  "priority_score": integer 1-10 (10 = most urgent),
  "language": one of ["RU", "KZ", "ENG"],
  "summary": "Provide a concise summary of the issue (1-2 sentences) in the same language as the ticket. CRITICAL: You MUST include a concrete, actionable recommendation for the manager at the end of the summary. For example: 'Action: Contact the client to verify their identity.' or 'Action: Create a technical support ticket for the buggy application.'"
}

Rules:
- Detect the language of the ticket text.
- Classify the ticket type based on content.

SENTIMENT GUIDELINES (follow carefully):

  Позитивный — the customer expresses gratitude, satisfaction, or a positive attitude.
    Examples:
    * "Спасибо за быструю помощь! Всё решили оперативно."
    * "Благодарю за консультацию, всё понятно."
    * "Отлично, приложение заработало, спасибо!"
    * "Доволен обслуживанием, всё супер."

  Негативный — the customer expresses anger, frustration, urgency, threats, or dissatisfaction.
    Examples:
    * "Срочно разблокируйте мой счёт!"
    * "Мошенники списали деньги, верните немедленно!"
    * "Ужасное обслуживание, буду жаловаться в прокуратуру."
    * "Приложение не работает уже 3 дня, это недопустимо."

  Нейтральный — factual request or question without strong emotion.
    Examples:
    * "Подскажите, как изменить номер телефона в профиле?"
    * "Хочу узнать условия по брокерскому счёту."
    * "Прошу обновить мои паспортные данные."
    * "Не могу войти в приложение, выдает ошибку, помогите разобраться."

- IMPORTANT: obvious ads/promotions with links, product offers, bulk sales, "специальные цены", etc. must be classified as "Спам" with priority_score=1.
- IMPORTANT: If the customer is calmly reporting a bug, error, or login issue without using aggressive or frustrated language, classify the sentiment as 'Нейтральный'. The presence of words like 'ошибка' (error) or 'не могу войти' (cannot login) does NOT automatically make it 'Негативный' unless accompanied by anger or strong dissatisfaction.
- Priority score guidance:
  * fraud/security, account hacked, money missing → 9-10
  * blocked accounts / cannot access funds, "срочно" → 8-10
  * complaints / претензии → 7-8
  * app issues → 6-7
  * data changes → 5-6
  * consultations → 3-4
  * spam → 1
- Return ONLY valid JSON, no markdown or extra text."""


URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)

# ── Keyword / phrase lists for deterministic sentiment ──────────────

# Strong positive: clear satisfaction / resolution (triggers POSITIVE)
STRONG_POSITIVE = [
    "всё решено", "все решено", "решили", "помогли",
    "всё заработало", "все заработало", "доволен", "довольна",
    "замечательно", "прекрасно", "молодцы",
    "great", "well done", "resolved", "fixed", "it works now",
]

# Weak positive: simple thanks without clear resolution (stays NEUTRAL)
WEAK_POSITIVE = [
    "спасибо", "спс", "рахмет", "thank you", "thanks", "благодарю",
    "благодарен", "благодарна",
]

# Issue / help-request markers: suggest the user has a problem but
# not necessarily negative sentiment (stays NEUTRAL unless strong neg)
ISSUE_MARKERS = [
    "проблем", "вопрос", "подскажите", "помогите", "как сделать",
    "как изменить", "не получается", "доступ", "нужна помощь",
    "консультация", "уточнить", "разъяснить", "не понимаю",
    "how to", "question", "help me", "issue",
]

# Fraud / security markers (always NEGATIVE)
FRAUD_MARKERS = [
    "мошенн", "fraud", "scam", "алаяқ",
    "списали деньги", "деньги пропали",
    "несанкционирован", "unauthorized",
]

# Blocked / access-lost markers (always NEGATIVE)
BLOCKED_MARKERS = [
    "заблок", "не могу войти", "счета заблокированы",
    "account blocked", "locked out",
]

# Legacy lists kept for backward compat with heuristic_fallback & _has_urgency
POSITIVE_MARKERS = STRONG_POSITIVE + WEAK_POSITIVE
NEGATIVE_MARKERS = [
    "срочно", "немедленно", "сейчас же", "urgent", "asap", "immediately",
    "ужас", "обман", "мошенники", "мошеннич",
    "заблок", "не работает", "верните", "вы обязаны",
    "жалоба", "жалоб", "угрожаю", "суд", "прокуратур",
    "взлом", "украли", "списали деньги", "не могу войти",
    "разбирательств", "недопустимо", "безобразие",
    "complaint", "fraud", "scam",
]


# ── Utility helpers ─────────────────────────────────────────────────

def _safe_lower(text: str | None) -> str:
    """Lowercase with None safety."""
    return (text or "").lower()


def _has_any_phrase(lowered_text: str, phrases: list[str]) -> bool:
    """Return True if any phrase appears as a substring in *lowered_text*."""
    return any(p in lowered_text for p in phrases)


def _has_any_word(text: str, words: list[str]) -> bool:
    """Return True if any word appears as a whole word (word-boundary match)."""
    t = (text or "")
    for w in words:
        if re.search(rf"\b{re.escape(w)}\b", t, re.IGNORECASE):
            return True
    return False


# ── Spam detection ──────────────────────────────────────────────────

def _looks_like_spam(text: str) -> bool:
    t = (text or "").lower()
    if URL_RE.search(t):
        # strong spam signals around links
        spam_markers = [
            "выгодное предложение",
            "специальные цены",
            "в наличии",
            "минимальный заказ",
            "отгрузка",
            "подберем оборудование",
            "питомник",
            "тюльпаны",
            "скидк",
            "купите",
            "закажите",
            "реклама",
        ]
        if any(m in t for m in spam_markers):
            return True
        # link-only / marketing-like content
        if len(t) > 200 and t.count("http") >= 1 and ("предлож" in t or "цена" in t):
            return True
    # no link but still spammy
    spam_markers2 = [
        "специальные цены",
        "минимальный заказ",
        "в наличии",
        "оптов",
        "прайс",
        "коммерческое предложение",
    ]
    return any(m in t for m in spam_markers2)


# ── Strong-negative evidence (shared by both paths) ─────────────────

def _has_strong_negative_evidence(text: str) -> bool:
    """
    True only when there is *strong* evidence of negative sentiment:
    - strong threats / escalation language
    - explicit severe failures (error/timeout/crash/sms not coming)
    - multiple exclamation marks (emotional intensity)
    """
    t = _safe_lower(text)

    # 4. Severely angry or escalated words (profanity, legal threats, deep dissatisfaction)
    strong_phrases = [
        "верните", "требую", "обман", "ужас", "безобраз", "недопустимо",
        "жалоб", "претенз", "прокуратур", "регулятор", "задолбал", "достали",
        "заеба", "блять", "хуй", "охуе", "пиздец", "сука", "ебан", "черт", "тварь"
    ]
    if _has_any_phrase(t, strong_phrases):
        return True

    # 5. Word-boundary match for "суд" (avoid matching inside longer words)
    if _has_any_word(text, ["суд"]):
        return True

    # 6. Multiple exclamation marks → strong emotion
    if re.search(r"!{2,}", text or ""):
        return True

    return False


# ── Deterministic sentiment detection ───────────────────────────────

def _detect_sentiment_markers(text: str) -> Sentiment:
    """
    Less-sensitive deterministic sentiment detection.

    Rules (applied in order):
      1. Spam → NEUTRAL.
      2. Strong negative evidence → NEGATIVE.
      3. Issue / help-request phrase (but not strong negative) → NEUTRAL.
      4. Strong positive markers (and no issue) → POSITIVE.
      5. Weak positive only (just "thanks") → NEUTRAL.
      6. Default → NEUTRAL.
    """
    t = _safe_lower(text)

    if _looks_like_spam(text):
        return Sentiment.NEUTRAL

    has_issue = _has_any_phrase(t, ISSUE_MARKERS)
    has_strong_pos = _has_any_phrase(t, STRONG_POSITIVE)
    has_weak_pos = _has_any_phrase(t, WEAK_POSITIVE) or _has_any_word(text, ["THX"])

    # Strong negative evidence → NEGATIVE
    if _has_strong_negative_evidence(text):
        return Sentiment.NEGATIVE

    # Issue / help request but not strong negative → NEUTRAL
    if has_issue:
        return Sentiment.NEUTRAL

    # Clear satisfaction + resolution (no active issue) → POSITIVE
    if has_strong_pos and not has_issue:
        return Sentiment.POSITIVE

    # Thanks alone → NEUTRAL
    if has_weak_pos:
        return Sentiment.NEUTRAL

    return Sentiment.NEUTRAL


# ── Urgency check ───────────────────────────────────────────────────

def _has_urgency(text: str) -> bool:
    t = (text or "").lower()
    urgent = ["срочно", "немедленно", "сейчас же", "urgent", "asap", "immediately"]
    if any(u in t for u in urgent):
        return True
    # blocking / access lost tends to be urgent
    if any(w in t for w in ["заблок", "не могу войти", "счета заблокированы"]):
        return True
    return False


# ── LLM enum mapping ───────────────────────────────────────────────

TICKET_TYPE_MAP: dict[str, TicketType] = {t.value: t for t in TicketType}
SENTIMENT_MAP: dict[str, Sentiment] = {s.value: s for s in Sentiment}
LANGUAGE_MAP: dict[str, Language] = {lang.value: lang for lang in Language}


class OpenAIAdapter(LLMPort):
    """OpenAI implementation of LLMPort."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = 3,
    ):
        if AsyncOpenAI is None:
            self._client = None
        else:
            self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self._model = model or settings.openai_model
        self._max_retries = max_retries

    async def analyze_ticket(
        self, description: str, attachments: str | None = None
    ) -> AIAnalysis:
        """Send ticket to OpenAI and parse structured response."""
        # Fast-path: obvious spam should not waste LLM calls.
        if _looks_like_spam(description):
            return self._spam_result(description)

        # If OpenAI SDK is missing or API key is missing/placeholder, do not attempt network calls.
        if self._client is None:
            logger.warning("openai package is not installed/available. Using heuristic fallback.")
            return self._post_adjust(self._heuristic_fallback(description), description)

        if not (settings.openai_api_key or "").strip() or "your-openai-api-key" in (settings.openai_api_key or ""):
            logger.warning("OPENAI_API_KEY is not set (or placeholder). Using heuristic fallback.")
            return self._post_adjust(self._heuristic_fallback(description), description)

        user_content = self._build_user_prompt(description, attachments)

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )

                raw_text = response.choices[0].message.content or ""
                parsed = json.loads(raw_text)
                analysis = self._map_to_analysis(parsed)
                return self._post_adjust(analysis, description)

            except json.JSONDecodeError:
                logger.warning(
                    "Attempt %d/%d: failed to parse JSON from LLM response",
                    attempt, self._max_retries,
                )
            except KeyError as e:
                logger.warning(
                    "Attempt %d/%d: missing key in LLM response: %s",
                    attempt, self._max_retries, e,
                )
            except Exception:
                logger.exception(
                    "Attempt %d/%d: unexpected error during LLM call",
                    attempt, self._max_retries,
                )

        # Fallback: heuristic classification
        logger.warning("All LLM attempts failed, using heuristic fallback")
        return self._post_adjust(self._heuristic_fallback(description), description)

    def _build_user_prompt(self, description: str, attachments: str | None) -> list[dict]:
        """Build the user message payload, potentially including base64 images."""
        content = [{"type": "text", "text": f"Ticket text:\n{description}"}]
        
        if attachments:
            content[0]["text"] += f"\nAttachments: {attachments}"
            
            import base64
            from pathlib import Path
            
            # Find the images folder relative to the data path configured via settings
            data_dir = Path(settings.csv_data_path).parent if hasattr(settings, 'csv_data_path') else Path.cwd() / "data"
            image_dir = data_dir / "images"
            
            if image_dir.exists():
                for filename in attachments.split(","):
                    filename = filename.strip()
                    img_path = image_dir / filename
                    
                    if img_path.exists() and img_path.is_file():
                        try:
                            with open(img_path, "rb") as image_file:
                                encoded = base64.b64encode(image_file.read()).decode("utf-8")
                                
                            ext = img_path.suffix.lower().replace(".", "")
                            mime_type = f"image/{ext}" if ext in ["jpeg", "jpg", "png", "webp", "gif"] else "image/jpeg"
                            
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{encoded}"
                                }
                            })
                            logger.info("Successfully attached image %s to LLM prompt", filename)
                        except Exception as e:
                            logger.error("Failed to read/encode image attachment %s: %s", filename, e)

        return content

    def _map_to_analysis(self, parsed: dict) -> AIAnalysis:
        """Map raw LLM JSON to AIAnalysis domain entity."""
        ticket_type = TICKET_TYPE_MAP.get(
            parsed.get("ticket_type", ""), TicketType.CONSULTATION
        )
        sentiment = SENTIMENT_MAP.get(
            parsed.get("sentiment", ""), Sentiment.NEUTRAL
        )
        language = LANGUAGE_MAP.get(
            parsed.get("language", ""), Language.RU
        )
        priority = max(1, min(10, int(parsed.get("priority_score", 5))))
        summary = parsed.get("summary", "")

        return AIAnalysis(
            id=None,
            ticket_id=0,
            ticket_type=ticket_type,
            sentiment=sentiment,
            priority_score=priority,
            language=language,
            summary=summary,
            llm_model=self._model,
        )

    def _spam_result(self, description: str) -> AIAnalysis:
        return AIAnalysis(
            id=None,
            ticket_id=0,
            ticket_type=TicketType.SPAM,
            sentiment=Sentiment.NEUTRAL,
            priority_score=1,
            language=Language.RU,
            summary="Спам/реклама. Обращение не относится к поддержке Freedom Broker.",
            llm_model="spam-heuristic",
        )

    @staticmethod
    def _post_adjust(analysis: AIAnalysis, original_text: str) -> AIAnalysis:
        """
        Less-sensitive deterministic post-adjustment for Sentiment.

        Applied AFTER both LLM and heuristic paths.  Only overrides when
        the text contains *unambiguous* evidence:
          1. Strong negative evidence → force NEGATIVE + priority boost.
          2. Strong positive evidence (no negative) → force POSITIVE.
          3. Weak thanks only → downgrade to NEUTRAL.
          4. LLM said NEGATIVE but no strong evidence → downgrade to NEUTRAL.
          5. Otherwise keep as-is (usually NEUTRAL).
        """
        if analysis.ticket_type == TicketType.SPAM:
            return analysis

        text = (original_text or "").strip()
        t = _safe_lower(text)

        strong_neg = _has_strong_negative_evidence(text)
        strong_pos = _has_any_phrase(t, STRONG_POSITIVE)
        weak_pos_only = (
            _has_any_phrase(t, WEAK_POSITIVE) or _has_any_word(text, ["THX"])
        ) and not strong_pos

        # Priority Boosts (Independent of Sentiment)
        # ----------------------------------------
        is_fraud = _has_any_phrase(t, FRAUD_MARKERS)
        is_blocked = _has_any_phrase(t, BLOCKED_MARKERS)
        is_urgent = _has_urgency(text)
        
        if is_fraud:
            analysis.priority_score = max(analysis.priority_score, 9)
        elif is_blocked or is_urgent:
            analysis.priority_score = max(analysis.priority_score, 8)

        # Sentiment Overrides
        # -------------------
        # 1) Strong negative evidence → force NEGATIVE
        if strong_neg:
            analysis.sentiment = Sentiment.NEGATIVE
            return analysis

        # 2) Strong positive evidence (no negative) → POSITIVE
        if strong_pos:
            analysis.sentiment = Sentiment.POSITIVE
            return analysis

        # 3) Weak thanks only → NEUTRAL (don't let "спасибо" alone = positive)
        if weak_pos_only:
            analysis.sentiment = Sentiment.NEUTRAL
            return analysis

        # 4) LLM said NEGATIVE but we found no strong evidence → downgrade
        if analysis.sentiment == Sentiment.NEGATIVE:
            analysis.sentiment = Sentiment.NEUTRAL

        # 5) Otherwise keep as-is
        return analysis

    @staticmethod
    def _heuristic_fallback(description: str) -> AIAnalysis:
        """Simple rule-based fallback when LLM is unavailable."""
        text = description.lower()

        # Obvious spam detection
        if _looks_like_spam(description):
            return AIAnalysis(
                id=None,
                ticket_id=0,
                ticket_type=TicketType.SPAM,
                sentiment=Sentiment.NEUTRAL,
                priority_score=1,
                language=Language.RU,
                summary="Спам/реклама. Обращение не относится к поддержке.",
                llm_model="heuristic-fallback",
            )

        # Language detection
        kz_markers = ["сәлем", "қалай", "мен", "маған", "жасау", "өтініш", "рахмет"]
        en_markers = ["hello", "please", "want", "need", "help", "issue", "thank you", "thanks"]
        if any(m in text for m in kz_markers):
            language = Language.KZ
        elif any(m in text for m in en_markers):
            language = Language.ENG
        else:
            language = Language.RU

        # Sentiment detection via the new less-sensitive markers
        sentiment = _detect_sentiment_markers(description)

        # Ticket type detection
        if any(w in text for w in ["мошен", "fraud", "алаяқ", "взлом", "украли", "списали деньги"]):
            ticket_type = TicketType.FRAUD
            priority = 9
        elif any(w in text for w in ["жалоб", "complaint", "шағым"]):
            ticket_type = TicketType.COMPLAINT
            priority = 7
        elif any(w in text for w in ["заблок", "счета заблокированы", "не могу войти", "доступ"]):
            ticket_type = TicketType.COMPLAINT
            priority = 8
        elif any(w in text for w in ["смена данных", "изменить", "данные", "деректер"]):
            ticket_type = TicketType.DATA_CHANGE
            priority = 5
        elif any(w in text for w in ["приложен", "app", "қосымша", "не работает", "ошибк"]):
            ticket_type = TicketType.APP_MALFUNCTION
            priority = 6
        elif any(w in text for w in ["претенз", "claim", "талап"]):
            ticket_type = TicketType.CLAIM
            priority = 7
        else:
            ticket_type = TicketType.CONSULTATION
            priority = 4

        return AIAnalysis(
            id=None,
            ticket_id=0,
            ticket_type=ticket_type,
            sentiment=sentiment,
            priority_score=priority,
            language=language,
            summary=description[:200],
            llm_model="heuristic-fallback",
        )
