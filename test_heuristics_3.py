import asyncio
from app.adapters.llm.openai_adapter import OpenAIAdapter
from app.domain.entities.ai_analysis import AIAnalysis
from app.domain.value_objects.enums import TicketType, Sentiment, Language

def test_sentiment():
    adapter = OpenAIAdapter()
    
    test_cases = [
        # Test Case 1: Neutral Problem Report (High Priority)
        {
            "desc": "Добрый день. Я не могу войти в приложение, отвечает ошибкой. Пожалуйста, помогите разобраться.",
            "expected_heuristic": Sentiment.NEUTRAL,
            "expected_min_priority": 8
        },
        # Test Case 2: Fraud / Scared (High Priority, currently Neutral by heuristic since strong anger is missing)
        {
            "desc": "Срочно помогите, я перевел деньги мошенникам! Счета заблокированы!",
            "expected_heuristic": Sentiment.NEUTRAL,   
            "expected_min_priority": 9
        },
        # Test Case 3: Angry Complaint (High Priority, Negative)
        {
            "desc": "Ужасное приложение, обман чистой воды! Буду писать жалобу в прокуратуру",
            "expected_heuristic": Sentiment.NEGATIVE,
            "expected_min_priority": 7
        }
    ]
    
    for idx, tc in enumerate(test_cases, 1):
        print(f"--- Test Case {idx} ---")
        print(f"Text: {tc['desc']}")
        # Direct heuristic test
        result = adapter._heuristic_fallback(tc['desc'])
        result = adapter._post_adjust(result, tc['desc'])
        print(f"Post-adjusted Sentiment: {result.sentiment.value if hasattr(result.sentiment, 'value') else result.sentiment}")
        print(f"Priority: {result.priority_score}")
        
        sent_pass = result.sentiment == tc['expected_heuristic']
        prio_pass = result.priority_score >= tc['expected_min_priority']
        print(f"Pass Sentiment? {sent_pass}")
        print(f"Pass Priority? {prio_pass}")
        print()

if __name__ == "__main__":
    test_sentiment()
