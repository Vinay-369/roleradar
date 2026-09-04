import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { getJobDetail } from "../../lib/jobDetail";
import { AlertTriangle, ExternalLink } from "lucide-react";

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

  const isVerifiedActive = job.verification_status === "VERIFIED_ACTIVE" && job.is_direct_apply;
  const isBenchmark = job.verification_status === "MARKET_BENCHMARK";
  const isClosed = job.verification_status === "CLOSED" || job.verification_status === "EXPIRED";

  const experienceText = (() => {
    const hasMin = job.experience_min !== null && job.experience_min !== undefined;
    const hasMax = job.experience_max !== null && job.experience_max !== undefined;
    if (hasMin && hasMax) {
      if (job.experience_min === job.experience_max) {
        return `${job.experience_min} year${job.experience_min === 1 ? "" : "s"}`;
      }
      return `${job.experience_min}–${job.experience_max} years`;
    }
    if (hasMin) {
      return `${job.experience_min}+ years`;
    }
    if (hasMax) {
      return `Up to ${job.experience_max} years`;
    }
    return "Experience not specified";
  })();

  const hasDirectApply = Boolean(isVerifiedActive && job.apply_url && !job.apply_url.includes("example.com"));

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 sm:px-6">
      <Link to="/opportunities/jobs" className="text-xs text-ink-500 hover:text-ink-800 mb-4 inline-block">
        ← Back to jobs
      </Link>

      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <h1 className="font-display text-2xl text-ink-900">{job.title}</h1>
          <p className="text-ink-500">{job.company} · {job.industry}</p>
        </div>
        <span className="rounded-full bg-ink-100 text-ink-700 px-3 py-1 text-xs font-medium shrink-0">
          {job.job_type === "internship" ? "Internship" : "Full-time"}
        </span>
      </div>

      {/* Verification Status Banner */}
      {isVerifiedActive ? (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 mb-4 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-emerald-800">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-semibold">Verified Live Opportunity</span>
            <span className="text-emerald-700">• Official employer job board</span>
          </div>
          <span className="text-emerald-700 font-mono text-[11px]">
            Direct ATS Requisition
          </span>
        </div>
      ) : (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 mb-4 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-amber-800">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span className="font-semibold">{isBenchmark ? "Market Skill Benchmark" : "Curated Opportunity"}</span>
            {isClosed && <span className="text-rose-600 font-semibold">• Position Closed</span>}
          </div>
          <span className="text-amber-700 font-mono text-[11px]">
            {isBenchmark ? "Reference Role" : "Verification Pending"}
          </span>
        </div>
      )}

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
          <p className="text-ink-900">{experienceText}{job.fresher_friendly ? " · Fresher-friendly" : ""}</p>
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
        {hasDirectApply ? (
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md bg-signal-500 hover:bg-signal-600 text-white px-4 py-2 text-sm font-semibold transition-transform active:scale-95 shadow-xs flex items-center gap-1.5"
          >
            <span>Apply Directly on Official Portal</span>
            <ExternalLink size={14} />
          </a>
        ) : (
          <span
            className="rounded-md bg-amber-50 text-amber-800 border border-amber-200 px-4 py-2 text-sm font-medium flex items-center gap-1.5"
            title="RoleRadar cannot verify a direct application link for this posting"
          >
            <AlertTriangle size={14} className="text-amber-600 shrink-0" />
            <span>Application link unavailable</span>
          </span>
        )}
      </div>
    </div>
  );
}
