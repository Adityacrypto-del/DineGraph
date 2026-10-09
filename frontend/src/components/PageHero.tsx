// The banner at the top of every page after Home: a slowly drifting photo
// behind a dark veil, with the headline rising in word by word like the hero.
import { ReactNode, useRef } from "react";
import gsap from "gsap";
import { Scene, scenePhoto } from "../lib/dishes";
import { useGSAP, useReducedMotion } from "../lib/motion";

interface Props {
  eyebrow: ReactNode;
  title: string;
  lede?: ReactNode;
  scene: Scene;
  compact?: boolean;
  /** Replays the entrance when this turns true, for views kept mounted while hidden. */
  active?: boolean;
  children?: ReactNode;
}

export default function PageHero({ eyebrow, title, lede, scene, compact, active = true, children }: Props) {
  const root = useRef<HTMLElement>(null);
  const reduced = useReducedMotion();

  useGSAP(
    () => {
      if (reduced || !active) return;
      gsap.fromTo(".ph-photo", { scale: 1.16 }, { scale: 1, duration: 2.2, ease: "power2.out" });
      gsap.from(".ph-word", { yPercent: 110, opacity: 0, duration: 0.8, stagger: 0.06, ease: "power3.out", delay: 0.1 });
      gsap.from(".ph-fade", { y: 14, opacity: 0, duration: 0.7, stagger: 0.08, ease: "power2.out", delay: 0.35 });
    },
    { dependencies: [reduced, active], scope: root },
  );

  return (
    <header ref={root} className={`page-hero ${compact ? "is-compact" : ""}`}>
      <div className="ph-media" aria-hidden>
        <img className="ph-photo" src={scenePhoto(scene)} alt="" />
      </div>
      <div className="ph-veil" aria-hidden />
      <div className="ph-copy">
        <div className="ph-text">
          <p className="eyebrow ph-fade">{eyebrow}</p>
          <h1 className="ph-title" aria-label={title}>
            {title.split(" ").map((w, i) => (
              <span key={i} className="hero-mask" aria-hidden>
                <span className="ph-word">{w}</span>
              </span>
            ))}
          </h1>
          {lede && <p className="ph-lede ph-fade">{lede}</p>}
        </div>
        {children && <div className="ph-side ph-fade">{children}</div>}
      </div>
    </header>
  );
}
