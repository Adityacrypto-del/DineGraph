// Motion helpers shared by the animated components. useGSAP is the inline
// stand-in from Peak-frontends' scroll timeline, so @gsap/react isn't needed.
import { useLayoutEffect, useRef, useSyncExternalStore } from "react";
import gsap from "gsap";

const REDUCED = "(prefers-reduced-motion: reduce)";

function subscribe(callback: () => void) {
  const mq = window.matchMedia(REDUCED);
  mq.addEventListener("change", callback);
  return () => mq.removeEventListener("change", callback);
}

export function useReducedMotion() {
  return useSyncExternalStore(subscribe, () => window.matchMedia(REDUCED).matches);
}

// One gsap.context lives for the component's lifetime; the callback is re-added
// when dependencies change and the context is reverted only on unmount.
export function useGSAP(
  callback: () => void | (() => void),
  options: { dependencies?: unknown[]; scope?: { current: Element | null } } = {},
) {
  const ctx = useRef<gsap.Context | null>(null);
  const cleanup = useRef<(() => void) | undefined>(undefined);

  useLayoutEffect(() => {
    ctx.current = gsap.context(() => {}, options.scope?.current ?? undefined);
    return () => {
      cleanup.current?.();
      cleanup.current = undefined;
      ctx.current?.revert();
      ctx.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useLayoutEffect(() => {
    if (!ctx.current) return;
    cleanup.current?.();
    const ret = ctx.current.add(callback);
    cleanup.current = typeof ret === "function" ? ret : undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, options.dependencies ?? []);
}

