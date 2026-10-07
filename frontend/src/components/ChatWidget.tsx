import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { useChatResults } from "../chatResults";
import { scrollBehavior } from "../motion";
import { Leaf } from "./Leaf";
import {
  ApiError,
  CHAT_MAX_MESSAGE,
  clearChatHistory,
  fetchChatHistory,
  formatPrice,
  imageSrc,
  sendChatMessage,
  type ChatProduct,
  type ChatTurn,
  type PageContext,
} from "../api";

interface Message {
  role: "user" | "assistant";
  text: string;
  products?: ChatProduct[];
  /** True when this reply put product cards on the Products page. */
  sentToPage?: boolean;
  /** Local-only messages (greeting, errors) are not sent back as history. */
  local?: boolean;
}

const QUICK_REPLIES = ["What hoodies do you have?", "Gifts under $40", "Is my size in stock?"];

function greetingFor(firstName?: string): Message {
  return {
    role: "assistant",
    text: firstName
      ? `Welcome back, ${firstName}! Looking for something blue today?`
      : "Hi! I'm the Campus Customs assistant. Looking for something blue?",
    local: true,
  };
}

/** The page the shopper is on, sent with every message so "this" can be resolved on the server. */
function pageContext(pathname: string): PageContext {
  const match = pathname.match(/^\/products\/([^/]+)$/);
  return { path: pathname, product_id: match ? decodeURIComponent(match[1]) : null };
}

export default function ChatWidget() {
  const { user, loading: authLoading } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([greetingFor()]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [clearing, setClearing] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const { apply: applyPageResults } = useChatResults();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const onProductsPage = pathname === "/products";
  const userId = user?.id;

  // On login (or page load while logged in), reload the last 30 saved messages. On logout, start fresh.
  useEffect(() => {
    if (authLoading) return;
    if (userId === undefined) {
      setMessages([greetingFor()]);
      return;
    }
    let cancelled = false;
    fetchChatHistory()
      .then(({ messages: saved }) => {
        if (cancelled) return;
        setMessages([
          greetingFor(user?.first_name),
          ...saved.map((m) => ({ role: m.role, text: m.content, products: m.products })),
        ]);
      })
      .catch(() => !cancelled && setMessages([greetingFor(user?.first_name)]));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, authLoading]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: scrollBehavior() });
  }, [messages, open]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await send(input);
  }

  async function send(raw: string) {
    const text = raw.trim();
    if (!text || sending) return;
    const history: ChatTurn[] = messages.filter((m) => !m.local).map((m) => ({ role: m.role, content: m.text }));
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setSending(true);
    try {
      const { reply, products, page_results } = await sendChatMessage(text, history, pageContext(pathname));
      // null = leave the page alone (off-topic, single-product questions); otherwise replace or clear.
      if (page_results) applyPageResults(page_results);
      const sentToPage = !!page_results && page_results.products.length > 0;
      setMessages((m) => [...m, { role: "assistant", text: reply, products, sentToPage }]);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Sorry, I couldn't reach the shop. Try again.";
      setMessages((m) => [...m, { role: "assistant", text: msg, local: true }]);
    } finally {
      setSending(false);
    }
  }

  async function handleClear() {
    if (clearing) return;
    if (!user) {
      setMessages([greetingFor()]); // guests: nothing is saved, just reset the panel
      return;
    }
    setClearing(true);
    try {
      await clearChatHistory();
      setMessages([greetingFor(user.first_name)]);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Couldn't clear your chat. Try again.";
      setMessages((m) => [...m, { role: "assistant", text: msg, local: true }]);
    } finally {
      setClearing(false);
    }
  }

  // Only the newest page-updating reply gets the button; older results were replaced.
  const lastPageReply = messages.reduce((last, m, i) => (m.sentToPage ? i : last), -1);
  const hasConversation = messages.some((m) => !m.local);
  // Quick replies help a shopper get started; they disappear once the shopper has typed anything.
  const showQuickReplies = !sending && input === "" && !messages.some((m) => m.role === "user");

  return (
    <>
      {open && (
        <section className="chat-panel" aria-label="Chat with Campus Customs">
          <header className="chat-header">
            <span className="chat-title">
              <Leaf color="var(--gold)" size={16} />
              <span className="chat-title-text">Campus Customs Assistant</span>
            </span>
            <span className="chat-header-actions">
              <button
                className="chat-clear"
                onClick={handleClear}
                disabled={clearing || sending || !hasConversation}
                title={user ? "Delete your saved chat history" : "Clear this chat"}
              >
                {clearing ? "Clearing…" : "Clear chat"}
              </button>
              <button aria-label="Close chat" onClick={() => setOpen(false)}>
                ✕
              </button>
            </span>
          </header>
          <p className="chat-note">
            {user ? "Your chats are saved to your account." : "Guest chat: nothing is saved. Log in to keep your chats."}
          </p>
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
                {m.sentToPage && i === lastPageReply && !onProductsPage && (
                  <button className="btn btn-primary btn-sm chat-see-page" onClick={() => navigate("/products")}>
                    See them on the page →
                  </button>
                )}
              </div>
            ))}
            {sending && (
              <div className="chat-bubble assistant typing" role="status" aria-label="The assistant is typing">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            )}
            {showQuickReplies && (
              <div className="chat-quick" aria-label="Suggested questions">
                {QUICK_REPLIES.map((q) => (
                  <button key={q} className="chat-quick-btn" onClick={() => send(q)}>
                    {q}
                  </button>
                ))}
              </div>
            )}
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
