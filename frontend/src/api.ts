export const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Product {
  id: string;
  name: string;
  garment_type: string;
  description: string;
  colors: string[];
  tags: string[];
  price: number;
  image_url: string;
  in_stock: boolean;
}

export interface SizeStock {
  size: string;
  quantity: number;
  in_stock: boolean;
}

export interface ProductDetail extends Product {
  sizes: SizeStock[];
}

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export interface SignupInput {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

/** Error carrying the server's user-facing message and HTTP status. */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(res.status === 404 ? "not-found" : `Request failed (${res.status})`);
  return res.json() as Promise<T>;
}

/** Auth calls send/receive the HttpOnly session cookie; JS never sees the token. */
async function authRequest<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}/api/auth${path}`, {
    method,
    credentials: "include",
    headers: method === "POST" ? { "Content-Type": "application/json" } : undefined,
    body: method === "POST" ? JSON.stringify(body ?? {}) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.detail ?? "Something went wrong. Please try again.", res.status);
  return data as T;
}

export const getCurrentUser = () =>
  authRequest<{ user: User }>("GET", "/me").then((d) => d.user);

export const login = (email: string, password: string) =>
  authRequest<{ user: User }>("POST", "/login", { email, password }).then((d) => d.user);

export const signup = (input: SignupInput) =>
  authRequest<{ user: User }>("POST", "/signup", input).then((d) => d.user);

export const logout = () => authRequest<{ ok: boolean }>("POST", "/logout");

export const fetchProducts = () => getJson<Product[]>("/api/products");

export const fetchProduct = (id: string) =>
  getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`);

export const imageSrc = (imageUrl: string) => `${API_BASE}${imageUrl}`;

export const formatPrice = (price: number) =>
  price.toLocaleString("en-US", { style: "currency", currency: "USD" });

/** A product card sent by the chat API. Built by the server from database rows, never from model text. */
export interface ChatProduct {
  id: string;
  name: string;
  price: number;
  image_url: string;
  garment_type: string;
  short_description: string;
}

/** Search results for the Products page. Empty `products` means "found nothing: clear the page". */
export interface PageResults {
  query: string;
  total: number;
  products: ChatProduct[];
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatReply {
  reply: string;
  products: ChatProduct[];
  /** null means leave the page unchanged. */
  page_results: PageResults | null;
}

/** Limits mirrored from the backend (backend/models.py); the server enforces them too. */
export const CHAT_MAX_MESSAGE = 500;
export const CHAT_MAX_HISTORY = 10;

/** Sends a message plus recent history to the shop agent (POST /api/chat). */
export async function sendChatMessage(message: string, history: ChatTurn[]): Promise<ChatReply> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history: history.slice(-CHAT_MAX_HISTORY) }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.detail ?? "The assistant is unavailable right now.", res.status);
  return data as ChatReply;
}
