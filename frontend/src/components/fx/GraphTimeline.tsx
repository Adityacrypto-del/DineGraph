// Adapted from Peak-frontends 06-scroll-timeline. The section pins while the
// page scrolls, sliding a track of steps sideways; the rail draws itself, and
// each step's stem, dot and SplitText lines rise as it crosses the viewport.
// Under reduced motion it becomes a plain, swipeable row with nothing hidden.
import { useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import { ChefHat, ClipboardCheck, ConciergeBell, CreditCard, LucideIcon, MessageSquareText, PackageCheck, Split, Sparkles } from "lucide-react";
import { useGSAP, useReducedMotion } from "../../lib/motion";

gsap.registerPlugin(ScrollTrigger, SplitText);

interface Step { node: string; title: string; body: string; Icon: LucideIcon; retries?: string }

export const GRAPH_STEPS: Step[] = [
  { node: "take_order", title: "Take the order", body: "A guest types the way they talk: “two dosas and a cold coffee, no sugar”.", Icon: MessageSquareText, retries: "3 attempts" },
  { node: "parse_order", title: "Understand it", body: "The LLM turns the message into dishes, quantities and notes, and ignores anything that isn't food.", Icon: Sparkles },
  { node: "order_confirm", title: "Check the menu", body: "Each dish is marked fully available, partly available, or sold out against live stock.", Icon: ClipboardCheck },
  { node: "user_decision", title: "Ask when it's partial", body: "The graph pauses for the guest: take what's there, order again, or cancel.", Icon: Split },
  { node: "reserve_stock", title: "Reserve stock", body: "Confirmed dishes take shared stock, so two tables can never buy the last plate.", Icon: PackageCheck },
  { node: "cook", title: "Cook", body: "The kitchen fires the ticket. A burnt dish is retried before anyone apologises.", Icon: ChefHat, retries: "2 attempts" },
  { node: "serve", title: "Serve", body: "The waiter carries it out. A dropped plate goes back to the kitchen.", Icon: ConciergeBell, retries: "2 attempts" },
  { node: "pay", title: "Settle the bill", body: "An itemised bill, then cash, card or UPI, with a retry if the card declines.", Icon: CreditCard, retries: "2 attempts" },
];

export default function GraphTimeline() {
  const section = useRef<HTMLElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

  useGSAP(
    () => {
      const el = section.current;
      const row = track.current;
      if (!el || !row || reduced) return;

      const distance = () => Math.max(0, row.scrollWidth - window.innerWidth);
      const slide = gsap.to(row, {
        x: () => -distance(),
        ease: "none",
        scrollTrigger: { trigger: el, start: "top top", end: () => `+=${distance()}`, pin: true, scrub: 0.6, invalidateOnRefresh: true },
      });

      gsap.fromTo(".gt-rail-fill", { scaleX: 0 }, { scaleX: 1, ease: "none", scrollTrigger: { trigger: el, start: "top top", end: () => `+=${distance()}`, scrub: 0.6 } });

      const splits: SplitText[] = [];
      gsap.utils.toArray<HTMLElement>(".gt-step", el).forEach((step) => {
        const reveal = { trigger: step, containerAnimation: slide, start: "left 92%", end: "left 52%", scrub: 0.5 };
        gsap.fromTo(step.querySelector(".gt-stem"), { scaleY: 0 }, { scaleY: 1, ease: "none", scrollTrigger: reveal });
        gsap.fromTo(step.querySelector(".gt-dot"), { scale: 0 }, { scale: 1, ease: "back.out(2)", scrollTrigger: reveal });
        gsap.fromTo(step.querySelector(".gt-icon"), { scale: 0.4, rotate: -30, opacity: 0 }, { scale: 1, rotate: 0, opacity: 1, scrollTrigger: reveal });
        step.querySelectorAll<HTMLElement>(".gt-split").forEach((text) => {
          const split = SplitText.create(text, {
            type: "lines",
            mask: "lines",
            autoSplit: true,
            onSplit: (self) => gsap.from(self.lines, { yPercent: 110, stagger: 0.08, ease: "power2.out", scrollTrigger: reveal }),
          });
          splits.push(split);
        });
      });

      // Fonts and photos change widths after first paint; measure again.
      void document.fonts?.ready.then(() => ScrollTrigger.refresh());
      return () => splits.forEach((s) => s.revert());
    },
    { dependencies: [reduced], scope: section },
  );

  return (
    <section ref={section} className={`gt ${reduced ? "gt-static" : ""}`} aria-labelledby="gt-title">
      <div ref={track} className="gt-track">
        <header className="gt-intro">
          <p className="eyebrow">Under the hood</p>
          <h2 id="gt-title" className="gt-title">One order, eight nodes.</h2>
          <p className="gt-lede">Every order is a run through a LangGraph state machine. Scroll to follow one from the first message to the receipt.</p>
        </header>
        <div className="gt-line">
          <div className="gt-rail" aria-hidden>
            <span className="gt-rail-fill" />
          </div>
          <ol className="gt-steps">
          {GRAPH_STEPS.map((s, i) => (
            <li key={s.node} className={`gt-step ${i % 2 ? "gt-low" : "gt-high"}`}>
              <span className="gt-stem" aria-hidden />
              <span className="gt-dot" aria-hidden />
              <div className="gt-card">
                <span className="gt-icon" aria-hidden>
                  <s.Icon size={22} />
                </span>
                <code className="gt-node">
                  {String(i + 1).padStart(2, "0")} · {s.node}
                </code>
                <h3 className="gt-split">{s.title}</h3>
                <p className="gt-split">{s.body}</p>
                {s.retries && <span className="gt-retry">{s.retries}</span>}
              </div>
            </li>
          ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
