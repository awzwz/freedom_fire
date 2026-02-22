"use client";

import React, { useState, useRef, useEffect } from "react";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend,
} from "recharts";
import { api, type AssistantResponse, type ChartPayload } from "@/lib/api";

const PIE_COLORS = ["#059669", "#10b981", "#34d399", "#6ee7b7", "#a7f3d0", "#047857", "#064e3b", "#0d9488", "#14b8a6"];

interface ChatMessage {
    role: "user" | "ai";
    text: string;
    chart?: ChartPayload | null;
}

function MiniChart({ chart }: { chart: ChartPayload }) {
    if (chart.type === "pie") {
        return (
            <div className="ai-chat-chart">
                <div className="ai-chat-chart-title">{chart.title}</div>
                <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                        <Pie
                            data={chart.data}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            outerRadius={70}
                            innerRadius={30}
                            paddingAngle={2}
                            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                            style={{ fontSize: 10 }}
                        >
                            {chart.data.map((_, i) => (
                                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: 10 }} />
                    </PieChart>
                </ResponsiveContainer>
            </div>
        );
    }

    return (
        <div className="ai-chat-chart">
            <div className="ai-chat-chart-title">{chart.title}</div>
            <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chart.data}>
                    <XAxis dataKey="name" tick={{ fontSize: 9, fill: "var(--text-secondary)" }} angle={-25} textAnchor="end" height={50} interval={0} />
                    <YAxis tick={{ fontSize: 10, fill: "var(--text-secondary)" }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#059669" radius={[4, 4, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

export default function AiAssistant() {
    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([
        { role: "ai", text: "Привет! Я AI-ассистент FIRE. Задайте вопрос о тикетах, менеджерах или аналитике. Например: «Сколько всего тикетов?» или «Покажи график по типам тикетов»." },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        const question = input.trim();
        if (!question || loading) return;

        setInput("");
        setMessages((prev) => [...prev, { role: "user", text: question }]);
        setLoading(true);

        try {
            const res: AssistantResponse = await api.askAssistant(question);
            setMessages((prev) => [
                ...prev,
                { role: "ai", text: res.answer, chart: res.chart },
            ]);
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : String(err);
            setMessages((prev) => [
                ...prev,
                { role: "ai", text: `Ошибка: ${errorMessage}` },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <>
            {/* Toggle button */}
            <button
                className={`ai-chat-toggle ${open ? "active" : ""}`}
                onClick={() => setOpen(!open)}
                title="AI Assistant"
                id="ai-assistant-toggle"
            >
                {open ? (
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                ) : (
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" />
                    </svg>
                )}
            </button>

            {/* Chat panel */}
            <div className={`ai-chat-panel ${open ? "open" : ""}`}>
                <div className="ai-chat-header">
                    <div className="ai-chat-header-left">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" />
                        </svg>
                        <span>AI Ассистент</span>
                    </div>
                    <button className="ai-chat-close" onClick={() => setOpen(false)}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                    </button>
                </div>

                <div className="ai-chat-messages" ref={scrollRef}>
                    {messages.map((msg, i) => (
                        <div key={i} className={`ai-chat-msg ${msg.role}`}>
                            <div className="ai-chat-bubble">
                                {msg.text}
                                {msg.chart && <MiniChart chart={msg.chart} />}
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="ai-chat-msg ai">
                            <div className="ai-chat-bubble ai-chat-typing">
                                <span /><span /><span />
                            </div>
                        </div>
                    )}
                </div>

                <div className="ai-chat-input-area">
                    <input
                        id="ai-assistant-input"
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Задайте вопрос..."
                        disabled={loading}
                    />
                    <button
                        className="ai-chat-send"
                        onClick={handleSend}
                        disabled={!input.trim() || loading}
                        id="ai-assistant-send"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="22" y1="2" x2="11" y2="13" />
                            <polygon points="22,2 15,22 11,13 2,9" />
                        </svg>
                    </button>
                </div>
            </div>
        </>
    );
}
