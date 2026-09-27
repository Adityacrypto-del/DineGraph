// Typed client for the DineGraph FastAPI backend. Types mirror dinegraph/api.py.

export type Role = "user" | "assistant" | "kitchen" | "waiter" | "cashier";
export type WaitingFor = "order" | "decision" | "payment" | null;

export interface ChatMessage { role: Role; content: string }
export interface OrderLine { dish: string; required_quantity: number; available_quantity: number; note: string }
export interface Counters {
  order_retries: number;
  cook_retries: number;
  serve_retries: number;
  payment_retries: number;
}
export interface SessionView {
  session_id: string;
  messages: ChatMessage[];
  waiting_for: WaitingFor;
  prompt: string | null;
  done: boolean;
  stalled: boolean;
  busy: boolean; // the graph is still running; poll getSession
  next_step: string | null;
  error: string | null;
  table: number | null;
  status: string;
  order: OrderLine[];
  counters: Counters;
  bill_total: number;
  payment_method: string;
  final_result: string;
}
export interface MenuItem { dish: string; available: number; price: number }
export interface MenuView { max_dishes: number; items: MenuItem[] }
export interface OrderRecord {
  session_id: string;
  status: string;
  final_result: string;
  items: OrderLine[];
  bill_total: number;
  payment_method: string;
  created_at: string;
  updated_at: string;
  table: number | null;
  stage: string;
}
export interface OrderEvent { at: string; step: string; status: string; detail: string }
export type KitchenStage = "cooking" | "serving" | "paying";
export interface KitchenTicket {
  session_id: string;
  table: number | null;
  stage: KitchenStage;
  status: string;
  items: OrderLine[];
  bill_total: number;
  created_at: string;
  updated_at: string;
}
export interface Stats {
  total_orders: number;
  completed: number;
  failed: number;
  cancelled: number;
  in_progress: number;
  revenue: number;
  revenue_by_method: Record<string, number>;
}
export interface Health { ok: boolean; llm: string; kitchen_seconds: number }

// Retry budgets from dinegraph/state.py, used to draw the counters.
export const MAX_RETRIES: Counters = { order_retries: 3, cook_retries: 2, serve_retries: 2, payment_retries: 2 };

const BASE: string = import.meta.env.VITE_API_URL ?? "/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}, adminToken?: string): Promise<T> {
  const headers: Record<string, string> = {};
  if (init.body) headers["Content-Type"] = "application/json";
  if (adminToken) headers["X-Admin-Token"] = adminToken;
  let res: Response;
  try {
    res = await fetch(BASE + path, { ...init, headers });
  } catch {
    throw new ApiError(0, "Can't reach the DineGraph server. Start it with: uvicorn dinegraph.api:app");
  }
  if (!res.ok) {
    let message = res.statusText || `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const json = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/health"),
  menu: () => request<MenuView>("/menu"),

  startSession: (table?: number | null) =>
    request<SessionView>("/sessions", table ? json({ table }) : { method: "POST" }),
  getSession: (id: string) => request<SessionView>(`/sessions/${id}`),
  // wait=1: answer quickly and let the order view poll while the kitchen works
  send: (id: string, text: string) => request<SessionView>(`/sessions/${id}/messages?wait=1`, json({ text })),
  retry: (id: string) => request<SessionView>(`/sessions/${id}/retry?wait=1`, { method: "POST" }),

  orders: (status?: string, limit = 50, offset = 0) => {
    const q = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (status) q.set("status", status);
    return request<OrderRecord[]>(`/orders?${q}`);
  },
  events: (id: string) => request<OrderEvent[]>(`/orders/${id}/events`),
  kitchen: () => request<KitchenTicket[]>("/kitchen"),

  stats: (token?: string) => request<Stats>("/admin/stats", {}, token),
  upsertDish: (dish: string, body: { quantity?: number; price?: number }, token?: string) =>
    request<MenuItem>(`/admin/menu/${encodeURIComponent(dish)}`, { method: "PUT", body: JSON.stringify(body) }, token),
  deleteDish: (dish: string, token?: string) =>
    request<void>(`/admin/menu/${encodeURIComponent(dish)}`, { method: "DELETE" }, token),
};

// Small shared helpers.
// Formats an ISO timestamp from the server as a local time, e.g. "7:42:05 pm".
export const clock = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", second: "2-digit" });

export const rupees = (n: number) => `₹${n.toLocaleString("en-IN")}`;

export function statusTone(status: string): "good" | "warn" | "bad" | "info" | "muted" {
  switch (status) {
    case "PAID":
    case "COMPLETE":
    case "CONFIRMED":
    case "READY":
      return "good";
    case "PARTIAL":
    case "COOK_FAILED":
    case "SERVE_FAILED":
    case "PAYMENT_FAILED":
    case "PAYMENT_PENDING":
      return "warn";
    case "FAILED":
    case "NOT_AVAILABLE":
    case "INVALID":
      return "bad";
    case "CANCELLED":
      return "muted";
    default:
      return "info";
  }
}

export const statusLabel = (status: string) =>
  status.toLowerCase().replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
