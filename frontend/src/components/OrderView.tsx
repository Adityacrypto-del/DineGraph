import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, ChatMessage, MenuView, SessionView } from "../api";
import { Armchair, ChefHat, CircleAlert, CircleCheck, CircleX, ConciergeBell, CreditCard, LucideIcon, UtensilsCrossed } from "lucide-react";
import OrderPanel from "./OrderPanel";

const SESSION_KEY = "dinegraph.session";
const TABLE_KEY = "dinegraph.table";
const TABLES = Array.from({ length: 20 }, (_, i) => i + 1);
const POLL_MS = 1000;

const QUICK_REPLIES: Record<string, string[]> = {
  decision: ["Accept what's available", "New order", "Cancel"],
  payment: ["Cash", "Card", "UPI"],
};

const ROLE_META: Record<string, { Icon: LucideIcon; label: string }> = {
  assistant: { Icon: UtensilsCrossed, label: "DineGraph" },
  kitchen: { Icon: ChefHat, label: "Kitchen" },
  waiter: { Icon: ConciergeBell, label: "Waiter" },
  cashier: { Icon: CreditCard, label: "Cashier" },
};

// What the typing bubble says while the graph runs a slow step.
const WORKING_LABEL: Record<string, string> = {
  cook: "Cooking",
  serve: "Serving",
  request_payment: "Preparing the bill",
  pay: "Processing payment",
};

function remember(id: string | null) {
  try {
    if (id) localStorage.setItem(SESSION_KEY, id);
    else localStorage.removeItem(SESSION_KEY);
  } catch {
    /* storage unavailable: the session just won't survive a reload */
  }
}

function recall(key = SESSION_KEY): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function rememberTable(table: number | null) {
  try {
    localStorage.setItem(TABLE_KEY, table ? String(table) : "");
  } catch {
    /* storage unavailable */
  }
}

