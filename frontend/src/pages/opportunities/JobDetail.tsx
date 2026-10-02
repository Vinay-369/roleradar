import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams, useNavigate } from "react-router-dom";
import { getJobDetail } from "../../lib/jobDetail";
import { formatCompensation } from "../../lib/compensation";
import { normalizeJobDescriptionPresentation } from "../../lib/descriptionNormalization";
import { recordApplicationSubmission } from "../../lib/applications";
import { useToast } from "../../context/ToastContext";
import { 
  AlertTriangle, 
  ExternalLink, 
  Clock, 
  Building, 
  MapPin, 
  Briefcase, 
  Coins, 
  Sparkles, 
  ArrowLeft,
  ShieldCheck,
  Bookmark,
  Calendar,
  CircleCheck,
  XCircle,
  BarChart3,
  Map as MapIcon,
  Target,
  Bot,
} from "lucide-react";

export function JobDetail() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [showAppliedConfirmation, setShowAppliedConfirmation] = useState(false);
  const { jobId } = useParams<{ jobId: string }>();
  const { data: job, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["job-detail", jobId],
    queryFn: () => getJobDetail(jobId!),
    enabled: !!jobId,
    retry: 1,
  });
  const markAppliedMutation = useMutation({
    mutationFn: () => recordApplicationSubmission(jobId!),
    onSuccess: (application) => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      if (application.status === "APPLIED") {
        toast.success("Application tracker updated to Applied.");
      } else {
        toast.info(`Kept the existing tracker stage: ${application.status.replaceAll("_", " ")}.`);
      }
      setShowAppliedConfirmation(false);
    },
    onError: () => toast.error("Could not update the application tracker. Please try again."),
  });

  const presentation = useMemo(() => {
    if (!job) return { responsibilities: [], qualifications: [], detailedSections: [] };
    return normalizeJobDescriptionPresentation({
      description: job.description || "",
      responsibilities: job.responsibilities || [],
      qualifications: job.qualifications || [],
      skillsRequired: job.skills_required || [],
      skillsNiceToHave: job.skills_nice_to_have || [],
    });
  }, [job]);
  const summaryItems = presentation.summary?.items ?? [];

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 text-center">
        <div className="inline-block w-8 h-8 border-3 border-signal-600 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-sm font-medium text-ink-600">Loading opportunity details…</p>
      </div>
    );
  }

  if (isError) {
    const isUnauthorized = (error as any)?.response?.status === 401;
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 text-center">
        <AlertTriangle size={32} className="mx-auto text-amber-500 mb-2" />
        <h2 className="text-lg font-bold text-ink-900">
          {isUnauthorized ? "Authentication Required" : "Unable to Load Opportunity"}
        </h2>
        <p className="text-sm text-ink-500 mb-4 max-w-md mx-auto">
          {isUnauthorized
            ? "Your session has expired or you are not signed in. Please log in to view opportunity details."
            : "We encountered an issue loading this opportunity. Please check your connection and retry."}
        </p>
        <div className="flex items-center justify-center gap-3">
          {isUnauthorized ? (
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-signal-600 text-white rounded-lg text-xs font-semibold hover:bg-signal-700"
            >
              Sign In
            </Link>
          ) : (
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-signal-600 text-white rounded-lg text-xs font-semibold hover:bg-signal-700 cursor-pointer"
            >
              Retry
            </button>
          )}
          <Link to="/opportunities/jobs" className="text-sm font-semibold text-signal-600 hover:text-signal-700">
            ← Back to Discovery
          </Link>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 text-center">
        <AlertTriangle size={32} className="mx-auto text-amber-500 mb-2" />
        <h2 className="text-lg font-bold text-ink-900">Job Not Found</h2>
        <p className="text-sm text-ink-500 mb-4">The opportunity you requested does not exist or has been removed.</p>
        <Link to="/opportunities/jobs" className="text-sm font-semibold text-signal-600 hover:text-signal-700">
          ← Back to Discovery
        </Link>
      </div>
    );
  }

  const salaryText = formatCompensation(job);
  const uniqueSkills = (skills: string[] = []): string[] => [
    ...new Map<string, string>(
      skills
        .filter((skill) => skill.trim())
        .map((skill): [string, string] => [skill.toLowerCase().replace(/[^a-z0-9]/g, ""), skill])
    ).values(),
  ];
  const requiredSkills = uniqueSkills(job.skills_required);

  const isVerifiedActive = job.verification_status === "VERIFIED_ACTIVE" && job.is_direct_apply;
  const isBenchmark = job.verification_status === "MARKET_BENCHMARK";
  const isClosed = job.verification_status === "CLOSED" || job.verification_status === "EXPIRED";

  const experienceText = (() => {
    if (job.experience_text?.trim()) return job.experience_text.trim();
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
    return "Not specified by employer";
  })();

  const isSafeHttpUrl = (url?: string) => Boolean(url && (url.startsWith("https://") || url.startsWith("http://")));
  const hasDirectApply = Boolean(isVerifiedActive && isSafeHttpUrl(job.apply_url) && !job.apply_url.includes("example.com"));
  const isAggregatorListing = ["adzuna", "jsearch", "jooble"].includes(job.source);
  const hasProviderApply = Boolean(isVerifiedActive && isAggregatorListing && isSafeHttpUrl(job.apply_url));

  const postedText = (() => {
    if (job.posted_at) {
      const postedDate = new Date(job.posted_at);
      if (!Number.isNaN(postedDate.getTime())) {
        return `Posted ${postedDate.toLocaleDateString("en-IN", {
          month: "short",
          day: "numeric",
          year: "numeric",
        })}`;
      }
    }
    if (job.posted_days_ago !== undefined && job.posted_days_ago !== null && job.posted_days_ago > 0) {
      if (job.posted_days_ago === 1) return "Posted 1 day ago";
      if (job.posted_days_ago <= 14) return `Posted ${job.posted_days_ago} days ago`;
      return `Posted ${job.posted_days_ago} days ago`;
    }
    return "Not disclosed";
  })();

  const deadlineText = (() => {
    const dl = job.registration_closing_date || job.application_deadline || job.end_date;
    if (!dl) return null;
    try {
      const d = new Date(dl);
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString("en-IN", { month: "short", day: "numeric", year: "numeric" });
      }
    } catch {
      // ignore
    }
    return dl;
  })();

  const backLink = job.job_type === "internship" ? "/opportunities/internships" : "/opportunities/jobs";
  const backLabel = job.job_type === "internship" ? "Back to Internships" : "Back to Jobs";

  const eligibility = job.eligibility;
  const match = job.match;
  const matchScore = Math.max(0, Math.min(100, match?.overall_score ?? 0));
  const matchAccent = matchScore >= 70 ? "#059669" : matchScore >= 50 ? "#d97706" : "#e11d48";
  const hasEligibilityMismatch = eligibility?.status === "INELIGIBLE"
    || eligibility?.status === "EXPERIENCE_MISMATCH"
    || eligibility?.status === "DEGREE_MISMATCH"
    || eligibility?.status === "GRADUATION_MISMATCH"
    || eligibility?.status === "LOCATION_MISMATCH";
  const hasExplicitSkills = ((match?.matched_skills?.length ?? 0) + (match?.missing_skills?.length ?? 0)) > 0;
  const eligibilityDetails = [
    ...(eligibility?.reasons ?? []),
    ...(eligibility?.reasons?.length ? [] : [job.eligibility_text || eligibility?.fit_explanation]),
  ].filter((text, index, all): text is string =>
    typeof text === "string"
      && text.trim().length > 0
      && all.findIndex((item) =>
        typeof item === "string"
          && item.trim().toLocaleLowerCase() === text.trim().toLocaleLowerCase()
      ) === index
  );

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 px-4 pt-5 pb-20 sm:px-6 sm:pt-7">
      {/* Navigation Breadcrumb */}
      <button
        type="button"
        onClick={() => {
          if (window.history.length > 1) {
            navigate(-1);
          } else {
            navigate(backLink);
          }
        }}
        className="mb-1 inline-flex h-9 items-center gap-1.5 rounded-lg px-3 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-100 hover:text-signal-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-signal-300"
      >
        <ArrowLeft size={14} />
        <span>{backLabel}</span>
      </button>

      {/* Main Header Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800 sm:p-6">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="rounded-full border border-signal-200 bg-signal-50 px-2.5 py-1 text-[11px] font-semibold text-signal-700 dark:border-signal-900 dark:bg-signal-950/40 dark:text-signal-300">
                {job.job_type === "internship" ? "Internship" : "Full-time"}
              </span>
              {job.canonical_role && (
                <span className="rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-700 dark:text-slate-200">
                  {job.canonical_role}
                </span>
              )}
              {job.role_domain && (
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  {job.role_domain}
                </span>
              )}
            </div>

            <h1 className="mb-1 font-display text-2xl font-bold text-slate-950 dark:text-white sm:text-3xl">
              {job.title}
            </h1>

            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-50 px-2.5 py-1 font-semibold text-slate-800 dark:bg-slate-700 dark:text-slate-100">
                <Building size={14} className="text-ink-400" />
                {job.company}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-50 px-2.5 py-1 dark:bg-slate-700">
                <MapPin size={14} className="text-ink-400" />
                {job.location}
                {job.is_remote ? " (Remote)" : ""}
              </span>
              {job.industry && (
                <>
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs dark:border-slate-600 dark:bg-slate-700">{job.industry}</span>
                </>
              )}
            </div>
          </div>

          {/* Primary Action Buttons */}
          <div className="flex flex-col sm:flex-row md:flex-col gap-2 shrink-0 md:min-w-[180px]">
            {hasDirectApply || hasProviderApply ? (
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setShowAppliedConfirmation(true)}
                className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm transition-all hover:bg-indigo-700 active:scale-95 text-center"
              >
                <span>{hasDirectApply ? "Apply on Official Portal" : "Continue to Application"}</span>
                <ExternalLink size={13} />
              </a>
            ) : isBenchmark ? (
              <span
                className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs font-semibold text-amber-800 text-center dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                title="Curated market skill benchmark used for skills and readiness reference"
              >
                <Bookmark size={13} className="text-amber-600 shrink-0" />
                <span>Market Skill Benchmark</span>
              </span>
            ) : (
              <span
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-slate-100 px-4 py-2.5 text-xs font-medium text-slate-600 text-center dark:bg-slate-700 dark:text-slate-300"
                title="Official requisition application link is currently unavailable"
              >
                <AlertTriangle size={13} className="text-amber-500 shrink-0" />
                <span>Application Link Unavailable</span>
              </span>
            )}

            <Link
              to={`/resume/tailor/${job.id}`}
              className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl bg-signal-600 px-4 py-2 text-xs font-semibold text-white transition-all hover:bg-signal-700 active:scale-95 text-center"
            >
              <Sparkles size={13} className="text-signal-400" />
              <span>Tailor Resume</span>
            </Link>
          </div>
        </div>

        {/* Verification Status Alert */}
        <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-700">
          {isVerifiedActive ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs dark:border-emerald-800 dark:bg-emerald-950/40">
              <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                <span className="font-bold">Verified active listing · Direct employer application</span>
              </div>
              {job.completeness_status === "VERIFIED_COMPLETE" ? (
                <span className="rounded-full border border-emerald-300 bg-emerald-100/80 px-2.5 py-1 text-[10px] font-semibold text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                  Complete Employer Posting
                </span>
              ) : job.completeness_status === "VERIFIED_PARTIAL" ? (
                <span className="rounded-full border border-amber-300 bg-amber-100/80 px-2.5 py-1 text-[10px] font-semibold text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
                  Partial Disclosure
                </span>
              ) : null}
            </div>
          ) : isBenchmark ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs dark:border-amber-800 dark:bg-amber-950/30">
              <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
                <span className="font-bold">Market skill benchmark · Reference role, not an active opening</span>
              </div>
            </div>
          ) : isClosed ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs dark:border-rose-800 dark:bg-rose-950/30">
              <div className="flex items-center gap-2 text-rose-800 dark:text-rose-300">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0" />
                <span className="font-bold">Position closed or expired · No longer accepting applications</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-700 dark:bg-slate-900">
              <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-ink-400 shrink-0" />
                <span className="font-semibold">Curated opportunity · Verification refresh pending</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Metadata Key Statistics */}
      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3 lg:grid-cols-5">
        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="mb-1 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <Coins size={12} />
            Compensation
          </p>
          <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 sm:text-sm">{salaryText}</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="mb-1 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <Briefcase size={12} />
            Experience
          </p>
          <div className="text-xs sm:text-sm">
            <span className="block text-xs font-semibold text-slate-900 dark:text-slate-100 sm:text-sm">{experienceText}</span>
            {job.seniority && (
              <span className="text-xs text-ink-500 font-normal block mt-0.5">
                Seniority: <span className="font-medium text-ink-700">{job.seniority}</span>
              </span>
            )}
            {job.fresher_friendly && !job.seniority && (
              <span className="text-signal-700 text-xs block font-normal mt-0.5">Fresher-friendly</span>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="mb-1 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <Clock size={12} />
            Posting Date
          </p>
          <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 sm:text-sm">{postedText}</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <p className="mb-1 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <MapPin size={12} />
            Workplace
          </p>
          <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 sm:text-sm">
            {job.workplace_type ? job.workplace_type.replace("_", " ") : job.is_remote ? "Remote" : "On-site"}
          </p>
        </div>

        <div className={`rounded-xl border p-3.5 shadow-sm ${deadlineText ? "border-rose-200 bg-rose-50/60 dark:border-rose-900 dark:bg-rose-950/30" : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"}`}>
          <p className={`mb-1 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider ${deadlineText ? "text-rose-600 dark:text-rose-300" : "text-slate-500 dark:text-slate-400"}`}>
            <Calendar size={12} />
            Last Date to Apply
          </p>
          <p className={`text-xs font-semibold sm:text-sm ${deadlineText ? "text-rose-900 dark:text-rose-200" : "text-slate-500 dark:text-slate-400"}`}>
            {deadlineText || "Not disclosed"}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-4 flex items-center gap-2">
            <span className="grid size-8 place-items-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-300">
              <Sparkles size={15} />
            </span>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">Technical alignment</p>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">Resume-to-role compatibility</p>
            </div>
            {match && (
              <span className="ml-auto text-xl font-bold tabular-nums" style={{ color: matchAccent }}>
                {matchScore}%
              </span>
            )}
          </div>
          {match ? (
            <>
              <div
                className="h-2.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"
                role="progressbar"
                aria-label="Technical alignment"
                aria-valuenow={matchScore}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div className="h-full rounded-full transition-all" style={{ width: `${matchScore}%`, backgroundColor: matchAccent }} />
              </div>
              {hasExplicitSkills ? (
                <>
                  <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    Skill overlap between your master resume and the employer’s requirements.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
                      {match.matched_skills?.length ?? 0} skills matched
                    </span>
                    <span className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-[11px] font-semibold text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
                      {match.missing_skills?.length ?? 0} skills missing
                    </span>
                  </div>
                </>
              ) : (
                <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                  Overall compatibility reflects role title, experience level, and location. The employer did not provide explicit technical skills to evaluate.
                </p>
              )}
            </>
          ) : (
            <p className="text-xs italic text-slate-500 dark:text-slate-400">Upload your resume to calculate technical skill alignment.</p>
          )}
        </section>

        <section className={`rounded-2xl border p-5 shadow-sm ${
          hasEligibilityMismatch
            ? "border-amber-200 bg-amber-50/60 dark:border-amber-800 dark:bg-amber-950/20"
            : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
        }`}>
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-100">
              {hasEligibilityMismatch
                ? <AlertTriangle size={15} className="text-amber-600 dark:text-amber-400" />
                : <ShieldCheck size={15} className="text-indigo-600 dark:text-indigo-400" />}
              Eligibility
            </h2>
            {eligibility && (
              <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold ${
                eligibility.status === "ELIGIBLE" || eligibility.status === "LIKELY_ELIGIBLE"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
                  : hasEligibilityMismatch
                    ? "border-amber-300 bg-amber-100 text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-300"
                    : "border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
              }`}>
                {eligibility.status.replaceAll("_", " ")}
              </span>
            )}
          </div>
          {eligibilityDetails.length ? (
            <div>
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Your eligibility</p>
              <ul className="space-y-2 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                {eligibilityDetails.map((detail) => (
                  <li key={detail} className="flex items-start gap-2">
                    {hasEligibilityMismatch
                      ? <XCircle size={14} className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                      : <CircleCheck size={14} className="mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400" />}
                    <span>{detail}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div>
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Your eligibility</p>
              <p className="text-xs text-slate-600 dark:text-slate-400">Complete your candidate profile to view eligibility checks for this position.</p>
            </div>
          )}
          {(job.degree_requirements?.length
            || job.graduation_year_requirements?.length
            || job.student_eligible !== undefined && job.student_eligible !== null
            || job.fresher_eligible !== undefined && job.fresher_eligible !== null) && (
            <div className="mt-4 border-t border-amber-200/80 pt-3 dark:border-amber-800/70">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Employer criteria</p>
              <div className="flex flex-wrap gap-1.5">
                {job.degree_requirements?.map((degree) => (
                  <span key={degree} className="rounded-full border border-amber-200 bg-white/70 px-2.5 py-1 text-[11px] text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">{degree}</span>
                ))}
                {job.graduation_year_requirements?.length ? (
                  <span className="rounded-full border border-amber-200 bg-white/70 px-2.5 py-1 text-[11px] text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                    Graduation: {job.graduation_year_requirements.join(", ")}
                  </span>
                ) : null}
                {job.student_eligible !== undefined && job.student_eligible !== null && (
                  <span className={`rounded-full border px-2.5 py-1 text-[11px] ${
                    job.student_eligible
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
                      : "border-amber-200 bg-white/70 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
                  }`}>
                    Students {job.student_eligible ? "eligible" : "not eligible"}
                  </span>
                )}
                {job.fresher_eligible !== undefined && job.fresher_eligible !== null && (
                  <span className={`rounded-full border px-2.5 py-1 text-[11px] ${
                    job.fresher_eligible
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
                      : "border-amber-200 bg-white/70 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
                  }`}>
                    Freshers {job.fresher_eligible ? "eligible" : "not eligible"}
                  </span>
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      {summaryItems.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-3 text-sm font-bold text-slate-900 dark:text-slate-100">Role overview</h2>
          <div className="space-y-2 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
            {summaryItems.map((item, index) => item.isBullet ? (
              <div key={`${item.text}-${index}`} className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-signal-500 mt-1.5 shrink-0" />
                <span>{item.text}</span>
              </div>
            ) : <p key={`${item.text}-${index}`}>{item.text}</p>)}
          </div>
        </section>
      )}

      {(presentation.responsibilities.length > 0
        || presentation.qualifications.length > 0
        || presentation.additionalInfo
        || presentation.detailedSections.length > 0
        || (!summaryItems.length && job.description?.trim())) && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-5 flex items-center gap-2">
            <span className="grid size-8 place-items-center rounded-lg bg-sky-50 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300">
              <Briefcase size={15} />
            </span>
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">Opportunity details</h2>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">Responsibilities, qualifications, and employer-provided context</p>
            </div>
          </div>

          <div className="space-y-6">
            {presentation.responsibilities.length > 0 && (
              <div>
                <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">Responsibilities</h3>
                <ul className="space-y-2 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                  {presentation.responsibilities.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-sky-600 dark:bg-sky-400" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {presentation.qualifications.length > 0 && (
              <div>
                <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">Qualifications</h3>
                <ul className="space-y-2 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                  {presentation.qualifications.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-indigo-600 dark:bg-indigo-400" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {presentation.additionalInfo && (
              <div>
                <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">{presentation.additionalInfo.title || "Additional information"}</h3>
                <div className="space-y-2 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                  {presentation.additionalInfo.items.map((item, index) => (
                    <p key={`${item.text}-${index}`}>{item.text}</p>
                  ))}
                </div>
              </div>
            )}

            {presentation.detailedSections.map((section, sectionIndex) => (
              <div key={`${section.title || "details"}-${sectionIndex}`}>
                {section.title && (
                  <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">{section.title}</h3>
                )}
                <div className="space-y-2 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                  {section.items.map((item, itemIndex) => item.isBullet ? (
                    <div key={`${item.text}-${itemIndex}`} className="flex items-start gap-2">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-slate-500 dark:bg-slate-400" />
                      <span>{item.text}</span>
                    </div>
                  ) : (
                    <p key={`${item.text}-${itemIndex}`}>{item.text}</p>
                  ))}
                </div>
              </div>
            ))}

            {!summaryItems.length && !presentation.responsibilities.length && !presentation.qualifications.length
              && !presentation.additionalInfo && !presentation.detailedSections.length && job.description?.trim() && (
                <p className="whitespace-pre-line text-xs leading-relaxed text-slate-700 dark:text-slate-300">{job.description.trim()}</p>
              )}
          </div>
        </section>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between gap-3 mb-3">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">Required skills</h2>
          {requiredSkills.length > 0 && (
            <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">{requiredSkills.length} skills</span>
          )}
        </div>
        {requiredSkills.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {requiredSkills.map((skill) => {
              const normalizedSkill = skill.toLowerCase().replace(/[^a-z0-9]/g, "");
              const matched = uniqueSkills(match?.matched_skills ?? []).some(
                (matchedSkill) => matchedSkill.toLowerCase().replace(/[^a-z0-9]/g, "") === normalizedSkill
              );
              const missing = uniqueSkills(match?.missing_skills ?? []).some(
                (missingSkill) => missingSkill.toLowerCase().replace(/[^a-z0-9]/g, "") === normalizedSkill
              );
              const stateClass = matched
                ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
                : missing
                  ? "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
                  : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300";
              const stateLabel = matched ? "Matched" : missing ? "Missing" : hasExplicitSkills ? "Partial" : "Not assessed";

              return (
                <span key={skill} className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold ${stateClass}`}>
                  {matched ? <CircleCheck size={13} /> : missing ? <XCircle size={13} /> : <AlertTriangle size={13} />}
                  {skill}
                  <span className="text-[10px] font-medium opacity-75">{stateLabel}</span>
                </span>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-slate-500 dark:text-slate-400">The employer has not specified required skills for this role.</p>
        )}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">Preparation & Career Tools</p>
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          <Link
            to={`/growth/skill-gaps?jobId=${job.id}`}
            className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-semibold text-slate-700 shadow-sm transition-colors hover:border-indigo-300 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-indigo-700 dark:hover:text-indigo-300"
          >
            <BarChart3 size={15} /> Skill Gap
          </Link>
          <Link
            to={`/growth/roadmap/${job.id}`}
            className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-semibold text-slate-700 shadow-sm transition-colors hover:border-indigo-300 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-indigo-700 dark:hover:text-indigo-300"
          >
            <MapIcon size={15} /> Roadmap
          </Link>
          <Link
            to={`/growth/interview/${job.id}`}
            className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-semibold text-slate-700 shadow-sm transition-colors hover:border-indigo-300 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-indigo-700 dark:hover:text-indigo-300"
          >
            <Target size={15} /> Interview Prep
          </Link>
          <Link
            to={`/copilot?job_id=${encodeURIComponent(job.id)}&company=${encodeURIComponent(job.company)}&role=${encodeURIComponent(job.title)}&prompt=${encodeURIComponent(`I am preparing to apply for the ${job.title} role at ${job.company}. How should I position my resume, what key competencies should I emphasize, and what interview strategies should I prepare?`)}`}
            className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-semibold text-slate-700 shadow-sm transition-colors hover:border-indigo-300 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-indigo-700 dark:hover:text-indigo-300"
          >
            <Bot size={15} /> Ask Copilot
          </Link>
        </div>
      </section>

      {showAppliedConfirmation && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !markAppliedMutation.isPending) {
              setShowAppliedConfirmation(false);
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="applied-confirmation-title"
            className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-800"
          >
            <h2 id="applied-confirmation-title" className="text-base font-bold text-slate-900 dark:text-slate-100">
              Did you submit your application?
            </h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              RoleRadar can’t check applications on the employer’s website. If you completed the application, mark this opportunity as Applied in your tracker.
            </p>
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                disabled={markAppliedMutation.isPending}
                onClick={() => setShowAppliedConfirmation(false)}
                className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                Not yet
              </button>
              <button
                type="button"
                disabled={markAppliedMutation.isPending}
                onClick={() => markAppliedMutation.mutate()}
                className="rounded-lg bg-signal-600 px-3 py-2 text-xs font-semibold text-white hover:bg-signal-700 disabled:opacity-60"
              >
                {markAppliedMutation.isPending ? "Updating…" : "Yes, mark as applied"}
              </button>
            </div>
          </section>
        </div>
      )}

    </div>
  );
}
