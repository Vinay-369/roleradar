import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { JobMatch } from "../../lib/jobs";
import { saveApplication } from "../../lib/applications";
import { WhyScoreModal } from "../common/WhyScoreModal";

const READINESS_LABEL: Record<JobMatch["apply_readiness"], { label: string; className: string }> = {
  ready: { label: "Ready to apply", className: "bg-signal-500/10 text-signal-600" },
  fix_gaps: { label: "Fix gaps first", className: "bg-amber-500/10 text-amber-600" },
  learn_first: { label: "Learn first", className: "bg-alert-600/10 text-alert-600" },
};

export function JobMatchCard({ job }: { job: JobMatch }) {
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: () => saveApplication(job.job_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  const readiness = READINESS_LABEL[job.apply_readiness];
  return (
    <div className="rounded-lg border border-ink-100 bg-white p-5 transition-shadow duration-200 hover:shadow-md">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2">
            <Link to={`/opportunities/job/${job.job_id}`} className="font-medium text-ink-900 hover:text-signal-600 hover:underline">
              {job.job_title}
            </Link>
            <span className="rounded bg-signal-500/10 text-signal-700 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide">
              Verified
            </span>
          </div>
          <p className="text-sm text-ink-500">{job.company}</p>
        </div>
        <div className="text-right shrink-0 ml-4 flex flex-col items-end">
          <p className="text-2xl font-display font-bold text-ink-900">{job.overall_score}%</p>
          <span className={`inline-block mt-1 rounded-full px-2 py-0.5 text-xs font-medium ${readiness.className}`}>
            {readiness.label}
          </span>
          <div className="mt-1">
            <WhyScoreModal job={job} />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mt-3">
        {job.matched_skills.map((s) => (
          <span key={s} className="rounded-full bg-signal-500/10 text-signal-700 px-2 py-0.5 text-xs">{s}</span>
        ))}
        {job.partial_skills.map((s) => (
          <span key={s} className="rounded-full bg-amber-500/10 text-amber-700 px-2 py-0.5 text-xs">{s} (related)</span>
        ))}
        {job.missing_skills.map((s) => (
          <span key={s} className="rounded-full bg-ink-50 text-ink-500 px-2 py-0.5 text-xs line-through">{s}</span>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3 mt-4 pt-3 border-t border-ink-50">
        <Link
          to={`/resume/tailor/${job.job_id}`}
          className="text-xs font-semibold text-white bg-ink-950 hover:bg-ink-900 px-3 py-1.5 rounded-md shadow-xs transition-all"
        >
          🎯 Tailor Resume
        </Link>
        <Link
          to={`/growth/interview/${job.job_id}`}
          className="text-xs font-medium text-ink-700 bg-ink-50 hover:bg-ink-100 px-2.5 py-1.5 rounded-md transition-colors"
        >
          🎙️ Prep Interview
        </Link>
        <Link
          to={`/growth/roadmap/${job.job_id}`}
          className="text-xs font-medium text-ink-700 bg-ink-50 hover:bg-ink-100 px-2.5 py-1.5 rounded-md transition-colors"
        >
          📈 Skill Roadmap
        </Link>
        <button
          onClick={() => save.mutate()}
          disabled={save.isPending || save.isSuccess}
          className="text-xs font-medium text-ink-500 hover:text-ink-900 hover:underline disabled:opacity-60 ml-auto"
        >
          {save.isSuccess ? "Saved to CRM ✓" : save.isPending ? "Saving…" : "Save to Tracker"}
        </button>
        {(() => {
          const directApplyUrl = (job.apply_url && !job.apply_url.includes("example.com"))
            ? job.apply_url
            : `https://www.google.com/search?q=${encodeURIComponent(job.company + " " + job.job_title + " careers apply")}`;
          return (
            <a
              href={directApplyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-md bg-signal-500 hover:bg-signal-600 text-white px-3 py-1.5 text-xs font-semibold shadow-xs transition-all active:scale-95"
            >
              Apply Directly ↗
            </a>
          );
        })()}
      </div>
    </div>
  );
}
