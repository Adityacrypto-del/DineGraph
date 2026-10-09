// Ported from 21st.dev "Animate Digits" (unlumen). The original drives each
// digit with motion/react springs; this keeps its behaviour, where only the
// digits that change blur-slide in while the old ones blur-slide out, but runs
// on CSS keyframes so the app needs no animation library for it.
//
// A rising digit enters from below and a falling one from above. Rapid updates
// are queued and stepped through `stepMs` apart, like the original.
import { useEffect, useRef, useState } from "react";

interface Props {
  value: string;
  className?: string;
  /** "dynamic" picks the direction per digit from whether it went up or down. */
  direction?: "dynamic" | "up" | "down";
  stepMs?: number;
  /** Spoken label; defaults to the value. */
  label?: string;
}

interface Exit { id: number; char: string; up: boolean }

let nextId = 0;

function Cell({ char, direction }: { char: string; direction: Props["direction"] }) {
  const prev = useRef(char);
  const [exits, setExits] = useState<Exit[]>([]);
  const [enter, setEnter] = useState<{ key: number; up: boolean } | null>(null);

  useEffect(() => {
    const before = prev.current;
    prev.current = char;
    if (char === before || !/\d/.test(before) || !/\d/.test(char)) return;
    const up = direction === "dynamic" ? Number(char) > Number(before) : direction === "up";
    const id = nextId++;
    // Keep at most three ghosts, as the original does.
    setExits((q) => [...q, { id, char: before, up }].slice(-3));
    setEnter({ key: id, up });
  }, [char, direction]);

  if (!/\d/.test(char)) return <span className="ad-sep">{char}</span>;
  return (
    <span className="ad-cell">
      {exits.map((e) => (
        <span key={e.id} className={`ad-out ${e.up ? "ad-up" : "ad-down"}`} onAnimationEnd={() => setExits((q) => q.filter((x) => x.id !== e.id))}>
          {e.char}
        </span>
      ))}
      <span key={enter?.key ?? "first"} className={enter ? `ad-in ${enter.up ? "ad-up" : "ad-down"}` : undefined}>
        {char}
      </span>
    </span>
  );
}

export default function AnimateDigits({ value, className, direction = "dynamic", stepMs = 80, label }: Props) {
  const [shown, setShown] = useState(value);
  const queue = useRef<string[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shownRef = useRef(value);

  useEffect(() => {
    if (value === shownRef.current && !queue.current.length) return;
    queue.current.push(value);
    if (timer.current) return;
    const step = () => {
      const next = queue.current.shift();
      if (next === undefined) {
        timer.current = null;
        return;
      }
      shownRef.current = next;
      setShown(next);
      timer.current = setTimeout(step, stepMs);
    };
    step();
  }, [value, stepMs]);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  // Cells are keyed from the right so "99" -> "100" animates the units digit
  // in place instead of shifting every cell along.
  const chars = shown.split("");
  return (
    <span className={`ad ${className ?? ""}`}>
      <span className="sr-only">{label ?? value}</span>
      <span className="ad-digits" aria-hidden>
        {chars.map((c, i) => (
          <Cell key={chars.length - i} char={c} direction={direction} />
        ))}
      </span>
    </span>
  );
}
