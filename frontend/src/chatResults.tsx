import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import type { PageResults } from "./api";

/**
 * Shared state for chat search results shown on the Products page ("Picked for you").
 * Kept in sessionStorage too, so a refresh or the back button doesn't lose them.
 */
interface ChatResultsState {
  results: PageResults | null;
  /** Increments each time the chat delivers new results (lets the page scroll to them once). */
  version: number;
  /** Apply a chat reply's page_results: cards replace the old set; an empty list clears it. */
  apply: (next: PageResults) => void;
  clear: () => void;
}

const STORAGE_KEY = "cc_picked_for_you";
const ChatResultsContext = createContext<ChatResultsState | null>(null);

function load(): PageResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PageResults) : null;
  } catch {
    return null;
  }
}

function save(results: PageResults | null) {
  try {
    if (results) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(results));
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage unavailable (private mode etc.): results still live in memory.
  }
}

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<PageResults | null>(load);
  const [version, setVersion] = useState(0);

  const apply = useCallback((next: PageResults) => {
    const value = next.products.length > 0 ? next : null; // never show an empty or stale section
    setResults(value);
    save(value);
    setVersion((v) => v + 1);
  }, []);

  const clear = useCallback(() => {
    setResults(null);
    save(null);
  }, []);

  return (
    <ChatResultsContext.Provider value={{ results, version, apply, clear }}>{children}</ChatResultsContext.Provider>
  );
}

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext);
  if (!ctx) throw new Error("useChatResults must be used inside <ChatResultsProvider>");
  return ctx;
}
