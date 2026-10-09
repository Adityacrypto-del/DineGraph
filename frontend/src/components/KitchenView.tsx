import { useEffect, useState } from "react";
import { ChefHat, ConciergeBell, CreditCard, LucideIcon } from "lucide-react";
import { api, KitchenStage, KitchenTicket, rupees } from "../api";
import PageHero from "./PageHero";

const POLL_MS = 2000;

const COLUMNS: { stage: KitchenStage; title: string; Icon: LucideIcon; empty: string }[] = [
  { stage: "cooking", title: "Cooking", Icon: ChefHat, empty: "Nothing on the stove." },
  { stage: "serving", title: "Ready to serve", Icon: ConciergeBell, empty: "No plates waiting." },
  { stage: "paying", title: "Awaiting payment", Icon: CreditCard, empty: "No open bills." },
];

// "3 min" since the order was placed, measured against `now` so it ticks with the poll.
function age(iso: string, now: number) {
  const secs = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)} min`;
}

// How far through its current step a ticket is, from the configured kitchen time.
function stepProgress(t: KitchenTicket, now: number, seconds: number) {
  if (t.stage === "paying" || seconds <= 0) return null;
  const elapsed = (now - new Date(t.updated_at).getTime()) / 1000;
  return Math.min(1, Math.max(0, elapsed / seconds));
}

const LATE_MIN = 10;

export default function KitchenView({ kitchenSeconds = 0 }: { kitchenSeconds?: number }) {
  const [tickets, setTickets] = useState<KitchenTicket[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    let live = true;
    const load = () =>
      api
        .kitchen()
        .then((t) => {
          if (!live) return;
          setTickets(t);
          setError(null);
          setNow(Date.now());
        })
        .catch((e) => live && setError((e as Error).message));
    void load();
    const t = setInterval(load, POLL_MS);
    return () => {
      live = false;
      clearInterval(t);
    };
  }, []);

  return (
    <section className="kitchen">
      <PageHero
        scene="kitchen"
        eyebrow="Live board"
        title="The kitchen pass."
        lede="Tickets move from the stove to the table to the till as the agent works each order."
      >
        <span className="live-chip">
          <span className="live-dot" aria-hidden /> Live · every {POLL_MS / 1000}s
        </span>
      </PageHero>
      {error && <div className="alert alert-bad">{error}</div>}
      <div className="kitchen-board">
        {COLUMNS.map(({ stage, title, Icon, empty }, col) => {
          const column = (tickets ?? []).filter((t) => t.stage === stage);
          return (
            <div key={stage} className={`kitchen-col kitchen-${stage} rise`} style={{ animationDelay: `${200 + col * 90}ms` }}>
              <h3>
                <Icon size={18} aria-hidden /> {title}
                <span className="count">{column.length}</span>
              </h3>
              {tickets === null ? (
                <p className="empty">Loading…</p>
              ) : column.length === 0 ? (
                <p className="empty">{empty}</p>
              ) : (
                column.map((t, i) => {
                  const progress = stepProgress(t, now, kitchenSeconds);
                  const late = (now - new Date(t.created_at).getTime()) / 60000 > LATE_MIN;
                  return (
                  <article key={t.session_id} className={`ticket ${late ? "ticket-late" : ""}`} style={{ animationDelay: `${i * 50}ms` }}>
                    <header>
                      <strong>{t.table ? `Table ${t.table}` : "Takeaway"}</strong>
                      <span className="muted small">
                        #{t.session_id.slice(0, 6)} · {age(t.created_at, now)}
                      </span>
                    </header>
                    <ul>
                      {t.items.map((i) => (
                        <li key={i.dish}>
                          <span className="qty">{i.required_quantity}×</span> {i.dish}
                          {i.note && <span className="note">{i.note}</span>}
                        </li>
                      ))}
                    </ul>
                    {progress !== null && (
                      <div className="ticket-progress" role="progressbar" aria-label={`${title} progress`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}>
                        <i style={{ transform: `scaleX(${progress})` }} />
                      </div>
                    )}
                    {stage === "paying" && t.bill_total > 0 && <footer>{rupees(t.bill_total)}</footer>}
                  </article>
                  );
                })
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
