// Ported from Peak-frontends 05-image-stream-hero.
//
// Two rails of cards ride from far behind the screen toward the viewer.
// Perspective alone makes each card grow and sweep outward from the vanishing
// point. Depth is authored as apparent size (geometric), the rails open hard
// then hold (`fan` > 1), and each card is born across the axis so the centre
// never opens up. Every length is in cqw, so the corridor keeps its shape at
// any container width.
import { CSSProperties, ReactNode, useId, useMemo } from "react";

const PATH = {
  perspective: 30,
  cardWidth: 18,
  cardHeight: 25,
  cardRadius: 0.6,
  birthHeight: 2.6,
  exitHeight: 46,
  railBirth: -11,
  railExit: 44,
  fan: 3.3,
  turnBirth: 6,
  turnExit: 28,
  stops: 24,
};
type Path = typeof PATH;

// Sample the path once so the CSS keyframes trace the real curve.
function keyframes(dir: 1 | -1, name: string, p: Path) {
  const steps: string[] = [];
  for (let s = 0; s <= p.stops; s++) {
    const u = s / p.stops;
    const scale = (p.birthHeight / p.cardHeight) * Math.pow(p.exitHeight / p.birthHeight, u);
    const z = p.perspective * (1 - 1 / scale);
    const rail = p.railExit - (p.railExit - p.railBirth) * Math.pow(1 - u, p.fan);
    const turn = p.turnBirth + (p.turnExit - p.turnBirth) * u;
    steps.push(
      `${(u * 100).toFixed(2)}%{transform:translate3d(${(dir * rail).toFixed(2)}cqw,0,${z.toFixed(2)}cqw) rotateY(${(-dir * turn).toFixed(2)}deg)}`,
    );
  }
  return `@keyframes ${name}{${steps.join("")}}`;
}

interface Props {
  images: string[];
  /** Cards on each rail at once. */
  cards?: number;
  /** Seconds for one card to travel the corridor. */
  speed?: number;
  /** Vertical placement of the axis, as a percentage of height. */
  axis?: number;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
}

export default function ImageStream({ images, cards = 9, speed = 18, axis = 55, children, className, style }: Props) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const right = `ish-r-${id}`;
  const left = `ish-l-${id}`;
  const card = `ish-c-${id}`;

  // Pausing rather than disabling keeps the corridor whole under reduced motion:
  // every card is already placed mid-flight by its negative delay.
  const css = useMemo(
    () =>
      keyframes(1, right, PATH) +
      keyframes(-1, left, PATH) +
      `@media(prefers-reduced-motion:reduce){.${card}{animation-play-state:paused!important}}`,
    [right, left, card],
  );

  return (
    <div className={className} style={{ position: "relative", overflow: "hidden", containerType: "inline-size", ...style }}>
      <style>{css}</style>
      <div
        aria-hidden
        style={{ position: "absolute", inset: 0, pointerEvents: "none", perspective: `${PATH.perspective}cqw`, perspectiveOrigin: `50% ${axis}%` }}
      >
        <div style={{ position: "absolute", inset: 0, transformStyle: "preserve-3d" }}>
          {[right, left].map((name) =>
            Array.from({ length: cards }, (_, i) => {
              const src = images[i % Math.max(images.length, 1)];
              return (
                <div
                  key={`${name}-${i}`}
                  className={card}
                  style={{
                    position: "absolute",
                    overflow: "hidden",
                    left: "50%",
                    top: `${axis}%`,
                    width: `${PATH.cardWidth}cqw`,
                    height: `${PATH.cardHeight}cqw`,
                    marginLeft: `${-PATH.cardWidth / 2}cqw`,
                    marginTop: `${-PATH.cardHeight / 2}cqw`,
                    borderRadius: `${PATH.cardRadius}cqw`,
                    animation: `${name} ${speed}s linear infinite`,
                    animationDelay: `${-(i * speed) / cards}s`,
                    backfaceVisibility: "hidden",
                    background: "#2a1512",
                  }}
                >
                  {src && (
                    <img src={src} alt="" loading="lazy" decoding="async" draggable={false} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
                  )}
                </div>
              );
            }),
          )}
        </div>
      </div>
      {children}
    </div>
  );
}
