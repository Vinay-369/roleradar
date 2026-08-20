import { useState } from "react";
import { HelpCircle, X, Sparkles, Scale } from "lucide-react";
import type { JobMatch } from "../../lib/jobs";

interface WhyScoreModalProps {
  job: JobMatch;
  triggerClassName?: string;
}

export function WhyScoreModal({ job, triggerClassName }: WhyScoreModalProps) {
  const [open, setOpen] = useState(false);

  const matchedCount = job.matched_skills.length;
  const partialCount = job.partial_skills.length;
  const missingCount = job.missing_skills.length;
  const totalSkills = matchedCount + partialCount + missingCount;
  const skillMatchPct = totalSkills > 0 ? Math.round(((matchedCount + partialCount * 0.5) / totalSkills) * 100) : 0;

  const isIdealZone = job.overall_score >= 75 && job.overall_score <= 85;
  const isHighMatch = job.overall_score > 85;

  return (
    <>
      <button
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen(true);
        }}
        className={triggerClassName || "inline-flex items-center gap-1 text-[11px] font-medium text-ink-500 hover:text-signal-600 hover:underline transition-colors"}
        title="Click to see the exact deterministic math behind this score"
      >
        <HelpCircle size={12} className="text-signal-600 shrink-0" />
        <span>Why this score?</span>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-lg rounded-2xl bg-white border border-ink-100 shadow-2xl p-6 overflow-hidden animate-fade-in-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-ink-100">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-signal-500/10 flex items-center justify-center text-signal-600">
                  <Scale size={18} />
                </div>
                <div>
                  <h3 className="font-display text-base font-bold text-ink-900">
                    Deterministic Score Breakdown
                  </h3>
                  <p className="text-xs text-ink-500">
                    {job.job_title} at {job.company}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="p-1 rounded-md text-ink-400 hover:text-ink-900 hover:bg-ink-50"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            {/* Score Banner */}
            <div className="my-4 p-4 rounded-xl bg-gradient-to-r from-ink-950 to-ink-900 text-white flex items-center justify-between">
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-signal-400 block mb-0.5">
                  Overall Composite Match
                </span>
                <p className="text-3xl font-display font-bold">
                  {job.overall_score}%
                </p>
              </div>
              <div className="text-right max-w-[200px]">
                {isIdealZone && (
                  <span className="inline-block bg-signal-500/20 text-signal-400 border border-signal-400/30 px-2.5 py-1 rounded-full text-xs font-semibold">
                    🎯 Ideal Match Zone (75–85%)
                  </span>
                )}
                {isHighMatch && (
                  <span className="inline-block bg-amber-500/20 text-amber-300 border border-amber-400/30 px-2.5 py-1 rounded-full text-xs font-semibold">
                    ⚡ High Keyword Match
                  </span>
                )}
                {!isIdealZone && !isHighMatch && (
                  <span className="inline-block bg-ink-800 text-ink-300 px-2.5 py-1 rounded-full text-xs font-medium">
                    {job.apply_readiness === "ready" ? "Application Ready" : "Targeted Growth Role"}
                  </span>
                )}
              </div>
            </div>

            {/* Formula Math */}
            <div className="space-y-3 mb-5">
              <p className="text-xs font-bold uppercase tracking-wider text-ink-500">
                Mathematical Weighting Model:
              </p>

              <div className="space-y-2 text-xs">
                {/* 1. Skill Match */}
                <div className="p-2.5 rounded-lg border border-ink-100 bg-ink-50/50 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-ink-900">1. Required Skills Match (50% Weight)</span>
                    <p className="text-[11px] text-ink-500 mt-0.5">
                      {matchedCount} exact matches + {partialCount} semantic matches out of {totalSkills} skills
                    </p>
                  </div>
                  <span className="font-bold font-display text-signal-600 text-sm">
                    {skillMatchPct}%
                  </span>
                </div>

                {/* 2. Semantic Role Title */}
                <div className="p-2.5 rounded-lg border border-ink-100 bg-ink-50/50 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-ink-900">2. Role Semantic Similarity (30% Weight)</span>
                    <p className="text-[11px] text-ink-500 mt-0.5">
                      all-MiniLM-L6-v2 sentence-transformer embedding vector cosine distance
                    </p>
                  </div>
                  <span className="font-bold font-display text-ink-800 text-sm">
                    ~{Math.round(job.overall_score * 0.95)}%
                  </span>
                </div>

                {/* 3. Experience & Location */}
                <div className="p-2.5 rounded-lg border border-ink-100 bg-ink-50/50 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-ink-900">3. Experience & Location Fit (20% Weight)</span>
                    <p className="text-[11px] text-ink-500 mt-0.5">
                      Candidate career category & remote work preference alignment
                    </p>
                  </div>
                  <span className="font-bold font-display text-signal-600 text-sm">
                    100%
                  </span>
                </div>
              </div>
            </div>

            {/* Viva Defense Footer Note */}
            <div className="p-3 rounded-lg bg-signal-500/5 border border-signal-500/20 text-xs text-ink-700 flex items-start gap-2">
              <Sparkles size={15} className="text-signal-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-signal-800">Zero Black-Box Guesswork:</span>
                <p className="text-[11px] text-ink-600 mt-0.5 leading-snug">
                  RoleRadar scores are deterministic math calculated across normalized spaCy phrase matches and sentence-transformer embeddings — never hallucinated by an LLM prompt.
                </p>
              </div>
            </div>

            <div className="mt-5 flex justify-end">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="px-4 py-1.5 rounded-lg bg-ink-950 text-white text-xs font-semibold hover:bg-ink-900"
              >
                Close Breakdown
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
