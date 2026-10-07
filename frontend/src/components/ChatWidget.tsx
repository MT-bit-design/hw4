import { useEffect, useRef, useState, type FormEvent } from "react";
import { sendChatMessage } from "../api";

interface Message {
  role: "user" | "assistant";
  text: string;
}

const greeting: Message = {
  role: "assistant",
  text: "Hi! I'm the Campus Customs assistant. Looking for something blue?",
};

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([greeting]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setSending(true);
    try {
      const reply = await sendChatMessage(text);
      setMessages((m) => [...m, { role: "assistant", text: reply }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "Sorry, something went wrong. Try again." }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      {open && (
        <section className="chat-panel" aria-label="Chat with Campus Customs">
          <header className="chat-header">
            <span>Campus Customs Assistant</span>
            <button aria-label="Close chat" onClick={() => setOpen(false)}>
              ✕
            </button>
          </header>
          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`chat-bubble ${m.role}`}>
                {m.text}
              </div>
            ))}
            {sending && <div className="chat-bubble assistant typing">…</div>}
            <div ref={endRef} />
          </div>
          <form className="chat-form" onSubmit={handleSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about sizes, styles, gifts…"
              aria-label="Your message"
              autoFocus
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={!input.trim() || sending}>
              Send
            </button>
          </form>
        </section>
      )}
      <button
        className="chat-fab"
        aria-label={open ? "Close chat" : "Open chat"}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? "✕" : "💬"}
      </button>
    </>
  );
}
