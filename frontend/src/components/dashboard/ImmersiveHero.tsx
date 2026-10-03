import { useEffect, useRef } from "react";
import { Compass, Target, Zap } from "lucide-react";
import { Link } from "react-router-dom";

type ImmersiveHeroProps = {
  firstName?: string;
  targetRole: string;
  hasResume: boolean;
};

const SHAPES = [
  { x: 12, y: 20, size: 52, depth: 0.8, delay: 0 },
  { x: 30, y: 72, size: 22, depth: 1.25, delay: 1.4 },
  { x: 58, y: 18, size: 38, depth: 0.65, delay: 2.2 },
  { x: 77, y: 66, size: 66, depth: 1.1, delay: 0.8 },
  { x: 91, y: 28, size: 18, depth: 1.45, delay: 2.9 },
];

const HERO_TITLE = "Turn your next role into momentum";

export function ImmersiveHero({ firstName, targetRole, hasResume }: ImmersiveHeroProps) {
  const heroRef = useRef<HTMLDivElement>(null);
  const shapeRefs = useRef<Array<HTMLSpanElement | null>>([]);
  const magneticRefs = useRef<Array<HTMLAnchorElement | null>>([]);

  useEffect(() => {
    const hero = heroRef.current;
    if (!hero) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const animatedShapes = shapeRefs.current;
    const magneticButtons = magneticRefs.current;

    const pointer = { x: 0, y: 0, clientX: 0, clientY: 0, active: false };
    let frame = 0;

    const onPointerMove = (event: PointerEvent) => {
      const rect = hero.getBoundingClientRect();
      pointer.x = (event.clientX - rect.left) / rect.width - 0.5;
      pointer.y = (event.clientY - rect.top) / rect.height - 0.5;
      pointer.clientX = event.clientX;
      pointer.clientY = event.clientY;
      pointer.active = true;
    };

    const onPointerLeave = () => {
      pointer.active = false;
      pointer.x = 0;
      pointer.y = 0;
    };

    const animate = (time: number) => {
      const seconds = time / 1000;

      animatedShapes.forEach((shape, index) => {
        if (!shape) return;
        const config = SHAPES[index];
        const driftX = Math.sin(seconds * 0.55 + config.delay) * 7;
        const driftY = Math.cos(seconds * 0.7 + config.delay) * 8;
        const x = pointer.x * config.depth * 28 + driftX;
        const y = pointer.y * config.depth * 24 + driftY;
        const rotation = seconds * (index % 2 === 0 ? 8 : -6) + pointer.x * 16;
        shape.style.transform = `translate3d(${x}px, ${y}px, 0) rotate3d(1, 1, 0, ${rotation}deg)`;
      });

      magneticButtons.forEach((button) => {
        if (!button) return;
        const rect = button.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const dx = pointer.clientX - centerX;
        const dy = pointer.clientY - centerY;
        const distance = Math.hypot(dx, dy);
        const radius = 130;
        const strength = pointer.active && distance < radius ? (1 - distance / radius) * 0.22 : 0;
        button.style.transform = `translate3d(${dx * strength}px, ${dy * strength}px, 0)`;
      });

      // Keep the loop smooth while allowing the browser to coalesce pointer work.
      frame = requestAnimationFrame(animate);
    };

    hero.addEventListener("pointermove", onPointerMove, { passive: true });
    hero.addEventListener("pointerleave", onPointerLeave, { passive: true });
    frame = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(frame);
      hero.removeEventListener("pointermove", onPointerMove);
      hero.removeEventListener("pointerleave", onPointerLeave);
      magneticButtons.forEach((button) => {
        if (button) button.style.transform = "translate3d(0, 0, 0)";
      });
    };
  }, []);

  return (
    <section ref={heroRef} className="rr-immersive-hero relative isolate min-h-[min(540px,72vh)] overflow-hidden rounded-2xl border border-slate-200/80 bg-slate-950 p-6 text-white shadow-sm sm:p-8">
      <div className="rr-hero-grid absolute inset-0 -z-10" aria-hidden="true" />
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_18%_20%,rgba(56,189,248,.16),transparent_30%),radial-gradient(circle_at_82%_78%,rgba(99,102,241,.18),transparent_34%)]" aria-hidden="true" />
      {SHAPES.map((shape, index) => (
        <span
          key={`${shape.x}-${shape.y}`}
          ref={(element) => { shapeRefs.current[index] = element; }}
          className={`rr-hero-shape rr-hero-shape-${index}`}
          style={{ left: `${shape.x}%`, top: `${shape.y}%`, width: shape.size, height: shape.size, animationDelay: `${shape.delay}s` }}
          aria-hidden="true"
        />
      ))}

      <div className="relative z-10 flex min-h-[min(492px,68vh)] flex-col justify-between gap-10">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-300/25 bg-cyan-300/10 px-2.5 py-1 text-[11px] font-semibold text-cyan-200">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-300" /> RoleRadar Intelligence Active
          </span>
          <Link to="/growth/skill-gaps" className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/10 px-2.5 py-1 text-[11px] font-semibold text-slate-200 transition-opacity hover:opacity-80">
            <Target size={11} /> Targeting: {targetRole}
          </Link>
        </div>

        <div className="max-w-3xl">
          <p className="mb-3 text-sm font-semibold text-slate-300">Welcome back{firstName ? `, ${firstName}` : ""}</p>
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200/80">AI resume intelligence for your next move</p>
          <h1 aria-label={HERO_TITLE} className="rr-split-title max-w-3xl font-display text-4xl font-bold leading-[1.03] tracking-tight text-white sm:text-6xl">
            {Array.from(HERO_TITLE).map((character, index) => (
              <span key={`${character}-${index}`} className="rr-split-character" style={{ animationDelay: `${index * 24}ms` }} aria-hidden="true">
                {character === " " ? "\u00a0" : character}
              </span>
            ))}
          </h1>
          <p className="mt-5 max-w-2xl text-sm leading-relaxed text-slate-300 sm:text-base">
            {hasResume
              ? `Track your ATS fit for ${targetRole}, discover verified roles, and turn every application into a stronger signal.`
              : `Upload your resume to unlock ATS analysis, verified opportunities, and a tailored plan for ${targetRole}.`}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Link ref={(element) => { magneticRefs.current[0] = element; }} to="/opportunities/jobs" className="rr-magnetic-action inline-flex items-center gap-2 rounded-xl bg-cyan-300 px-4 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-950/20">
            <Compass size={16} /> Explore Jobs
          </Link>
          <Link ref={(element) => { magneticRefs.current[1] = element; }} to="/growth/interview" className="rr-magnetic-action inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-sm font-semibold text-white backdrop-blur-sm">
            <Zap size={16} className="text-amber-300" /> Mock Interview
          </Link>
        </div>
      </div>
    </section>
  );
}
