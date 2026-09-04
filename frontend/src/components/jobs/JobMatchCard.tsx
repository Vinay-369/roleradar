import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MapPin, Bookmark, Check, Sparkles, Clock } from "lucide-react";
import type { JobMatch } from "../../lib/jobs";
import { saveApplication } from "../../lib/applications";
import { WhyScoreModal } from "../common/WhyScoreModal";
import { useToast } from "../../context/ToastContext";

const READINESS_LABEL: Record<string, { label: string; className: string }> = {
  ready: { label: "Ready to apply", className: "bg-signal-500/10 text-signal-700 border border-signal-500/20" },
  fix_gaps: { label: "Fix gaps first", className: "bg-amber-500/10 text-amber-700 border border-amber-500/20" },
  learn_first: { label: "Learn first", className: "bg-alert-600/10 text-alert-600 border border-alert-600/20" },
};

export function JobMatchCard({ job }: { job: JobMatch }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const save = useMutation({
    mutationFn: () => saveApplication(job.job_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      toast.success(`Bookmarked "${job.job_title}" at ${job.company}`);
    },
    onError: () => toast.error("Failed to bookmark job."),
  });

  const readiness = job.apply_readiness ? READINESS_LABEL[job.apply_readiness] : null;

  const FIT_BADGES: Record<string, { label: string; className: string }> = {
    GOOD_FIT: { label: "Good Fit", className: "bg-signal-500/10 text-signal-700 border border-signal-500/30" },
    POSSIBLE_FIT: { label: "Possible Fit", className: "bg-ink-100 text-ink-700 border border-ink-200" },
    SKILL_GAP: { label: "Skill Gap", className: "bg-amber-500/10 text-amber-700 border border-amber-500/30" },
    EXPERIENCE_GAP: { label: "Experience Gap", className: "bg-alert-600/10 text-alert-600 border border-alert-600/30" },
  };

  const compensationDisplay = (() => {
    if (job.salary_min && job.salary_max) return `₹${job.salary_min}–${job.salary_max} LPA`;
    if (job.salary_min) return `₹${job.salary_min}+ LPA`;
    if (job.stipend) return `₹${job.stipend.toLocaleString()} / mo`;
    if (job.stipend_min && job.stipend_max) return `₹${job.stipend_min.toLocaleString()}–${job.stipend_max.toLocaleString()} / mo`;
    if (job.stipend_min) return `₹${job.stipend_min.toLocaleString()} / mo`;
    if (job.job_type === "internship" || job.opportunity_type === "INTERNSHIP") return "Stipend not specified";
    return null;
  })();

  const locationDisplay = job.is_remote
    ? "Remote"
    : job.location
    ? job.location
    : "On-site / Hybrid";

  const eligibility = job.eligibility;
  const isExpMismatch = eligibility?.status === "EXPERIENCE_MISMATCH";
  const isDegreeMismatch = eligibility?.status === "DEGREE_MISMATCH";
  const isEligible = eligibility?.status === "ELIGIBLE" || eligibility?.status === "LIKELY_ELIGIBLE";

  return (
    <div className={`rounded-xl border ${isExpMismatch ? "border-amber-200 bg-amber-50/20" : "border-ink-100 bg-white"} p-5 transition-all duration-200 hover:shadow-md`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <Link to={`/opportunities/job/${job.job_id}`} className="font-semibold text-ink-900 hover:text-signal-600 hover:underline">
              {job.job_title}
            </Link>
            {job.verification_status === "VERIFIED_ACTIVE" && job.is_direct_apply && (
              <span className="rounded-full bg-signal-500/10 text-signal-700 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                Verified Direct Opening
              </span>
            )}
            {job.last_verified_at && (
              <span className="rounded-full bg-ink-50 text-ink-600 border border-ink-100 px-2 py-0.5 text-[10px] font-medium" title={`Audited: ${job.last_verified_at}`}>
                Verified recently
              </span>
            )}
            {job.posted_days_ago !== undefined && (
              <span className="flex items-center gap-1 text-[10px] text-ink-500 font-semibold bg-ink-50 px-2 py-0.5 rounded-full border border-ink-100">
                <Clock size={10} className="text-signal-600" />
                <span>{job.posted_days_ago === 0 ? "Posted today" : `Posted ${job.posted_days_ago}d ago`}</span>
              </span>
            )}
          </div>
          <p className="text-xs text-ink-500 font-medium mt-0.5">{job.company}</p>

          {/* Location & Compensation Chips */}
          <div className="flex items-center gap-3 mt-1.5 text-xs text-ink-500 flex-wrap">
            <span className="flex items-center gap-1">
              <MapPin size={12} className="text-ink-400" />
              <span>{locationDisplay}</span>
            </span>
            {compensationDisplay && (
              <span className="font-semibold text-ink-700">
                {compensationDisplay}
              </span>
            )}
            {job.workplace_type && job.workplace_type !== "UNKNOWN" && (
              <span className="rounded bg-ink-100/70 text-ink-700 px-1.5 py-0.5 text-[10px] font-medium">
                {job.workplace_type}
              </span>
            )}
            {job.degree_requirements && job.degree_requirements.length > 0 && (
              <span className="rounded bg-ink-100/70 text-ink-600 px-1.5 py-0.5 text-[10px] font-medium">
                {job.degree_requirements.join(", ")}
              </span>
            )}
          </div>

          {/* India-First Eligibility Callout */}
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            {isExpMismatch && (
              <span className="rounded-md bg-amber-500/10 text-amber-800 border border-amber-500/30 px-2 py-0.5 text-[11px] font-semibold flex items-center gap-1">
                <span>⚠</span>
                <span>{eligibility?.reasons[0] || "Requires more experience"}</span>
              </span>
            )}
            {isDegreeMismatch && (
              <span className="rounded-md bg-amber-500/10 text-amber-800 border border-amber-500/30 px-2 py-0.5 text-[11px] font-semibold flex items-center gap-1">
                <span>⚠</span>
                <span>{eligibility?.reasons[0] || "Degree mismatch"}</span>
              </span>
            )}
            {isEligible && (
              <span className="rounded-md bg-signal-500/10 text-signal-700 border border-signal-500/30 px-2 py-0.5 text-[11px] font-semibold flex items-center gap-1">
                <span>✓</span>
                <span>{job.has_match ? "Eligible for your profile" : "Eligible opening"}</span>
              </span>
            )}
            {!isEligible && !isExpMismatch && !isDegreeMismatch && job.fresher_eligible && (
              <span className="rounded-md bg-signal-500/10 text-signal-700 border border-signal-500/30 px-2 py-0.5 text-[11px] font-semibold flex items-center gap-1">
                <span>✓</span>
                <span>Fresher eligible</span>
              </span>
            )}
            {!isEligible && !isExpMismatch && !isDegreeMismatch && job.student_eligible && (
              <span className="rounded-md bg-signal-500/10 text-signal-700 border border-signal-500/30 px-2 py-0.5 text-[11px] font-semibold flex items-center gap-1">
                <span>✓</span>
                <span>Student eligible</span>
              </span>
            )}
            {job.realistic_fit && FIT_BADGES[job.realistic_fit] && (
              <span className={`rounded-md px-2 py-0.5 text-[11px] font-semibold ${FIT_BADGES[job.realistic_fit].className}`}>
                {FIT_BADGES[job.realistic_fit].label}
              </span>
            )}
          </div>
        </div>

        <div className="text-right shrink-0 ml-4 flex flex-col items-end">
          {job.has_match && job.overall_score !== null && job.overall_score !== undefined ? (
            <>
              <p className="text-2xl font-display font-bold text-ink-900">{job.overall_score}%</p>
              {readiness && (
                <span className={`inline-block mt-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${readiness.className}`}>
                  {readiness.label}
                </span>
              )}
              <div className="mt-1">
                <WhyScoreModal job={job} />
              </div>
            </>
          ) : (
            <div className="flex flex-col items-end">
              <Link
                to="/resume/master"
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-signal-700 bg-signal-500/10 hover:bg-signal-500/20 border border-signal-500/20 px-2.5 py-1 rounded-lg transition-colors group"
                title="Upload your resume to see your personalized match score"
              >
                <Sparkles size={11} className="text-signal-600 group-hover:scale-110 transition-transform" />
                <span>Upload resume to see match</span>
              </Link>
              <span className="text-[10px] text-ink-400 mt-1">
                Match score not calculated
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Matched & Missing Skills or Required Skills */}
      {job.has_match ? (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {job.matched_skills.map((s) => (
            <span key={s} className="rounded-full bg-signal-500/10 text-signal-700 px-2 py-0.5 text-xs font-medium">{s}</span>
          ))}
          {job.partial_skills.map((s) => (
            <span key={s} className="rounded-full bg-amber-500/10 text-amber-700 px-2 py-0.5 text-xs font-medium">{s} (related)</span>
          ))}
          {job.missing_skills.map((s) => (
            <span key={s} className="rounded-full bg-amber-50 text-amber-800 border border-amber-200/60 px-2 py-0.5 text-xs font-medium" title="Skill gap - needs learning">
              {s} · Missing
            </span>
          ))}
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-1.5 mt-3">
          <span className="text-[11px] text-ink-400 font-medium mr-1">Skills:</span>
          {(job.skills_required && job.skills_required.length > 0 ? job.skills_required : job.matched_skills).map((s) => (
            <span key={s} className="rounded-full bg-ink-50 text-ink-700 border border-ink-100 px-2 py-0.5 text-xs font-medium">{s}</span>
          ))}
        </div>
      )}

      {/* Action Footer Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 mt-4 pt-3 border-t border-ink-50">
        <div className="flex items-center gap-2">
          <Link
            to={job.has_match ? `/resume/tailor/${job.job_id}` : `/resume/master?targetJobId=${encodeURIComponent(job.job_id)}`}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-ink-950 hover:bg-ink-900 px-3.5 py-1.5 rounded-lg shadow-xs transition-all"
          >
            <Sparkles size={13} />
            <span>{job.has_match ? "Tailor Resume" : "Upload Resume to Tailor"}</span>
          </Link>
          <button
            onClick={() => save.mutate()}
            disabled={save.isPending || save.isSuccess}
            className="inline-flex items-center gap-1 text-xs font-medium text-ink-600 hover:text-ink-950 bg-ink-50 hover:bg-ink-100 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-60"
          >
            {save.isSuccess ? (
              <>
                <Check size={12} className="text-signal-600" />
                <span className="text-signal-700 font-semibold">Saved</span>
              </>
            ) : (
              <>
                <Bookmark size={12} className="text-ink-400" />
                <span>{save.isPending ? "Saving…" : "Save"}</span>
              </>
            )}
          </button>
        </div>

        {job.is_direct_apply && job.apply_url ? (
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 rounded-lg bg-signal-500 hover:bg-signal-600 text-white px-3.5 py-1.5 text-xs font-semibold shadow-xs transition-all active:scale-95 ml-auto"
            title={`Apply directly on official portal for ${job.company}`}
          >
            Apply Directly ↗
          </a>
        ) : (
          <Link
            to={`/opportunities/job/${job.job_id}`}
            className="inline-flex items-center gap-1 rounded-lg bg-ink-100 hover:bg-ink-200 text-ink-700 px-3.5 py-1.5 text-xs font-semibold transition-all ml-auto"
          >
            View Details
          </Link>
        )}
      </div>
    </div>
  );
}
