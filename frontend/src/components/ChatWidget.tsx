import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  ApiError,
  CHAT_MAX_MESSAGE,
  formatPrice,
  imageSrc,
  sendChatMessage,
  type ChatProduct,
  type ChatTurn,
} from "../api";

interface Message {
  role: "user" | "assistant";
  text: string;
  products?: ChatProduct[];
  /** Local-only messages (greeting, errors) are not sent back as history. */
  local?: boolean;
}

const greeting: Message = {
  role: "assistant",
  text: "Hi! I'm the Campus Customs assistant. Looking for something blue?",
  local: true,
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
    const history: ChatTurn[] = messages.filter((m) => !m.local).map((m) => ({ role: m.role, content: m.text }));
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setSending(true);
    try {
      const { reply, products } = await sendChatMessage(text, history);
      setMessages((m) => [...m, { role: "assistant", text: reply, products }]);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Sorry, I couldn't reach the shop. Try again.";
      setMessages((m) => [...m, { role: "assistant", text: msg, local: true }]);
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
              <div key={i} className={`chat-turn ${m.role}`}>
                <div className={`chat-bubble ${m.role}`}>{m.text}</div>
                {m.products && m.products.length > 0 && (
                  <div className="chat-products">
                    {m.products.map((p) => (
                      <Link key={p.id} to={`/products/${p.id}`} className="chat-product">
                        <img src={imageSrc(p.image_url)} alt="" loading="lazy" />
                        <span className="chat-product-text">
                          <span className="chat-product-name">{p.name}</span>
                          <span className="chat-product-price">{formatPrice(p.price)}</span>
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {sending && <div className="chat-bubble assistant typing">Looking that up…</div>}
            <div ref={endRef} />
          </div>
          <form className="chat-form" onSubmit={handleSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about sizes, styles, gifts…"
              aria-label="Your message"
              maxLength={CHAT_MAX_MESSAGE}
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
