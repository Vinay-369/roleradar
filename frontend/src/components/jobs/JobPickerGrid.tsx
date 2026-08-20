import { useNavigate } from "react-router-dom";
import { Briefcase } from "lucide-react";
import type { JobMatch } from "../../lib/jobs";

export function JobPickerGrid({
  matches,
  basePath,
  emptyMessage,
}: {
  matches: JobMatch[] | undefined;
  basePath: string; // e.g. "/growth/roadmap" -> navigates to `${basePath}/${jobId}`
  emptyMessage: string;
}) {
  const navigate = useNavigate();

  if (!matches || matches.length === 0) {
    return <p className="text-sm text-ink-500">{emptyMessage}</p>;
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {matches.map((m) => (
        <button
          key={m.job_id}
          onClick={() => navigate(`${basePath}/${m.job_id}`)}
          className="text-left rounded-lg border border-ink-100 bg-white p-4 transition-all duration-200 hover:shadow-md hover:border-signal-500/50 hover:-translate-y-0.5"
        >
          <div className="flex items-start justify-between mb-1">
            <Briefcase size={16} className="text-signal-500 mt-0.5" />
            <span className="text-sm font-display text-ink-900">{m.overall_score}%</span>
          </div>
          <p className="text-sm font-medium text-ink-900">{m.job_title}</p>
          <p className="text-xs text-ink-500">{m.company}</p>
        </button>
      ))}
    </div>
  );
}
