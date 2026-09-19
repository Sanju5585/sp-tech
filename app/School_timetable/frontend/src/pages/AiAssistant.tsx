import { FormEvent, useState } from "react";
import { api } from "../api";

type Msg = { role: "user" | "ai"; content: string };

export default function AiAssistant() {
  const [instruction, setInstruction] = useState("Keep Maths and Science mostly in the morning for Class 8.");
  const [parsed, setParsed] = useState<unknown>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [chat, setChat] = useState("Mr Sharma is not available on Friday.");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [error, setError] = useState("");

  async function parseRule(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await api.post("/api/ai/parse-rule", { instruction, apply: true });
      setParsed(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI failed");
    }
  }

  async function send(confirm = false) {
    setError("");
    try {
      const res = await api.post<{ reply: string; conversation_id: number; affected_count: number }>("/api/ai/chat", {
        message: chat,
        conversation_id: conversationId,
        confirm_action: confirm,
      });
      setConversationId(res.conversation_id);
      setMessages((m) => [...m, { role: "user", content: chat }, { role: "ai", content: res.reply }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI failed");
    }
  }

  return (
    <div>
      <h1>AI assistant</h1>
      <p className="muted">
        Gemini only proposes structured rules. The OR-Tools solver still owns the timetable. All AI JSON is validated
        before anything is stored.
      </p>
      {error && <p className="error">{error}</p>}
      <form className="card" onSubmit={parseRule}>
        <label>Natural-language rule</label>
        <textarea className="input" rows={3} value={instruction} onChange={(e) => setInstruction(e.target.value)} />
        <button className="btn" style={{ marginTop: 10 }}>
          Parse & save as rule
        </button>
        {parsed != null && <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(parsed, null, 2)}</pre>}
      </form>
      <div className="card chat" style={{ marginTop: 16 }}>
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role === "user" ? "user" : "ai"}`}>
            {m.content}
          </div>
        ))}
        <textarea className="input" rows={2} value={chat} onChange={(e) => setChat(e.target.value)} />
        <div className="row">
          <button className="btn" onClick={() => send(false)}>
            Send
          </button>
          <button className="btn secondary" onClick={() => send(true)}>
            Confirm / Fix them
          </button>
        </div>
      </div>
    </div>
  );
}
