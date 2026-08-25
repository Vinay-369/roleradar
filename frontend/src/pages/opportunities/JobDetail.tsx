import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { getJobDetail } from "../../lib/jobDetail";

export function JobDetail() {
  const { jobId } = useParams<{ jobId: string }>();
  const { data: job, isLoading } = useQuery({
    queryKey: ["job-detail", jobId],
    queryFn: () => getJobDetail(jobId!),
    enabled: !!jobId,
  });

  if (isLoading) return <p className="text-ink-500">Loading…</p>;
  if (!job) return <p className="text-ink-500">Job not found.</p>;

  const salaryText = job.salary_disclosed && job.salary_min != null
    ? `₹${job.salary_min}–${job.salary_max} LPA`
    : job.stipend_min != null
      ? `₹${job.stipend_min}/month stipend`
      : "Not disclosed";

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-2 mb-1">
        <h1 className="font-display text-2xl text-ink-900">{job.title}</h1>
        <span className="rounded bg-signal-500/10 text-signal-700 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide">
          Verified Opening
        </span>
      </div>
      <p className="text-ink-500 mb-6">{job.company} · {job.industry}</p>

      <div className="grid grid-cols-2 gap-3 mb-6 text-sm">
        <div className="rounded-lg border border-ink-100 bg-white p-3">
          <p className="text-xs text-ink-500">Location</p>
          <p className="text-ink-900">{job.location}{job.is_remote ? " (Remote)" : ""}</p>
        </div>
        <div className="rounded-lg border border-ink-100 bg-white p-3">
          <p className="text-xs text-ink-500">Compensation</p>
          <p className="text-ink-900">{salaryText}</p>
        </div>
        <div className="rounded-lg border border-ink-100 bg-white p-3">
          <p className="text-xs text-ink-500">Experience</p>
          <p className="text-ink-900">{job.experience_min}–{job.experience_max} years{job.fresher_friendly ? " · Fresher-friendly" : ""}</p>
        </div>
        <div className="rounded-lg border border-ink-100 bg-white p-3">
          <p className="text-xs text-ink-500">Posted</p>
          <p className="text-ink-900">{job.posted_days_ago === 0 ? "Today" : `${job.posted_days_ago} days ago`}</p>
        </div>
      </div>

      <div className="rounded-lg border border-ink-100 bg-white p-5 mb-4">
        <p className="text-xs font-medium uppercase tracking-wider text-ink-500 mb-2">Description</p>
        <p className="text-sm text-ink-800 whitespace-pre-wrap">{job.description}</p>
      </div>

      {job.responsibilities.length > 0 && (
        <div className="rounded-lg border border-ink-100 bg-white p-5 mb-4">
          <p className="text-xs font-medium uppercase tracking-wider text-ink-500 mb-2">Responsibilities</p>
          <ul className="list-disc list-inside space-y-1">
            {job.responsibilities.map((r, i) => <li key={i} className="text-sm text-ink-800">{r}</li>)}
          </ul>
        </div>
      )}

      <div className="rounded-lg border border-ink-100 bg-white p-5 mb-6">
        <p className="text-xs font-medium uppercase tracking-wider text-ink-500 mb-2">Required skills</p>
        <div className="flex flex-wrap gap-2 mb-3">
          {job.skills_required.map((s) => <span key={s} className="rounded-full bg-signal-500/10 text-signal-700 px-2 py-0.5 text-xs">{s}</span>)}
        </div>
        {job.skills_nice_to_have.length > 0 && (
          <>
            <p className="text-xs font-medium uppercase tracking-wider text-ink-500 mb-2">Nice to have</p>
            <div className="flex flex-wrap gap-2">
              {job.skills_nice_to_have.map((s) => <span key={s} className="rounded-full bg-ink-50 text-ink-500 px-2 py-0.5 text-xs">{s}</span>)}
            </div>
          </>
        )}
      </div>

      <div className="flex gap-3 flex-wrap">
        <Link
          to={`/resume/tailor/${job.id}`}
          className="rounded-md bg-ink-950 hover:bg-ink-900 text-white px-4 py-2 text-sm font-medium transition-transform active:scale-95"
        >
          Tailor resume for this job
        </Link>
        <Link
          to={`/growth/roadmap/${job.id}`}
          className="rounded-md bg-ink-100 hover:bg-ink-200 text-ink-700 px-4 py-2 text-sm font-medium transition-transform active:scale-95"
        >
          Learning roadmap for this role
        </Link>
        <Link
          to={`/growth/interview/${job.id}`}
          className="rounded-md bg-ink-100 hover:bg-ink-200 text-ink-700 px-4 py-2 text-sm font-medium transition-transform active:scale-95"
        >
          Interview prep for {job.company}
        </Link>
        <Link
          to={`/copilot?job_id=${encodeURIComponent(job.id)}&company=${encodeURIComponent(job.company)}&role=${encodeURIComponent(job.title)}&prompt=${encodeURIComponent(`I am preparing to apply for the ${job.title} role at ${job.company}. How should I position my resume, what key competencies should I emphasize, and what interview strategies should I prepare?`)}`}
          className="rounded-md bg-ink-100 hover:bg-ink-200 text-ink-700 px-4 py-2 text-sm font-medium transition-transform active:scale-95"
        >
          🤖 Ask Copilot
        </Link>
        {(() => {
          const directApplyUrl = (job.apply_url && !job.apply_url.includes("example.com"))
            ? job.apply_url
            : `https://www.google.com/search?q=${encodeURIComponent(job.company + " " + job.title + " careers apply")}`;
          return (
            <a
              href={directApplyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md bg-signal-500 hover:bg-signal-600 text-white px-4 py-2 text-sm font-semibold transition-transform active:scale-95 shadow-xs flex items-center gap-1.5"
            >
              Apply Directly on Official Portal ↗
            </a>
          );
        })()}
      </div>
    </div>
  );
}
