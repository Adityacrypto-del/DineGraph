import { useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import { ArrowRight, ChefHat, Flame, Plus, Soup } from "lucide-react";
import { api, Health, MenuView, rupees } from "../api";
import { AMBIENT_PHOTOS, dishPhoto, dishThumb, PORTRAIT } from "../lib/dishes";
import { useGSAP, useReducedMotion } from "../lib/motion";
import AnimateDigits from "./fx/AnimateDigits";
import FlowField from "./fx/FlowField";
import GraphTimeline from "./fx/GraphTimeline";
import ImageStream from "./fx/ImageStream";
import MorphGallery from "./fx/MorphGallery";

const LLM_NAME: Record<string, string> = { RuleBasedLLM: "Offline mode", GeminiLLM: "Gemini", ClaudeLLM: "Claude" };
const CENTER: [number, number] = [0.5, 0.5];

interface Props {
  health: Health | null | "down";
  onNavigate: (tab: "order" | "kitchen") => void;
  onAddDish: (dish: string) => void;
}

export default function HomeView({ health, onNavigate, onAddDish }: Props) {
  const [menu, setMenu] = useState<MenuView | null>(null);
  const [tickets, setTickets] = useState<number | null>(null);
  const [active, setActive] = useState(0);
  const hero = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    let live = true;
    const load = () => {
      api.menu().then((m) => live && setMenu(m)).catch(() => undefined);
      api.kitchen().then((t) => live && setTickets(t.length)).catch(() => undefined);
    };
    load();
    const t = setInterval(load, 5000);
    return () => {
      live = false;
      clearInterval(t);
    };
  }, []);

  // Headline words rise in one after another, like the gateway card's title.
  useGSAP(
    () => {
      if (reduced) return;
      gsap.from(".hero-word", { yPercent: 110, opacity: 0, duration: 0.9, stagger: 0.07, ease: "power3.out", delay: 0.15 });
      gsap.from(".hero-fade", { y: 16, opacity: 0, duration: 0.8, stagger: 0.1, ease: "power2.out", delay: 0.55 });
    },
    { dependencies: [reduced], scope: hero },
  );

  const items = menu?.items ?? [];
  const corridor = useMemo(() => {
    const dishes = items.map((i) => PORTRAIT(i.dish));
    // Interleave dishes with kitchen shots so neighbouring cards differ.
    return dishes.length ? dishes.flatMap((d, i) => [d, AMBIENT_PHOTOS[i % AMBIENT_PHOTOS.length]]) : AMBIENT_PHOTOS;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.map((i) => i.dish).join("|")]);
  const slides = useMemo(
    () => items.map((i) => ({ src: dishPhoto(i.dish), thumb: dishThumb(i.dish), alt: i.dish })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [items.map((i) => i.dish).join("|")],
  );
  const current = items[Math.min(active, items.length - 1)];
  const inStock = items.filter((i) => i.available > 0).length;
  const llm = health && health !== "down" ? (LLM_NAME[health.llm] ?? health.llm) : health === "down" ? "Server offline" : "Connecting";

  return (
    <div className="home">
      <div ref={hero}>
        <ImageStream images={corridor} className="hero" cards={9} speed={22}>
          <div className="hero-veil" aria-hidden />
          <div className="hero-copy">
            <h1 className="hero-title" aria-label="Order the way you'd tell a waiter.">
              {"Order the way you'd tell a waiter.".split(" ").map((w, i) => (
                <span key={i} className="hero-mask" aria-hidden>
                  <span className="hero-word">{w}</span>
                </span>
              ))}
            </h1>
            <div className="hero-actions hero-fade">
              <button className="btn btn-primary btn-lg" onClick={() => onNavigate("order")}>
                Start an order <ArrowRight size={18} aria-hidden />
              </button>
              <button className="btn btn-glass btn-lg" onClick={() => onNavigate("kitchen")}>
                <ChefHat size={18} aria-hidden /> Watch the kitchen
              </button>
            </div>
            <ul className="hero-stats hero-fade" aria-label="Live status">
              <li>
                <span className={`live-dot ${health === "down" ? "is-down" : ""}`} aria-hidden /> {llm}
              </li>
              <li>
                <Soup size={15} aria-hidden /> <AnimateDigits value={String(inStock)} /> dishes in stock
              </li>
              <li>
                <Flame size={15} aria-hidden /> <AnimateDigits value={String(tickets ?? 0)} /> tickets in the kitchen
              </li>
            </ul>
          </div>
        </ImageStream>
      </div>

      <section className="showcase" aria-labelledby="showcase-title">
        <div className="section-head">
          <p className="eyebrow">Tonight's menu</p>
          <h2 id="showcase-title" className="section-title">
            Pick a dish, we'll write the order.
          </h2>
        </div>
        {slides.length > 0 ? (
          <MorphGallery
            items={slides}
            height="min(68vh, 620px)"
            autoplay={5200}
            label="Tonight's menu"
            className="showcase-gallery"
            onIndexChange={setActive}
            index={active}
            overlay={
              current && (
                <div className="showcase-caption" key={current.dish}>
                  <span className="showcase-count">
                    {String(active + 1).padStart(2, "0")} / {String(items.length).padStart(2, "0")}
                  </span>
                  <h3>{current.dish}</h3>
                  <div className="showcase-meta">
                    <strong>{rupees(current.price)}</strong>
                    <span className={`stock-badge ${current.available === 0 ? "out" : current.available <= 2 ? "low" : ""}`}>
                      {current.available === 0 ? "Sold out" : current.available <= 2 ? `Only ${current.available} left` : `${current.available} left`}
                    </span>
                  </div>
                  <button
                    className="btn btn-primary"
                    disabled={current.available === 0}
                    onPointerDown={(e) => e.stopPropagation()}
                    onPointerUp={(e) => e.stopPropagation()}
                    onClick={() => onAddDish(current.dish)}
                  >
                    <Plus size={18} aria-hidden /> Add to my order
                  </button>
                </div>
              )
            }
          />
        ) : (
          <div className="showcase-empty card">{menu ? "The menu is empty. Add dishes in Admin." : "Loading the menu…"}</div>
        )}
      </section>

      <GraphTimeline />

      <section className="cta-band">
        <FlowField className="cta-field" density={1.4} focus={CENTER} />
        <div className="cta-copy">
          <h2 className="section-title">Hungry yet?</h2>
          <p>Click anywhere in this panel to send a ripple through the field, then go place an order.</p>
          <button className="btn btn-primary btn-lg" onClick={() => onNavigate("order")}>
            Start an order <ArrowRight size={18} aria-hidden />
          </button>
        </div>
      </section>
    </div>
  );
}