export default function OrderView() {
  const [session, setSession] = useState<SessionView | null>(null);
  const [menu, setMenu] = useState<MenuView | null>(null);
  const [pending, setPending] = useState<string | null>(null); // user text sent but not yet answered
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [table, setTable] = useState<number | null>(() => Number(recall(TABLE_KEY)) || null);
  const scroller = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  const loadMenu = useCallback(() => {
    api.menu().then(setMenu).catch(() => undefined);
  }, []);

  const startNew = useCallback(async (seat: number | null = table) => {
    setBusy(true);
    setError(null);
    setDraft("");
    try {
      const s = await api.startSession(seat);
      setSession(s);
      remember(s.session_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      loadMenu();
    }
  }, [loadMenu, table]);

  // Resume the last session after a reload, or start a fresh one.
  useEffect(() => {
    loadMenu();
    const saved = recall();
    if (!saved) {
      void startNew();
      return;
    }
    api
      .getSession(saved)
      .then(setSession)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) void startNew();
        else setError((e as Error).message);
      });
    // only on first load; startNew changes whenever the table does
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // While the kitchen works, the server answers before the graph pauses. Poll until it does.
  const sessionId = session?.session_id;
  const serverBusy = !!session?.busy;
  useEffect(() => {
    if (!sessionId || !serverBusy) return;
    const t = setTimeout(() => {
      api
        .getSession(sessionId)
        .then((s) => {
          setSession(s);
          if (!s.busy) loadMenu();
        })
        .catch(() => setSession((s) => (s ? { ...s } : s))); // try again on the next tick
    }, POLL_MS);
    return () => clearTimeout(t);
  }, [sessionId, serverBusy, session, loadMenu]);

  function pickTable(value: string) {
    const seat = Number(value) || null;
    setTable(seat);
    rememberTable(seat);
    // nothing ordered yet: move this session to the new table by starting afresh
    if (session && session.messages.length <= 1 && !busy) void startNew(seat);
  }

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [session?.messages.length, pending, busy]);

  useEffect(() => {
    if (!busy && session?.waiting_for) input.current?.focus();
  }, [busy, session?.waiting_for]);

  async function act(call: () => Promise<SessionView>) {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      setSession(await call());
    } catch (e) {
      setError((e as Error).message);
      // a failed step leaves the session stalled on the server; show that state
      api.getSession(session.session_id).then(setSession).catch(() => undefined);
    } finally {
      setPending(null);
      setBusy(false);
      loadMenu();
    }
  }

  function send(text: string) {
    const clean = text.trim();
    if (!clean || !session || busy || session.busy) return;
    setDraft("");
    setPending(clean);
    void act(() => api.send(session.session_id, clean));
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    send(draft);
  }

  function addDish(dish: string) {
    if (session?.waiting_for !== "order") return;
    const max = menu?.max_dishes ?? 3;
    const parts = draft.split(",").map((p) => p.trim()).filter(Boolean);
    const idx = parts.findIndex((p) => p.toLowerCase().replace(/^\d+\s*x?\s*/, "") === dish.toLowerCase());
    if (idx >= 0) {
      const m = parts[idx].match(/^(\d+)/);
      parts[idx] = `${(m ? Number(m[1]) : 1) + 1} ${dish}`;
    } else if (parts.length < max) {
      parts.push(`1 ${dish}`);
    }
    setDraft(parts.join(", "));
    input.current?.focus();
  }

  const messages: ChatMessage[] = session?.messages ?? [];
  const waiting = session?.waiting_for ?? null;
  const working = busy || serverBusy;
  const canType = !!session && !!waiting && !working;
  const placeholder = !session
    ? "Connecting…"
    : session.done
      ? "This order has finished"
      : session.stalled
        ? "A step failed. Retry to continue"
        : waiting === "order"
          ? "e.g. 2 Veg Biryani (extra spicy), 1 Cold Coffee"
          : waiting === "decision"
            ? "Accept the partial order, order again, or cancel"
            : waiting === "payment"
              ? "Cash, card or UPI"
              : "…";

  return (
    <div className="order-layout">
      <section className="chat card" aria-label="Conversation">
        <div className="chat-head">
          <label>
            <Armchair size={16} aria-hidden />
            <select value={table ?? ""} onChange={(e) => pickTable(e.target.value)} aria-label="Table">
              <option value="">Takeaway</option>
              {TABLES.map((n) => (
                <option key={n} value={n}>
                  Table {n}
                </option>
              ))}
            </select>
          </label>
          <span className="muted small">
            {session && (session.table ?? null) !== table ? "Applies to your next order" : "Add notes in brackets: (no onion)"}
          </span>
        </div>
        <div className="chat-scroll" ref={scroller} aria-live="polite">
          {messages.map((m, i) => (
            <Message key={i} message={m} />
          ))}
          {pending && <Message message={{ role: "user", content: pending }} />}
          {working && (
            <div className="msg msg-assistant">
              <span className="avatar" aria-hidden>
                {serverBusy ? <ChefHat size={16} /> : <UtensilsCrossed size={16} />}
              </span>
              <div className="bubble typing" aria-label={serverBusy ? "The kitchen is working" : "DineGraph is working"}>
                <i />
                <i />
                <i />
                {serverBusy && <span className="typing-label">{WORKING_LABEL[session?.next_step ?? ""] ?? "Working"}</span>}
              </div>
            </div>
          )}
          {session?.done && <FinalBanner session={session} onNew={() => startNew()} />}
        </div>

        {error && (
          <div className="alert alert-bad" role="alert">
            <span>{error}</span>
            {!session && (
              <button className="btn btn-small" onClick={() => startNew()}>
                Try again
              </button>
            )}
          </div>
        )}
        {session?.stalled && (
          <div className="alert alert-warn">
            <span>The last step didn't finish{session.error ? ` (${session.error})` : ""}. Your order is saved.</span>
            <button className="btn btn-small" disabled={busy} onClick={() => act(() => api.retry(session.session_id))}>
              Retry step
            </button>
          </div>
        )}

        {waiting && QUICK_REPLIES[waiting] && (
          <div className="quick-replies">
            {QUICK_REPLIES[waiting].map((q) => (
              <button key={q} className="chip" disabled={working} onClick={() => send(q)}>
                {q}
              </button>
            ))}
          </div>
        )}

        <form className="composer" onSubmit={onSubmit}>
          <input
            ref={input}
            value={draft}
            maxLength={1000}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={placeholder}
            disabled={!canType}
            aria-label="Message"
          />
          <button className="btn btn-primary" disabled={!canType || !draft.trim()}>
            Send
          </button>
        </form>
      </section>

      <OrderPanel session={session} menu={menu} onPickDish={addDish} canPick={waiting === "order" && !working} onNew={() => startNew()} busy={working} />
    </div>
  );
}

function Message({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="msg msg-user">
        <div className="bubble">{message.content}</div>
      </div>
    );
  }
  const meta = ROLE_META[message.role] ?? ROLE_META.assistant;
  if (message.role !== "assistant") {
    return (
      <div className={`event event-${message.role}`}>
        <meta.Icon className="event-icon" size={15} aria-hidden />
        <span className="event-label">{meta.label}</span>
        <span className="event-text">{message.content}</span>
      </div>
    );
  }
  return (
    <div className="msg msg-assistant">
      <span className="avatar" aria-hidden>
        <meta.Icon size={16} />
      </span>
      <div className="bubble">{message.content}</div>
    </div>
  );
}

function FinalBanner({ session, onNew }: { session: SessionView; onNew: () => void }) {
  const ok = session.final_result === "COMPLETED";
  const reason = session.final_result.replace(/^NOT_COMPLETED:\s*/, "").replace(/_/g, " ");
  return (
    <div className={`final ${ok ? "final-good" : "final-bad"}`}>
      <div className="final-icon" aria-hidden>
        {ok ? <CircleCheck size={28} /> : session.status === "CANCELLED" ? <CircleX size={28} /> : <CircleAlert size={28} />}
      </div>
      <div>
        <strong>{ok ? "Order complete" : session.status === "CANCELLED" ? "Order cancelled" : "Order not completed"}</strong>
        <p>{ok ? `Paid ${session.payment_method.toUpperCase()}. Enjoy your meal.` : `Reason: ${reason}.`}</p>
      </div>
      <button className="btn btn-primary" onClick={onNew}>
        Start a new order
      </button>
    </div>
  );
}
