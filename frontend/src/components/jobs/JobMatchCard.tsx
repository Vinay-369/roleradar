import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MapPin, Bookmark, Check, Sparkles, Clock } from "lucide-react";
import type { JobMatch } from "../../lib/jobs";
import { saveApplication } from "../../lib/applications";
import { WhyScoreModal } from "../common/WhyScoreModal";
import { useToast } from "../../context/ToastContext";

const READINESS_LABEL: Record<JobMatch["apply_readiness"], { label: string; className: string }> = {
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

  const readiness = READINESS_LABEL[job.apply_readiness];

  const compensationDisplay = (() => {
    if (job.salary_min && job.salary_max) return `₹${job.salary_min}–${job.salary_max} LPA`;
    if (job.salary_min) return `₹${job.salary_min}+ LPA`;
    if (job.stipend_min && job.stipend_max) return `₹${job.stipend_min.toLocaleString()}–${job.stipend_max.toLocaleString()} / mo`;
    if (job.stipend_min) return `₹${job.stipend_min.toLocaleString()} / mo`;
    return null;
  })();

  const locationDisplay = job.is_remote
    ? "Remote"
    : job.location
    ? job.location
    : "On-site / Hybrid";

  return (
    <div className="rounded-xl border border-ink-100 bg-white p-5 transition-all duration-200 hover:shadow-md">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <Link to={`/opportunities/job/${job.job_id}`} className="font-semibold text-ink-900 hover:text-signal-600 hover:underline">
              {job.job_title}
            </Link>
            <span className="rounded-full bg-signal-500/10 text-signal-700 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
              Verified
            </span>
            {job.posted_days_ago !== undefined && (
              <span className="flex items-center gap-1 text-[10px] text-ink-500 font-semibold bg-ink-50 px-2 py-0.5 rounded-full border border-ink-100">
                <Clock size={10} className="text-signal-600" />
                <span>{job.posted_days_ago === 0 ? "Posted today" : `Posted ${job.posted_days_ago}d ago`}</span>
              </span>
            )}
          </div>
          <p className="text-xs text-ink-500 font-medium mt-0.5">{job.company}</p>

          {/* Location & Compensation Chips */}
          <div className="flex items-center gap-3 mt-1.5 text-xs text-ink-500">
            <span className="flex items-center gap-1">
              <MapPin size={12} className="text-ink-400" />
              <span>{locationDisplay}</span>
            </span>
            {compensationDisplay && (
              <span className="font-semibold text-ink-700">
                {compensationDisplay}
              </span>
            )}
          </div>
        </div>

        <div className="text-right shrink-0 ml-4 flex flex-col items-end">
          <p className="text-2xl font-display font-bold text-ink-900">{job.overall_score}%</p>
          <span className={`inline-block mt-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${readiness.className}`}>
            {readiness.label}
          </span>
          <div className="mt-1">
            <WhyScoreModal job={job} />
          </div>
        </div>
      </div>

      {/* Matched & Missing Skills */}
      <div className="flex flex-wrap gap-1.5 mt-3">
        {job.matched_skills.map((s) => (
          <span key={s} className="rounded-full bg-signal-500/10 text-signal-700 px-2 py-0.5 text-xs font-medium">{s}</span>
        ))}
        {job.partial_skills.map((s) => (
          <span key={s} className="rounded-full bg-amber-500/10 text-amber-700 px-2 py-0.5 text-xs font-medium">{s} (related)</span>
        ))}
        {job.missing_skills.map((s) => (
          <span key={s} className="rounded-full bg-ink-50 text-ink-400 px-2 py-0.5 text-xs line-through">{s}</span>
        ))}
      </div>

      {/* Action Footer Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 mt-4 pt-3 border-t border-ink-50">
        <div className="flex items-center gap-2">
          <Link
            to={`/resume/tailor/${job.job_id}`}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-ink-950 hover:bg-ink-900 px-3.5 py-1.5 rounded-lg shadow-xs transition-all"
          >
            <Sparkles size={13} />
            <span>Tailor Resume</span>
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

        {(() => {
          const directApplyUrl = (job.apply_url && !job.apply_url.includes("example.com"))
            ? job.apply_url
            : `https://www.google.com/search?q=${encodeURIComponent(job.company + " " + job.job_title + " careers apply")}`;
          return (
            <a
              href={directApplyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg bg-signal-500 hover:bg-signal-600 text-white px-3.5 py-1.5 text-xs font-semibold shadow-xs transition-all active:scale-95 ml-auto"
            >
              Apply Directly ↗
            </a>
          );
        })()}
      </div>
    </div>
  );
}
