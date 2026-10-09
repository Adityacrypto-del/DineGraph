// Ported from Peak-frontends 02-gateway-flow. The original rendered an iframe
// that pulled Tailwind and GSAP from CDNs; this draws the same converging
// particle field straight onto a canvas, in the app's theme colours.
//
// Particles drift at random while being pulled gently toward a focal point,
// leave fading trails, and are pushed outward by a ripple wherever you click.
import { useEffect, useRef } from "react";

interface Props {
  /** Particles per 10,000 square pixels. */
  density?: number;
  speed?: number;
  /** Focal point as fractions of the box. */
  focus?: [number, number];
  /** Pull toward the focal point per frame. */
  pull?: number;
  className?: string;
}

interface Particle { x: number; y: number; vx: number; vy: number; hue: number }
interface Ripple { x: number; y: number; r: number }

function themeColors(el: Element) {
  const css = getComputedStyle(el);
  return [css.getPropertyValue("--primary").trim() || "#dc2626", css.getPropertyValue("--accent").trim() || "#a16207"];
}

export default function FlowField({ density = 1.1, speed = 0.7, focus = [0.5, 0.5], pull = 0.0011, className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [focusX, focusY] = focus;

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const scheme = window.matchMedia("(prefers-color-scheme: dark)");
    let colors = themeColors(canvas);
    let width = 0;
    let height = 0;
    let particles: Particle[] = [];
    const ripples: Ripple[] = [];
    let raf = 0;
    let visible = true;

    const spawn = (p?: Particle): Particle => {
      const q = p ?? ({} as Particle);
      q.x = Math.random() * width;
      q.y = Math.random() * height;
      q.vx = (Math.random() - 0.5) * speed;
      q.vy = (Math.random() - 0.5) * speed;
      q.hue = Math.random() < 0.7 ? 0 : 1;
      return q;
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(900, Math.round(((width * height) / 10000) * density));
      particles = Array.from({ length: count }, (_, i) => spawn(particles[i]));
    };

    const step = () => {
      // Fade the previous frame instead of clearing it, which leaves the trails.
      ctx.globalCompositeOperation = "destination-out";
      ctx.fillStyle = "rgba(0,0,0,0.12)";
      ctx.fillRect(0, 0, width, height);
      ctx.globalCompositeOperation = "source-over";

      const fx = width * focusX;
      const fy = height * focusY;
      for (const p of particles) {
        p.x += p.vx + (fx - p.x) * pull;
        p.y += p.vy + (fy - p.y) * pull;
        for (const r of ripples) {
          const dx = p.x - r.x;
          const dy = p.y - r.y;
          const d = Math.hypot(dx, dy);
          if (d < r.r && d > r.r - 24) {
            p.x += dx * 0.05;
            p.y += dy * 0.05;
          }
        }
        if (p.x < 0 || p.x > width || p.y < 0 || p.y > height || Math.hypot(fx - p.x, fy - p.y) < 6) spawn(p);
        ctx.fillStyle = colors[p.hue];
        ctx.fillRect(p.x, p.y, 1.6, 1.6);
      }
      for (let i = ripples.length - 1; i >= 0; i--) {
        ripples[i].r += 6;
        if (ripples[i].r > 520) ripples.splice(i, 1);
      }
    };

    const loop = () => {
      step();
      raf = requestAnimationFrame(loop);
    };
    const play = () => {
      cancelAnimationFrame(raf);
      if (reduced.matches) {
        // A still field: settle the particles a little and draw once.
        for (let i = 0; i < 40; i++) step();
        return;
      }
      if (visible && !document.hidden) raf = requestAnimationFrame(loop);
    };

    const onPointer = (e: PointerEvent) => {
      const box = canvas.getBoundingClientRect();
      const x = e.clientX - box.left;
      const y = e.clientY - box.top;
      if (x >= 0 && y >= 0 && x <= box.width && y <= box.height) ripples.push({ x, y, r: 0 });
    };
    const onScheme = () => {
      colors = themeColors(canvas);
    };

    const sizer = new ResizeObserver(() => {
      resize();
      play();
    });
    sizer.observe(canvas);
    const seen = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      play();
    });
    seen.observe(canvas);
    window.addEventListener("pointerdown", onPointer);
    document.addEventListener("visibilitychange", play);
    reduced.addEventListener("change", play);
    scheme.addEventListener("change", onScheme);

    return () => {
      cancelAnimationFrame(raf);
      sizer.disconnect();
      seen.disconnect();
      window.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("visibilitychange", play);
      reduced.removeEventListener("change", play);
      scheme.removeEventListener("change", onScheme);
    };
  }, [density, speed, focusX, focusY, pull]);

  return <canvas ref={canvasRef} className={className} aria-hidden />;
}
