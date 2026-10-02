import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Bookmark, Building2, Calendar, Check, Clock3, ExternalLink, MapPin, Sparkles } from "lucide-react";
import type { JobMatch } from "../../lib/jobs";
import { formatCompensation } from "../../lib/compensation";
import { saveApplication } from "../../lib/applications";
import { WhyScoreModal } from "../common/WhyScoreModal";
import { useToast } from "../../context/ToastContext";

function formatLocation(value?: string | null): string | null {
  if (!value?.trim()) return null;

  const parts = value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const normalized = part.toLocaleLowerCase();
      if (normalized === "bengaluru" || normalized === "bangalore") return "Bangalore";
      if (normalized === "usa") return "USA";
      if (normalized === "uk") return "UK";
      return normalized.replace(/\b\p{L}/gu, (letter) => letter.toLocaleUpperCase());
    });

  return [...new Set(parts)].join(", ") || null;
}

function getScoreBadgeClass(score: number): string {
  if (score >= 70) return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900";
  if (score >= 50) return "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900";
  return "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";
}

export function JobMatchCard({ job, onViewDetail }: { job: JobMatch; onViewDetail?: () => void }) {
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

  const eligibility = job.eligibility;
  const isExpMismatch = eligibility?.status === "EXPERIENCE_MISMATCH";
  const isDegreeMismatch = eligibility?.status === "DEGREE_MISMATCH";
  const isEligible = eligibility?.status === "ELIGIBLE" || eligibility?.status === "LIKELY_ELIGIBLE";
  const hasGoodFit = job.realistic_fit === "GOOD_FIT";
  const score = job.has_match ? job.overall_score : null;
  const isInternship = job.job_type === "internship" || job.opportunity_type === "INTERNSHIP";
  const isAggregatorListing = ["adzuna", "jsearch", "jooble"].includes(job.source);
  const isVerifiedDirect = job.verification_status === "VERIFIED_ACTIVE" && job.is_direct_apply;
  const hasSafeApplyUrl = Boolean(
    job.apply_url
      && (job.apply_url.startsWith("https://") || job.apply_url.startsWith("http://"))
      && (isVerifiedDirect || (isAggregatorListing && job.verification_status === "VERIFIED_ACTIVE")),
  );
  const location = job.is_remote ? "Remote" : formatLocation(job.location);
  const compensation = formatCompensation(job);
  const compensationDisclosed = compensation !== "Not disclosed";
  const workplace = job.workplace_type && job.workplace_type !== "UNKNOWN"
    ? job.workplace_type.replaceAll("_", " ")
    : job.is_remote
      ? "Remote"
      : null;

  const freshnessLabel = (() => {
    if (job.posted_days_ago !== undefined && job.posted_days_ago !== null) {
      if (job.posted_days_ago === 0) return "Posted today";
      if (job.posted_days_ago === 1) return "Posted 1 day ago";
      if (job.posted_days_ago <= 14) return `Posted ${job.posted_days_ago} days ago`;
      if (job.verification_status === "VERIFIED_ACTIVE") return "Verified active · Continuous hiring";
      return `Posted ${job.posted_days_ago} days ago`;
    }
    return job.verification_status === "VERIFIED_ACTIVE" ? "Verified active" : "Active listing";
  })();

  const experienceDisplay = (() => {
    const hasMin = job.experience_min !== null && job.experience_min !== undefined;
    const hasMax = job.experience_max !== null && job.experience_max !== undefined;
    if (hasMin && hasMax) {
      if (job.experience_min === job.experience_max) {
        return `${job.experience_min} yr${job.experience_min === 1 ? "" : "s"} experience`;
      }
      return `${job.experience_min}–${job.experience_max} yrs experience`;
    }
    if (hasMin) return `${job.experience_min}+ yrs experience`;
    if (hasMax) return `Up to ${job.experience_max} yrs experience`;
    return null;
  })();

  const deadlineDisplay = (() => {
    const deadline = job.registration_closing_date || job.application_deadline || job.end_date;
    if (!deadline) return null;
    const date = new Date(deadline);
    return Number.isNaN(date.getTime())
      ? deadline.length > 25 ? `${deadline.slice(0, 25)}…` : deadline
      : date.toLocaleDateString("en-IN", { month: "short", day: "numeric", year: "numeric" });
  })();

  const fitLabel = isEligible && hasGoodFit
    ? "Eligible · Good fit"
    : isEligible
      ? job.has_match ? "Eligible for your profile" : "Eligible opening"
      : hasGoodFit
        ? "Good fit"
        : job.realistic_fit === "POSSIBLE_FIT"
          ? "Possible fit"
          : null;
  const warningLabel = isExpMismatch
    ? "Experience gap"
    : isDegreeMismatch
      ? "Degree requirement"
      : job.realistic_fit === "EXPERIENCE_GAP"
        ? "Experience gap"
        : null;

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all duration-200 hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {isVerifiedDirect && (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                <Check size={11} />
                Verified Direct
              </span>
            )}
            {job.verification_status === "VERIFIED_ACTIVE" && isAggregatorListing && (
              <span className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[10px] font-semibold text-sky-700">
                Live listing
              </span>
            )}
            {job.verification_status === "MARKET_BENCHMARK" && (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                Market benchmark
              </span>
            )}
          </div>
          <Link
            to={`/opportunities/job/${job.job_id}`}
            onClick={onViewDetail}
            className="block text-base font-bold leading-snug text-ink-900 hover:text-signal-700"
          >
            {job.job_title}
          </Link>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-slate-600 dark:text-slate-400">
            <span className="inline-flex items-center gap-1.5 font-semibold text-ink-700 dark:text-slate-200">
              <Building2 size={13} className="text-slate-400" /> {job.company}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Clock3 size={12} className="text-slate-400" /> {freshnessLabel}
            </span>
          </div>
        </div>

        <div className="flex shrink-0 items-start gap-2">
          {score !== null && score !== undefined && (
            <span className={`inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-sm font-bold tabular-nums ${getScoreBadgeClass(score)}`}>
              {score}% <span className="text-[10px] font-semibold">match</span>
            </span>
          )}
          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={save.isPending || save.isSuccess}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-800 disabled:cursor-default disabled:opacity-70 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
            aria-label={save.isSuccess ? "Saved opportunity" : "Save opportunity"}
            title={save.isSuccess ? "Saved" : "Save opportunity"}
          >
            {save.isSuccess ? <Check size={15} className="text-emerald-600" /> : <Bookmark size={15} />}
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {isInternship ? "Internship" : "Full-time"}
        </span>
        {workplace && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {workplace}
          </span>
        )}
        {compensationDisclosed ? (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {compensation}
          </span>
        ) : (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">
            Salary not disclosed
          </span>
        )}
        {experienceDisplay && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {experienceDisplay}
          </span>
        )}
        {location && (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            <MapPin size={12} />
            {location}
          </span>
        )}
        {deadlineDisplay && (
          <span
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
            title={`Application deadline: ${job.registration_closing_date || job.application_deadline || job.end_date}`}
          >
            <Calendar size={12} />
            Closes {deadlineDisplay}
          </span>
        )}
        {job.seniority && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {job.seniority}
          </span>
        )}
      </div>

      {(fitLabel || warningLabel) && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {fitLabel && (
            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
              {fitLabel}
            </span>
          )}
          {warningLabel && (
            <span
            className="inline-flex cursor-help items-center rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300"
              title={eligibility?.reasons?.[0] || "Review the eligibility details before applying."}
            >
              ⚠ {warningLabel}
            </span>
          )}
        </div>
      )}

      {job.has_match && job.missing_skills.length > 0 ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <div className="flex min-w-0 flex-1 flex-wrap gap-1.5">
            {job.missing_skills.slice(0, 4).map((skill) => (
              <span
                key={skill}
                className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
                title={`Missing skill: ${skill}`}
              >
                + {skill}
              </span>
            ))}
            {job.missing_skills.length > 4 && (
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                +{job.missing_skills.length - 4} more
              </span>
            )}
          </div>
          <WhyScoreModal
            job={job}
            triggerClassName="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-ink-500 hover:text-signal-700"
          />
        </div>
      ) : job.has_match ? (
        <div className="mt-4 flex justify-end">
          <WhyScoreModal
            job={job}
            triggerClassName="inline-flex items-center gap-1 text-xs font-medium text-ink-500 hover:text-signal-700"
          />
        </div>
      ) : job.skills_required?.length ? (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {job.skills_required.slice(0, 5).map((skill) => (
            <span key={skill} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {skill}
            </span>
          ))}
          {job.skills_required.length > 5 && (
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">
              +{job.skills_required.length - 5} more
            </span>
          )}
        </div>
      ) : null}

      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-slate-200 pt-4 dark:border-slate-800">
        {hasSafeApplyUrl && (
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-10 items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-4 text-xs font-bold text-white shadow-sm transition-colors hover:bg-indigo-700 sm:text-sm"
            title={isVerifiedDirect ? `Apply directly on ${job.company}'s official portal` : `Continue to ${job.company}'s listing`}
          >
            Apply
            <ExternalLink size={13} />
          </a>
        )}
        <Link
          to={`/opportunities/job/${job.job_id}`}
          onClick={onViewDetail}
          className="inline-flex h-10 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-4 text-xs font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 sm:text-sm"
        >
          View Details
          <ArrowRight size={13} />
        </Link>
        <Link
          to={job.has_match ? `/resume/tailor/${job.job_id}` : `/resume/master?targetJobId=${encodeURIComponent(job.job_id)}`}
          className="inline-flex h-10 items-center justify-center gap-1.5 rounded-lg bg-signal-50 px-3 text-xs font-semibold text-signal-800 transition-colors hover:bg-signal-100 dark:bg-signal-950/40 dark:text-signal-300 dark:hover:bg-signal-950/70 sm:text-sm"
        >
          <Sparkles size={13} className="text-signal-600" />
          {job.has_match ? "Tailor Resume" : "Tailor"}
        </Link>
      </div>
    </article>
  );
}
