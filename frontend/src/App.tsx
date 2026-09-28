import { useEffect, useState } from "react";
import { UtensilsCrossed } from "lucide-react";
import { api, Health } from "./api";
import AdminView from "./components/AdminView";
import KitchenView from "./components/KitchenView";
import OrderView from "./components/OrderView";
import OrdersView from "./components/OrdersView";

const TABS = [
  { id: "order", label: "Order" },
  { id: "kitchen", label: "Kitchen" },
  { id: "orders", label: "Orders" },
  { id: "admin", label: "Admin" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export default function App() {
  // the URL hash picks the tab, so a kitchen display can open straight to #kitchen
  const fromHash = (): Tab => TABS.find((t) => "#" + t.id === window.location.hash)?.id ?? "order";
  const [tab, setTabState] = useState<Tab>(fromHash);
  const setTab = (t: Tab) => {
    setTabState(t);
    history.replaceState(null, "", t === "order" ? window.location.pathname : "#" + t);
  };

  useEffect(() => {
    const onHash = () => setTabState(fromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const [health, setHealth] = useState<Health | null | "down">(null);

  useEffect(() => {
    const check = () => api.health().then(setHealth).catch(() => setHealth("down"));
    void check();
    const t = setInterval(check, 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo" aria-hidden>
            <UtensilsCrossed size={22} />
          </span>
          <div>
            <h1>DineGraph</h1>
            <p>Order, cook, serve and pay, run by a LangGraph agent</p>
          </div>
        </div>
        <nav className="tabs" role="tablist">
          {TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
        <span className={`health ${health === "down" ? "down" : health ? "up" : ""}`}>
          {health === "down" ? "Server offline" : health ? (({ RuleBasedLLM: "Offline mode", GeminiLLM: "Gemini", ClaudeLLM: "Claude" }[health.llm] ?? health.llm)) : "Connecting…"}
        </span>
      </header>

      <main>
        {/* Keep the order view mounted so the conversation survives tab switches. */}
        <div hidden={tab !== "order"}>
          <OrderView />
        </div>
        {tab === "kitchen" && <KitchenView />}
        {tab === "orders" && <OrdersView />}
        {tab === "admin" && <AdminView />}
      </main>
    </div>
  );
}
