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

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(res.status === 404 ? "not-found" : `Request failed (${res.status})`);
  return res.json() as Promise<T>;
}

export const fetchProducts = () => getJson<Product[]>("/api/products");

export const fetchProduct = (id: string) =>
  getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`);

export const imageSrc = (imageUrl: string) => `${API_BASE}${imageUrl}`;

export const formatPrice = (price: number) =>
  price.toLocaleString("en-US", { style: "currency", currency: "USD" });

/**
 * Sends a chat message and returns the assistant's reply.
 * Stub for now: Problem 5 will replace the body with a call to the agent backend.
 */
export async function sendChatMessage(message: string): Promise<string> {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return `Thanks for your message! Our shopping assistant is still in training, so I can't answer "${message}" just yet. Check back soon.`;
}
