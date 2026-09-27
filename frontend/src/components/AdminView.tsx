import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, ApiError, MenuItem, rupees, Stats } from "../api";

const TOKEN_KEY = "dinegraph.adminToken";

function loadToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export default function AdminView() {
  const [token, setToken] = useState(loadToken);
  const [stats, setStats] = useState<Stats | null>(null);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const report = (e: unknown) => {
    const err = e as Error;
    setError(
      e instanceof ApiError && e.status === 401
        ? "The server needs an admin token. Enter the value of DINEGRAPH_ADMIN_TOKEN above."
        : err.message,
    );
  };

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, m] = await Promise.all([api.stats(token || undefined), api.menu()]);
      setStats(s);
      setItems(m.items);
    } catch (e) {
      report(e);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  function saveToken(value: string) {
    setToken(value);
    try {
      sessionStorage.setItem(TOKEN_KEY, value);
    } catch {
      /* ignore */
    }
  }

  async function save(dish: string, body: { quantity?: number; price?: number }) {
    setError(null);
    setNotice(null);
    try {
      const item = await api.upsertDish(dish, body, token || undefined);
      setNotice(`Saved ${item.dish}.`);
      await load();
    } catch (e) {
      report(e);
    }
  }

  async function remove(dish: string) {
    if (!confirm(`Remove ${dish} from the menu?`)) return;
    setError(null);
    setNotice(null);
    try {
      await api.deleteDish(dish, token || undefined);
      setNotice(`Removed ${dish}.`);
      await load();
    } catch (e) {
      report(e);
    }
  }

  const methods = stats ? Object.entries(stats.revenue_by_method) : [];
  const maxMethod = Math.max(1, ...methods.map(([, v]) => v));

  return (
    <div className="admin">
      <section className="card wide">
        <div className="card-head">
          <h2>Admin</h2>
          <div className="toolbar">
            <input
              type="password"
              placeholder="Admin token (if set)"
              value={token}
              onChange={(e) => saveToken(e.target.value)}
              aria-label="Admin token"
            />
            <button className="btn btn-small" onClick={load}>
              Refresh
            </button>
          </div>
        </div>
        {error && <div className="alert alert-bad">{error}</div>}
        {notice && <div className="alert alert-good">{notice}</div>}

        {stats && (
          <>
            <div className="stats">
              <Stat label="Revenue" value={rupees(stats.revenue)} />
              <Stat label="Orders" value={stats.total_orders} />
              <Stat label="Completed" value={stats.completed} tone="good" />
              <Stat label="In progress" value={stats.in_progress} />
              <Stat label="Failed" value={stats.failed} tone="bad" />
              <Stat label="Cancelled" value={stats.cancelled} />
            </div>
            {methods.length > 0 && (
              <div className="bars">
                {methods.map(([m, v]) => (
                  <div key={m} className="bar-row">
                    <span>{m.toUpperCase()}</span>
                    <div className="bar">
                      <i style={{ width: `${(v / maxMethod) * 100}%` }} />
                    </div>
                    <span className="num">{rupees(v)}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </section>

      <section className="card wide">
        <div className="card-head">
          <h2>Menu and stock</h2>
        </div>
        <div className="table-wrap">
          <table className="orders">
            <thead>
              <tr>
                <th>Dish</th>
                <th className="num">Stock</th>
                <th className="num">Price (₹)</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <EditRow key={`${i.dish}-${i.available}-${i.price}`} item={i} onSave={save} onDelete={remove} />
              ))}
            </tbody>
          </table>
        </div>
        <AddDish onAdd={(dish, quantity, price) => save(dish, { quantity, price })} />
      </section>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string | number; tone?: "good" | "bad" }) {
  return (
    <div className={`stat ${tone ? `stat-${tone}` : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EditRow({
  item,
  onSave,
  onDelete,
}: {
  item: MenuItem;
  onSave: (dish: string, body: { quantity?: number; price?: number }) => void;
  onDelete: (dish: string) => void;
}) {
  const [qty, setQty] = useState(String(item.available));
  const [price, setPrice] = useState(String(item.price));
  const q = Number(qty);
  const p = Number(price);
  const valid = qty !== "" && price !== "" && Number.isInteger(q) && Number.isInteger(p) && q >= 0 && p >= 0;
  const changed = q !== item.available || p !== item.price;

  return (
    <tr>
      <td>{item.dish}</td>
      <td className="num">
        <input className="num-input" type="number" min={0} value={qty} onChange={(e) => setQty(e.target.value)} aria-label={`${item.dish} stock`} />
      </td>
      <td className="num">
        <input className="num-input" type="number" min={0} value={price} onChange={(e) => setPrice(e.target.value)} aria-label={`${item.dish} price`} />
      </td>
      <td className="actions">
        <button className="btn btn-small btn-primary" disabled={!valid || !changed} onClick={() => onSave(item.dish, { quantity: q, price: p })}>
          Save
        </button>
        <button className="btn btn-small btn-ghost" onClick={() => onDelete(item.dish)}>
          Remove
        </button>
      </td>
    </tr>
  );
}

function AddDish({ onAdd }: { onAdd: (dish: string, quantity: number, price: number) => void }) {
  const [dish, setDish] = useState("");
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!dish.trim() || qty === "" || price === "") return;
    onAdd(dish.trim(), Number(qty), Number(price));
    setDish("");
    setQty("");
    setPrice("");
  }

  return (
    <form className="add-dish" onSubmit={submit}>
      <input placeholder="New dish name" value={dish} onChange={(e) => setDish(e.target.value)} aria-label="New dish name" />
      <input type="number" min={0} placeholder="Stock" value={qty} onChange={(e) => setQty(e.target.value)} aria-label="New dish stock" />
      <input type="number" min={0} placeholder="Price ₹" value={price} onChange={(e) => setPrice(e.target.value)} aria-label="New dish price" />
      <button className="btn btn-primary" disabled={!dish.trim() || qty === "" || price === ""}>
        Add dish
      </button>
    </form>
  );
}
