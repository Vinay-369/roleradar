import { Target, CheckCircle2 } from "lucide-react";

const POINTS = [
  "Truth Guard: nothing is added to your resume without your approval",
  "Real ATS-style parseability checks, not vibes",
  "Tailored per company, your master resume never touched",
];

export function AuthBrandPanel() {
  return (
    <div className="hidden lg:flex flex-col justify-between w-1/2 bg-gradient-to-br from-ink-950 via-ink-900 to-ink-950 p-12 relative overflow-hidden">
      <div className="absolute -right-20 -top-20 w-72 h-72 rounded-full bg-signal-500/20 blur-3xl" />
      <div className="absolute left-10 bottom-10 w-56 h-56 rounded-full bg-signal-400/10 blur-3xl" />

      <div className="relative flex items-center gap-2">
        <div className="w-9 h-9 rounded-md bg-gradient-to-br from-signal-400 to-signal-600 flex items-center justify-center">
          <Target size={18} className="text-white" strokeWidth={2.5} />
        </div>
        <span className="font-display text-xl text-white">
          Role<span className="text-signal-400">Radar</span>
        </span>
      </div>

      <div className="relative">
        <h2 className="font-display text-3xl text-white leading-tight mb-6">
          Know exactly why<br />you'd get filtered out<br />— and fix it honestly.
        </h2>
        <div className="space-y-3">
          {POINTS.map((point) => (
            <div key={point} className="flex items-start gap-2.5">
              <CheckCircle2 size={16} className="text-signal-400 mt-0.5 shrink-0" />
              <p className="text-sm text-ink-300">{point}</p>
            </div>
          ))}
        </div>
      </div>

      <p className="relative text-xs text-ink-500">Resume intelligence that never fabricates.</p>
    </div>
  );
}
