import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, ChatMessage, MenuView, SessionView } from "../api";
import { Armchair, Check, ChefHat, CircleAlert, CircleCheck, CircleX, ConciergeBell, Copy, CreditCard, LucideIcon, User, UtensilsCrossed } from "lucide-react";
import { useReducedMotion } from "../lib/motion";
import OrderPanel from "./OrderPanel";
import PageHero from "./PageHero";

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

export default function OrderView({ seed, active = true }: { seed?: { dish: string; n: number } | null; active?: boolean }) {
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

  // A dish picked on the home page lands in the composer once the agent is ready for an order.
  const seeded = useRef(0);
  useEffect(() => {
    if (!seed || seed.n === seeded.current || session?.waiting_for !== "order" || busy || session.busy) return;
    seeded.current = seed.n;
    addDish(seed.dish);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed, session?.waiting_for, session?.busy, busy]);

  const messages: ChatMessage[] = session?.messages ?? [];
  // The backend keeps no message times, so stamp each message when it first
  // arrives here. Ones restored from an earlier visit get no time and no typing.
  const arrived = useRef<{ id: string | null; at: (Date | null)[] }>({ id: null, at: [] });
  if (session) {
    const seen = arrived.current;
    if (seen.id === null) seen.at = messages.map(() => null);
    else if (seen.id !== session.session_id) seen.at = [];
    seen.id = session.session_id;
    while (seen.at.length < messages.length) seen.at.push(new Date());
  }
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
    <>
      <PageHero
        compact
        active={active}
        scene="dining"
        eyebrow="Table service"
        title="What are you craving?"
        lede="Type it the way you'd say it to a waiter, or tap a dish on the menu."
      />
      <div className="order-layout rise" style={{ animationDelay: "150ms" }}>
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
              <Message key={`${session?.session_id}-${i}`} message={m} at={arrived.current.at[i] ?? null} />
            ))}
            {pending && <Message message={{ role: "user", content: pending }} at={null} />}
            {working && (
              <div className="msg msg-assistant">
                <span className="avatar avatar-live" aria-hidden>
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
    </>
  );
}

// Bubbles adapted from 21st.dev "AI Message Bubble" (elements-): role avatars,
// a time under each message, copy on hover, and a cursor while a fresh reply
// types itself out.
function Message({ message, at }: { message: ChatMessage; at: Date | null }) {
  if (message.role === "user") {
    return (
      <div className="msg msg-user" role="article" aria-label="Your message">
        <div className="bubble">
          {message.content}
          {at && <MessageTime at={at} />}
        </div>
        <span className="avatar avatar-user" aria-hidden>
          <User size={15} />
        </span>
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
    <div className="msg msg-assistant" role="article" aria-label="DineGraph says">
      <span className="avatar" aria-hidden>
        <meta.Icon size={16} />
      </span>
      <div className="bubble">
        <TypedText text={message.content} animate={at !== null} />
        {at && <MessageTime at={at} />}
      </div>
      <CopyButton text={message.content} />
    </div>
  );
}

function MessageTime({ at }: { at: Date }) {
  return (
    <time className="msg-time" dateTime={at.toISOString()}>
      {at.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
    </time>
  );
}

// Reveals a new reply over at most ~0.9s. Screen readers get the whole text at
// once from the hidden copy, not every intermediate frame.
function TypedText({ text, animate }: { text: string; animate: boolean }) {
  const reduced = useReducedMotion();
  const [count, setCount] = useState(animate && !reduced ? 0 : text.length);
  const cursor = useRef<HTMLSpanElement>(null);

  // The bubble grows as it types; keep the chat pinned to the bottom unless
  // the reader has scrolled up.
  useEffect(() => {
    const box = cursor.current?.closest<HTMLElement>(".chat-scroll");
    if (box && box.scrollHeight - box.scrollTop - box.clientHeight < 120) box.scrollTop = box.scrollHeight;
  }, [count]);

  useEffect(() => {
    if (count >= text.length) return;
    const total = Math.min(text.length * 14, 900);
    const start = performance.now() - (count / text.length) * total;
    let raf = 0;
    const tick = (now: number) => {
      const n = Math.min(text.length, Math.ceil(((now - start) / total) * text.length));
      setCount(n);
      if (n < text.length) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  if (count >= text.length) return <>{text}</>;
  return (
    <>
      <span className="sr-only">{text}</span>
      <span aria-hidden>
        {text.slice(0, count)}
        <span className="msg-cursor" ref={cursor} />
      </span>
    </>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be refused (http, permissions); nothing to undo.
    }
  };
  return (
    <button type="button" className="msg-copy" onClick={copy} aria-label={copied ? "Copied" : "Copy message"} title={copied ? "Copied" : "Copy"}>
      {copied ? <Check size={14} aria-hidden /> : <Copy size={14} aria-hidden />}
    </button>
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
