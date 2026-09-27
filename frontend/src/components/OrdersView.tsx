import { useCallback, useEffect, useState } from "react";
import { api, OrderRecord, rupees, statusLabel, statusTone } from "../api";

const FILTERS = ["", "PAID", "FAILED", "CANCELLED", "PAYMENT_PENDING"];
const PAGE = 25;

function when(iso: string) {
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  return isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default function OrdersView() {
  const [status, setStatus] = useState("");
  const [rows, setRows] = useState<OrderRecord[]>([]);
  const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (offset: number) => {
      setLoading(true);
      setError(null);
      try {
        const page = await api.orders(status || undefined, PAGE, offset);
        setRows((prev) => (offset === 0 ? page : [...prev, ...page]));
        setMore(page.length === PAGE);
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [status],
  );

  useEffect(() => {
    void load(0);
  }, [load]);

  return (
    <section className="card wide">
      <div className="card-head">
        <h2>Orders</h2>
        <div className="toolbar">
          <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
            {FILTERS.map((f) => (
              <option key={f} value={f}>
                {f ? statusLabel(f) : "All statuses"}
              </option>
            ))}
          </select>
          <button className="btn btn-small" disabled={loading} onClick={() => load(0)}>
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="alert alert-bad">{error}</div>}

      {rows.length === 0 && !loading ? (
        <p className="empty">No orders yet.</p>
      ) : (
        <div className="table-wrap">
          <table className="orders">
            <thead>
              <tr>
                <th>Updated</th>
                <th>Table</th>
                <th>Items</th>
                <th className="num">Total</th>
                <th>Paid with</th>
                <th>Status</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((o) => (
                <tr key={o.session_id}>
                  <td className="nowrap">{when(o.updated_at)}</td>
                  <td>{o.table ?? "—"}</td>
                  <td>
                    {o.items.length
                      ? o.items.map((i) => `${i.required_quantity}× ${i.dish}${i.note ? ` (${i.note})` : ""}`).join(", ")
                      : "—"}
                  </td>
                  <td className="num">{o.bill_total ? rupees(o.bill_total) : "—"}</td>
                  <td>{o.payment_method ? o.payment_method.toUpperCase() : "—"}</td>
                  <td>
                    <span className={`pill pill-${statusTone(o.status)}`}>{statusLabel(o.status)}</span>
                  </td>
                  <td className="muted small">{o.final_result ? o.final_result.replace(/_/g, " ") : "In progress"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {more && (
        <button className="btn btn-ghost btn-block" disabled={loading} onClick={() => load(rows.length)}>
          Load more
        </button>
      )}
    </section>
  );
}
