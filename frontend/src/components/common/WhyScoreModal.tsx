import { useState } from "react";
import { HelpCircle, X, Scale, CheckCircle2, AlertCircle } from "lucide-react";
import type { JobMatch } from "../../lib/jobs";

interface WhyScoreModalProps {
  job: JobMatch;
  triggerClassName?: string;
}

export function WhyScoreModal({ job, triggerClassName }: WhyScoreModalProps) {
  const [open, setOpen] = useState(false);

  const score = job.overall_score ?? 0;
  const isIdealZone = score >= 75 && score <= 85;
  const isHighMatch = score > 85;

  const weights = job.factor_weights || {
    skills: 0.50,
    role: 0.20,
    experience: 0.15,
    location: 0.05,
    salary: 0.05,
    industry: 0.05,
  };

  const factors = [
    {
      name: "Required Skills Match",
      score: job.skill_score,
      weight: weights.skills,
      details: `${job.matched_skills.length} exact, ${job.partial_skills.length} partial, ${job.missing_skills.length} missing`,
    },
    {
      name: "Role & Title Relevance",
      score: job.role_score,
      weight: weights.role,
      details: "Semantic similarity between candidate profile and role title",
    },
    {
      name: "Experience Level Alignment",
      score: job.experience_score,
      weight: weights.experience,
      details: "Experience brackets and seniority tier evaluation",
    },
    {
      name: "Location Preference",
      score: job.location_score,
      weight: weights.location,
      details: "Workplace mode and geographic compatibility",
    },
    {
      name: "Compensation Alignment",
      score: job.salary_score,
      weight: weights.salary,
      details: "Stipend or CTC alignment with expectations",
    },
    {
      name: "Industry / Domain Match",
      score: job.industry_score,
      weight: weights.industry,
      details: "Domain overlap between candidate background and job scope",
    },
  ].filter((f) => f.weight !== undefined && f.weight > 0);

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
        title="View canonical backend deterministic score calculation"
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
            className="w-full max-w-lg max-h-[90vh] flex flex-col rounded-2xl bg-white border border-ink-100 shadow-2xl p-6 overflow-hidden animate-fade-in-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-ink-100 shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-signal-500/10 flex items-center justify-center text-signal-600">
                  <Scale size={18} />
                </div>
                <div>
                  <h3 className="font-display text-base font-bold text-ink-900">
                    Canonical Score Breakdown
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

            <div className="overflow-y-auto space-y-4 my-4 pr-1">
              {/* Score Banner */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-ink-950 to-ink-900 text-white flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-signal-400 block mb-0.5">
                    Overall Backend Score
                  </span>
                  <p className="text-3xl font-display font-bold">
                    {job.overall_score ?? "N/A"}%
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
                      ⚡ High Match Tier
                    </span>
                  )}
                  {!isIdealZone && !isHighMatch && (
                    <span className="inline-block bg-ink-800 text-ink-300 px-2.5 py-1 rounded-full text-xs font-medium">
                      {job.apply_readiness === "ready" ? "Application Ready" : "Targeted Role"}
                    </span>
                  )}
                </div>
              </div>

              {/* Backend Explanation */}
              {job.score_explanation && (
                <div className="p-3 rounded-lg bg-ink-50 border border-ink-200/80 text-xs text-ink-700">
                  <span className="font-semibold text-ink-900 block mb-0.5">Scoring Model Output:</span>
                  <p className="text-ink-600 leading-relaxed">{job.score_explanation}</p>
                </div>
              )}

              {/* Factors */}
              <div className="space-y-2.5">
                <p className="text-xs font-bold uppercase tracking-wider text-ink-500">
                  Canonical Backend Factor Breakdown:
                </p>

                <div className="space-y-2 text-xs">
                  {factors.map((f, i) => {
                    const weightPct = Math.round((f.weight ?? 0) * 100);
                    const factorScoreVal = f.score !== null && f.score !== undefined ? `${Math.round(f.score)}%` : "N/A";
                    return (
                      <div key={i} className="p-2.5 rounded-lg border border-ink-100 bg-ink-50/50 flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-ink-900">{f.name}</span>
                            <span className="text-[10px] px-1.5 py-0.2 bg-ink-200/60 text-ink-700 rounded font-mono">
                              {weightPct}% weight
                            </span>
                          </div>
                          <p className="text-[11px] text-ink-500 mt-0.5">
                            {f.details}
                          </p>
                        </div>
                        <span className="font-bold font-display text-signal-700 text-sm ml-2 shrink-0">
                          {factorScoreVal}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Skills Evidence */}
              <div className="space-y-2 pt-1 border-t border-ink-100">
                <p className="text-xs font-bold uppercase tracking-wider text-ink-500">
                  Evidence Breakdown:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg border border-signal-100 bg-signal-50/40">
                    <div className="flex items-center gap-1 text-signal-800 font-semibold mb-1">
                      <CheckCircle2 size={13} />
                      <span>Matched Skills ({job.matched_skills.length})</span>
                    </div>
                    {job.matched_skills.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {job.matched_skills.map((s, idx) => (
                          <span key={idx} className="bg-signal-100/80 text-signal-900 px-1.5 py-0.5 rounded text-[10px]">
                            {s}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-[11px] text-ink-400 italic">No direct matches</span>
                    )}
                  </div>

                  <div className="p-2.5 rounded-lg border border-amber-100 bg-amber-50/40">
                    <div className="flex items-center gap-1 text-amber-800 font-semibold mb-1">
                      <AlertCircle size={13} />
                      <span>Skill Gaps ({job.missing_skills.length})</span>
                    </div>
                    {job.missing_skills.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {job.missing_skills.map((s, idx) => (
                          <span key={idx} className="bg-amber-100/80 text-amber-900 px-1.5 py-0.5 rounded text-[10px]">
                            {s}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-[11px] text-ink-400 italic">No missing requirements</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Deterministic Guarantee Note */}
              <div className="p-2.5 rounded-lg bg-ink-100/70 border border-ink-200 text-xs text-ink-700 flex items-start gap-2">
                <Scale size={14} className="text-ink-600 shrink-0 mt-0.5" />
                <p className="text-[11px] text-ink-600 leading-snug">
                  Scores and factor weights reflect canonical backend calculations evaluated from your profile and the opportunity requisition. The client interface does not independently recalculate or estimate fit.
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-ink-100 shrink-0">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="px-4 py-1.5 rounded-lg bg-ink-950 text-white text-xs font-semibold hover:bg-ink-900 transition-colors"
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
