import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ChefHat, ClipboardList, House, LucideIcon, MessageSquareText, Settings2, UtensilsCrossed } from "lucide-react";
import { api, Health } from "./api";
import AdminView from "./components/AdminView";
import FlowField from "./components/fx/FlowField";
import HomeView from "./components/HomeView";
import KitchenView from "./components/KitchenView";
import OrderView from "./components/OrderView";
import OrdersView from "./components/OrdersView";

const TABS: readonly { id: string; label: string; Icon: LucideIcon }[] = [
  { id: "home", label: "Home", Icon: House },
  { id: "order", label: "Order", Icon: MessageSquareText },
  { id: "kitchen", label: "Kitchen", Icon: ChefHat },
  { id: "orders", label: "Orders", Icon: ClipboardList },
  { id: "admin", label: "Admin", Icon: Settings2 },
] as const;
type Tab = "home" | "order" | "kitchen" | "orders" | "admin";
const LLM_NAME: Record<string, string> = { RuleBasedLLM: "Offline mode", GeminiLLM: "Gemini", ClaudeLLM: "Claude" };
const FIELD_FOCUS: [number, number] = [0.5, 0.35];

export default function App() {
  // the URL hash picks the tab, so a kitchen display can open straight to #kitchen
  const fromHash = (): Tab => (TABS.find((t) => "#" + t.id === window.location.hash)?.id as Tab) ?? "home";
  const [tab, setTabState] = useState<Tab>(fromHash);
  const [seed, setSeed] = useState<{ dish: string; n: number } | null>(null);
  const setTab = (t: Tab) => {
    setTabState(t);
    history.replaceState(null, "", t === "home" ? window.location.pathname : "#" + t);
    window.scrollTo({ top: 0 });
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

  // A pill slides under the active tab.
  const nav = useRef<HTMLElement>(null);
  const [pill, setPill] = useState<{ left: number; width: number } | null>(null);
  useLayoutEffect(() => {
    const measure = () => {
      const el = nav.current?.querySelector<HTMLElement>('[aria-selected="true"]');
      if (el) setPill({ left: el.offsetLeft, width: el.offsetWidth });
    };
    measure();
    window.addEventListener("resize", measure);
    void document.fonts?.ready.then(measure);
    return () => window.removeEventListener("resize", measure);
  }, [tab]);

  const addDish = (dish: string) => {
    setSeed((s) => ({ dish, n: (s?.n ?? 0) + 1 }));
    setTab("order");
  };

  return (
    <div className={`app app-${tab}`}>
      {tab !== "home" && <FlowField className="ambient" density={0.55} speed={0.5} focus={FIELD_FOCUS} pull={0.0006} />}

      <header className="topbar">
        <div className="container topbar-inner">
          <button className="brand" onClick={() => setTab("home")} aria-label="DineGraph home">
            <span className="logo" aria-hidden>
              <UtensilsCrossed size={20} />
            </span>
            <span className="brand-name">DineGraph</span>
          </button>
          <nav className="tabs" role="tablist" ref={nav}>
            {pill && <span className="tab-pill" style={{ transform: `translateX(${pill.left}px)`, width: pill.width }} aria-hidden />}
            {TABS.map((t) => (
              <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id as Tab)}>
                <t.Icon size={16} aria-hidden />
                <span className="tab-label">{t.label}</span>
              </button>
            ))}
          </nav>
          <span className={`health ${health === "down" ? "down" : health ? "up" : ""}`} role="status">
            {health === "down" ? "Server offline" : health ? (LLM_NAME[health.llm] ?? health.llm) : "Connecting…"}
          </span>
        </div>
      </header>

      <main>
        {tab === "home" && <HomeView health={health} onNavigate={setTab} onAddDish={addDish} />}
        <div className="container view">
          {/* Keep the order view mounted so the conversation survives tab switches. */}
          <div hidden={tab !== "order"} className="view-enter">
            <OrderView seed={seed} active={tab === "order"} />
          </div>
          {tab === "kitchen" && (
            <div className="view-enter">
              <KitchenView kitchenSeconds={health && health !== "down" ? health.kitchen_seconds : 0} />
            </div>
          )}
          {tab === "orders" && (
            <div className="view-enter">
              <OrdersView />
            </div>
          )}
          {tab === "admin" && (
            <div className="view-enter">
              <AdminView />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
