import { useEffect, useState } from "react";
import { Check, X } from "lucide-react";
import { api, clock, Counters, MAX_RETRIES, MenuView, OrderEvent, rupees, SessionView, statusLabel, statusTone } from "../api";

const STAGES = ["Order", "Confirm", "Cook", "Serve", "Pay"];

// Which pipeline stage the graph is at, and whether it ended there with a failure.
function stageOf(s: SessionView): { index: number; failed: boolean } {
  const byReason: Record<string, number> = {
    cook_attempts_exhausted: 2,
    serve_attempts_exhausted: 3,
    payment_attempts_exhausted: 4,
    order_attempts_exhausted: 1,
    cancelled_by_user: 1,
  };
  if (s.status === "FAILED" || s.status === "CANCELLED") {
    const reason = s.final_result.replace(/^NOT_COMPLETED:\s*/, "");
    return { index: byReason[reason] ?? 0, failed: true };
  }
  // a slow kitchen: the step about to run tells us more than the status does
  if (s.next_step === "cook") return { index: 2, failed: false };
  if (s.next_step === "serve") return { index: 3, failed: false };
  const byStatus: Record<string, number> = {
    NEW: 0, INVALID: 0, PLACED: 0,
    CONFIRMED: 1, PARTIAL: 1, NOT_AVAILABLE: 1,
    COOK_FAILED: 2,
    READY: 3, SERVE_FAILED: 3,
    COMPLETE: 4, PAYMENT_PENDING: 4, PAYMENT_FAILED: 4,
    PAID: 5,
  };
  return { index: byStatus[s.status] ?? 0, failed: false };
}

const COUNTER_LABELS: [keyof Counters, string][] = [
  ["order_retries", "Order attempts"],
  ["cook_retries", "Cook attempts"],
  ["serve_retries", "Serve attempts"],
  ["payment_retries", "Payment attempts"],
];

interface Props {
  session: SessionView | null;
  menu: MenuView | null;
  canPick: boolean;
  busy: boolean;
  onPickDish: (dish: string) => void;
  onNew: () => void;
}

export default function OrderPanel({ session, menu, canPick, busy, onPickDish, onNew }: Props) {
  const stage = session ? stageOf(session) : { index: 0, failed: false };

  return (
    <aside className="panel">
      <div className="card">
        <div className="card-head">
          <h2>
            Your order{session?.table ? <span className="muted small"> · Table {session.table}</span> : null}
          </h2>
          {session && <span className={`pill pill-${statusTone(session.status)}`}>{statusLabel(session.status)}</span>}
        </div>

        <ol className="pipeline" aria-label="Order progress">
          {STAGES.map((name, i) => {
            const state =
              i < stage.index ? "done" : i === stage.index ? (stage.failed ? "failed" : session?.done ? "done" : "current") : "todo";
            return (
              <li key={name} className={`step step-${state}`} aria-current={state === "current" ? "step" : undefined}>
                <span className="dot">{state === "done" ? <Check size={14} strokeWidth={3} aria-hidden /> : state === "failed" ? <X size={14} strokeWidth={3} aria-hidden /> : i + 1}</span>
                <span>{name}</span>
              </li>
            );
          })}
        </ol>

        {session && session.order.length > 0 ? (
          <table className="lines">
            <thead>
              <tr>
                <th>Dish</th>
                <th className="num">Wanted</th>
                <th className="num">In stock</th>
              </tr>
            </thead>
            <tbody>
              {session.order.map((l) => (
                <tr key={l.dish} className={l.available_quantity < l.required_quantity ? "short" : ""}>
                  <td>
                    {l.dish}
                    {l.note && <span className="note">{l.note}</span>}
                  </td>
                  <td className="num">{l.required_quantity}</td>
                  <td className="num">{l.available_quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="empty">No dishes yet. Type an order or tap the menu below.</p>
        )}

        {session && session.bill_total > 0 && (
          <div className="bill">
            <span>Bill total</span>
            <strong>{rupees(session.bill_total)}</strong>
            {session.payment_method && <span className="muted">via {session.payment_method.toUpperCase()}</span>}
          </div>
        )}

        {session && (
          <div className="counters">
            {COUNTER_LABELS.map(([key, label]) => (
              <div key={key} className="counter" title={`${session.counters[key]} of ${MAX_RETRIES[key]} left`}>
                <span>{label}</span>
                <span className="pips">
                  {Array.from({ length: MAX_RETRIES[key] }, (_, i) => (
                    <i key={i} className={i < session.counters[key] ? "on" : ""} />
                  ))}
                </span>
              </div>
            ))}
          </div>
        )}

        {session && !session.done && (
          <button className="btn btn-ghost btn-block" disabled={busy} onClick={onNew}>
            Start over
          </button>
        )}
      </div>

      {session && <Timeline session={session} />}

      <div className="card">
        <div className="card-head">
          <h2>Menu</h2>
          <span className="muted small">Up to {menu?.max_dishes ?? 3} dishes</span>
        </div>
        {!menu ? (
          <p className="empty">Loading menu…</p>
        ) : (
          <ul className="menu">
            {menu.items.map((item) => (
              <li key={item.dish}>
                <button
                  className="menu-item"
                  disabled={!canPick}
                  onClick={() => onPickDish(item.dish)}
                  title={canPick ? `Add ${item.dish} to your message` : undefined}
                >
                  <span className="menu-name">{item.dish}</span>
                  <span className="menu-price">{rupees(item.price)}</span>
                  <span className={`stock ${item.available === 0 ? "stock-out" : item.available <= 2 ? "stock-low" : ""}`}>
                    {item.available === 0 ? "Sold out" : `${item.available} left`}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}

// The order's activity log from the server, refreshed whenever the session moves on.
function Timeline({ session }: { session: SessionView }) {
  const [events, setEvents] = useState<OrderEvent[]>([]);
  const id = session.session_id;
  const tick = `${session.messages.length}/${session.status}/${session.next_step}`;

  useEffect(() => {
    let live = true;
    api
      .events(id)
      .then((e) => live && setEvents(e))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [id, tick]);

  if (events.length === 0) return null;
  return (
    <div className="card">
      <div className="card-head">
        <h2>Tracking</h2>
      </div>
      <ol className="timeline">
        {events.map((e, i) => (
          <li key={i} className={`tl tl-${statusTone(e.status)}`}>
            <time dateTime={e.at}>{clock(e.at)}</time>
            <span>{e.detail}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
