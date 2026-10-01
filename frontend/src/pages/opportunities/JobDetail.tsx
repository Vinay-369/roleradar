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
  CheckCircle2, 
  Clock, 
  Building, 
  MapPin, 
  Briefcase, 
  Coins, 
  Sparkles, 
  ArrowLeft,
  ShieldCheck,
  Bookmark,
  Calendar
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
  const hasExplicitSkills = ((match?.matched_skills?.length ?? 0) + (match?.missing_skills?.length ?? 0)) > 0;
  const eligibilityDetails = [
    job.eligibility_text,
    ...(eligibility?.reasons ?? []),
    eligibility?.fit_explanation,
  ].filter((text, index, all): text is string =>
    typeof text === "string"
      && text.trim().length > 0
      && all.findIndex((item) =>
        typeof item === "string"
          && item.trim().toLocaleLowerCase() === text.trim().toLocaleLowerCase()
      ) === index
  );

  return (
    <div className="max-w-4xl mx-auto pt-4 sm:pt-5 pb-12 px-4 sm:px-6">
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
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-ink-500 hover:text-signal-700 transition-colors mb-2.5 cursor-pointer bg-transparent border-0 p-0"
      >
        <ArrowLeft size={14} />
        <span>{backLabel}</span>
      </button>

      {/* Main Header Card */}
      <div className="bg-white rounded-2xl border border-ink-100 p-5 mb-4 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="rounded-md bg-signal-50 text-signal-700 border border-signal-200 px-2.5 py-0.5 text-xs font-semibold">
                {job.job_type === "internship" ? "Internship" : "Full-time"}
              </span>
              {job.canonical_role && (
                <span className="rounded-md bg-ink-100 text-ink-800 px-2.5 py-0.5 text-xs font-medium">
                  {job.canonical_role}
                </span>
              )}
              {job.role_domain && (
                <span className="rounded-md bg-ink-50 text-ink-600 px-2 py-0.5 text-xs">
                  {job.role_domain}
                </span>
              )}
              {deadlineText && (
                <span className="rounded-md bg-rose-50 text-rose-700 border border-rose-200/80 px-2.5 py-0.5 text-xs font-semibold flex items-center gap-1">
                  <Calendar size={12} className="text-rose-500" />
                  <span>Apply by: {deadlineText}</span>
                </span>
              )}
            </div>

            <h1 className="font-display text-2xl sm:text-3xl font-bold text-ink-950 mb-1">
              {job.title}
            </h1>

            <div className="flex items-center gap-3 text-sm text-ink-600 flex-wrap">
              <span className="font-semibold text-ink-900 flex items-center gap-1">
                <Building size={14} className="text-ink-400" />
                {job.company}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <MapPin size={14} className="text-ink-400" />
                {job.location}
                {job.is_remote ? " (Remote)" : ""}
              </span>
              {job.industry && (
                <>
                  <span>•</span>
                  <span>{job.industry}</span>
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
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-signal-600 hover:bg-signal-700 text-white px-4 py-2.5 text-xs font-bold transition-all shadow-sm active:scale-95 text-center"
              >
                <span>{hasDirectApply ? "Apply on Official Portal" : "Continue to Application"}</span>
                <ExternalLink size={13} />
              </a>
            ) : isBenchmark ? (
              <span
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 px-4 py-2.5 text-xs font-semibold text-center"
                title="Curated market skill benchmark used for skills and readiness reference"
              >
                <Bookmark size={13} className="text-amber-600 shrink-0" />
                <span>Market Skill Benchmark</span>
              </span>
            ) : (
              <span
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-ink-100 text-ink-500 px-4 py-2.5 text-xs font-medium text-center"
                title="Official requisition application link is currently unavailable"
              >
                <AlertTriangle size={13} className="text-amber-500 shrink-0" />
                <span>Application Link Unavailable</span>
              </span>
            )}

            <Link
              to={`/resume/tailor/${job.id}`}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-ink-900 hover:bg-ink-950 text-white px-4 py-2 text-xs font-semibold transition-all active:scale-95 text-center"
            >
              <Sparkles size={13} className="text-signal-400" />
              <span>Tailor Resume</span>
            </Link>
          </div>
        </div>

        {/* Verification Status Alert */}
        <div className="mt-5 pt-4 border-t border-ink-100">
          {isVerifiedActive ? (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 flex items-center justify-between text-xs flex-wrap gap-2">
              <div className="flex items-center gap-2 text-emerald-800">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                <span className="font-bold">Verified Live Opportunity</span>
                <span className="text-emerald-700">• Official employer applicant tracking system</span>
              </div>
              <div className="flex items-center gap-2">
                {job.completeness_status === "VERIFIED_COMPLETE" ? (
                  <span className="rounded bg-emerald-100/80 text-emerald-800 border border-emerald-300 px-2 py-0.5 text-[10px] font-semibold">
                    Complete Employer Posting
                  </span>
                ) : job.completeness_status === "VERIFIED_PARTIAL" ? (
                  <span className="rounded bg-amber-100/80 text-amber-800 border border-amber-300 px-2 py-0.5 text-[10px] font-semibold">
                    Partial Disclosure
                  </span>
                ) : null}
                <span className="text-emerald-700 font-mono text-[11px] font-semibold">
                  Direct Employer ATS
                </span>
              </div>
            </div>
          ) : isBenchmark ? (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 flex items-center justify-between text-xs flex-wrap gap-2">
              <div className="flex items-center gap-2 text-amber-800">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
                <span className="font-bold">Market Skill Benchmark</span>
                <span className="text-amber-700">• Reference career role for benchmarking skills and readiness</span>
              </div>
              <span className="text-amber-700 font-mono text-[11px] font-semibold">
                Curated Benchmark
              </span>
            </div>
          ) : isClosed ? (
            <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-3 flex items-center justify-between text-xs flex-wrap gap-2">
              <div className="flex items-center gap-2 text-rose-800">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0" />
                <span className="font-bold">Position Closed or Expired</span>
                <span className="text-rose-700">• No longer accepting new applications</span>
              </div>
              <span className="text-rose-700 font-mono text-[11px] font-semibold">
                Closed
              </span>
            </div>
          ) : (
            <div className="rounded-xl border border-ink-200 bg-ink-50 p-3 flex items-center justify-between text-xs flex-wrap gap-2">
              <div className="flex items-center gap-2 text-ink-700">
                <span className="w-2.5 h-2.5 rounded-full bg-ink-400 shrink-0" />
                <span className="font-semibold">Curated Opportunity</span>
                <span className="text-ink-500">• Verification refresh pending</span>
              </div>
              <span className="text-ink-600 font-mono text-[11px]">
                Standard Requisition
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Metadata Key Statistics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 mb-4 text-sm">
        <div className="rounded-xl border border-ink-100 bg-white p-3.5 shadow-2xs">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-400 mb-1 flex items-center gap-1">
            <Coins size={12} />
            Compensation
          </p>
          <p className="font-semibold text-ink-900 text-xs sm:text-sm">{salaryText}</p>
        </div>

        <div className="rounded-xl border border-ink-100 bg-white p-3.5 shadow-2xs">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-400 mb-1 flex items-center gap-1">
            <Briefcase size={12} />
            Experience
          </p>
          <div className="text-xs sm:text-sm">
            <span className="font-semibold text-ink-900 block">{experienceText}</span>
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

        <div className="rounded-xl border border-ink-100 bg-white p-3.5 shadow-2xs">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-400 mb-1 flex items-center gap-1">
            <Clock size={12} />
            Posting Date
          </p>
          <p className="font-semibold text-ink-900 text-xs sm:text-sm">{postedText}</p>
        </div>

        <div className="rounded-xl border border-ink-100 bg-white p-3.5 shadow-2xs">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-400 mb-1 flex items-center gap-1">
            <MapPin size={12} />
            Workplace
          </p>
          <p className="font-semibold text-ink-900 text-xs sm:text-sm">
            {job.workplace_type ? job.workplace_type.replace("_", " ") : job.is_remote ? "Remote" : "On-site"}
          </p>
        </div>

        <div className={`rounded-xl border p-3.5 shadow-2xs ${deadlineText ? "border-rose-200/80 bg-rose-50/40" : "border-ink-100 bg-white"}`}>
          <p className={`text-[11px] font-semibold uppercase tracking-wider mb-1 flex items-center gap-1 ${deadlineText ? "text-rose-600" : "text-ink-400"}`}>
            <Calendar size={12} />
            Last Date to Apply
          </p>
          <p className={`font-semibold text-xs sm:text-sm ${deadlineText ? "text-rose-900" : "text-ink-500"}`}>
            {deadlineText || "Not disclosed"}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 mb-4">
        <div className="rounded-xl border border-ink-100 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-bold uppercase tracking-wider text-ink-500 flex items-center gap-1.5">
              <Sparkles size={13} className="text-signal-600" />
              Technical Alignment
            </p>
            {match && (hasExplicitSkills ? (
              <span className="text-base font-bold font-mono text-signal-700">{match.overall_score}%</span>
            ) : (
              <span className="rounded-md bg-ink-100 text-ink-700 px-2 py-0.5 text-[11px] font-semibold">
                Limited Technical Evidence
              </span>
            ))}
          </div>
          {match ? (
            hasExplicitSkills ? (
              <>
                <p className="text-xs text-ink-600 mb-3">
                  Evaluates technical skill overlap between your master resume and this job's requirements.
                </p>
                <div className="flex gap-4 text-xs font-medium">
                  <span className="text-emerald-700"><b>{match.matched_skills?.length ?? 0}</b> skills matched</span>
                  <span className="text-rose-700"><b>{match.missing_skills?.length ?? 0}</b> skills missing</span>
                </div>
              </>
            ) : (
              <p className="text-xs text-ink-600">
                Overall compatibility ({match.overall_score}%) reflects role title, experience level, and location compatibility. The employer did not provide explicit technical skills to evaluate.
              </p>
            )
          ) : (
            <p className="text-xs text-ink-400 italic">Upload your resume to calculate technical skill alignment.</p>
          )}
        </div>

        <div className="rounded-xl border border-ink-100 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between gap-3 mb-2">
            <h2 className="text-xs font-bold uppercase tracking-wider text-ink-700 flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-indigo-600" />
              Candidate Eligibility
            </h2>
            {eligibility && (
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                eligibility.status === "ELIGIBLE" || eligibility.status === "LIKELY_ELIGIBLE"
                  ? "bg-emerald-100 text-emerald-800"
                  : eligibility.status === "INELIGIBLE"
                    ? "bg-rose-100 text-rose-800"
                    : "bg-ink-100 text-ink-700"
              }`}>
                {eligibility.status.replaceAll("_", " ")}
              </span>
            )}
          </div>
          {eligibilityDetails.length ? (
            <ul className="space-y-1.5 text-xs text-ink-700">
              {eligibilityDetails.map((detail) => <li key={detail}>{detail}</li>)}
            </ul>
          ) : (
            <p className="text-xs text-ink-500">Complete your candidate profile to view eligibility checks for this position.</p>
          )}
          {(job.degree_requirements?.length
            || job.graduation_year_requirements?.length
            || job.student_eligible !== undefined && job.student_eligible !== null
            || job.fresher_eligible !== undefined && job.fresher_eligible !== null) && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {job.degree_requirements?.map((degree) => (
                <span key={degree} className="rounded-md bg-indigo-50 px-2 py-1 text-[11px] text-indigo-800">{degree}</span>
              ))}
              {job.graduation_year_requirements?.length ? (
                <span className="rounded-md bg-indigo-50 px-2 py-1 text-[11px] text-indigo-800">
                  Graduation: {job.graduation_year_requirements.join(", ")}
                </span>
              ) : null}
              {job.student_eligible !== undefined && job.student_eligible !== null && (
                <span className="rounded-md bg-indigo-50 px-2 py-1 text-[11px] text-indigo-800">
                  {job.student_eligible ? "Students eligible" : "Students not eligible"}
                </span>
              )}
              {job.fresher_eligible !== undefined && job.fresher_eligible !== null && (
                <span className="rounded-md bg-indigo-50 px-2 py-1 text-[11px] text-indigo-800">
                  {job.fresher_eligible ? "Freshers eligible" : "Freshers not eligible"}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {job.company_description && (
        <div className="rounded-xl border border-ink-100 bg-white p-4 mb-4 shadow-2xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-ink-700 mb-2">About {job.company}</h2>
          <p className="text-xs text-ink-600 leading-relaxed line-clamp-3">{job.company_description}</p>
        </div>
      )}

      {presentation.summary?.items.length ? (
        <div className="rounded-xl border border-ink-100 bg-white p-5 mb-4 shadow-2xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-ink-700 mb-3">Job Summary & Overview</h2>
          <div className="space-y-2 text-xs text-ink-700 leading-relaxed">
            {presentation.summary.items.map((item, index) =>
              item.isBullet ? (
                <div key={`${item.text}-${index}`} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-signal-500 mt-1.5 shrink-0" />
                  <span>{item.text}</span>
                </div>
              ) : <p key={`${item.text}-${index}`}>{item.text}</p>
            )}
          </div>
        </div>
      ) : null}

      {presentation.responsibilities.length ? (
        <div className="rounded-xl border border-ink-100 bg-white p-5 mb-4 shadow-2xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-ink-700 mb-3">Core Responsibilities</h2>
          <ul className="space-y-2">
            {presentation.responsibilities.map((item, index) => (
              <li key={`${item}-${index}`} className="text-xs text-ink-800 flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-signal-500 mt-1.5 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* 3. Structured Job Requirements: Required vs Preferred vs Contextual */}
      <div className="rounded-xl border border-ink-100 bg-white p-5 mb-4 shadow-2xs space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-700 flex items-center gap-1.5">
              <CheckCircle2 size={13} className="text-signal-600" />
              Employer Required Skills
            </h3>
            <span className="text-[11px] text-ink-400">Employer Requirements (Zero Inferred)</span>
          </div>

          {job.skills_required && job.skills_required.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {job.skills_required.map((skill) => (
                <span
                  key={skill}
                  className="rounded-lg bg-signal-500/10 border border-signal-500/20 text-signal-800 px-2.5 py-1 text-xs font-semibold"
                >
                  {skill}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-ink-400 italic">
              No specific mandatory skills disclosed by employer in the posting.
            </p>
          )}
        </div>

        {job.skills_nice_to_have && job.skills_nice_to_have.length > 0 && (
          <div className="pt-3 border-t border-ink-50">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 mb-2">
              Employer Preferred Skills
            </h4>
            <div className="flex flex-wrap gap-2">
              {job.skills_nice_to_have.map((skill) => (
                <span
                  key={skill}
                  className="rounded-lg bg-ink-50 border border-ink-200 text-ink-700 px-2.5 py-1 text-xs font-medium"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

      </div>

      {presentation.qualifications.length ? (
        <div className="rounded-xl border border-ink-100 bg-white p-5 mb-4 shadow-2xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-ink-700 mb-3">
            Qualifications & Educational Requirements
          </h2>
          <ul className="space-y-2">
            {presentation.qualifications.map((item, index) => (
              <li key={`${item}-${index}`} className="text-xs text-ink-800 flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {presentation.additionalInfo?.items.length ? (
        <div className="rounded-xl border border-ink-100 bg-white p-5 mb-4 shadow-2xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-ink-700 mb-3">Additional Information</h2>
          <div className="space-y-2 text-xs text-ink-700 leading-relaxed">
            {presentation.additionalInfo.items.map((item, index) =>
              item.isBullet ? (
                <div key={`${item.text}-${index}`} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-ink-400 mt-1.5 shrink-0" />
                  <span>{item.text}</span>
                </div>
              ) : <p key={`${item.text}-${index}`}>{item.text}</p>
            )}
          </div>
        </div>
      ) : null}

      {presentation.detailedSections.length ? (
        <div className="rounded-xl border border-ink-100 bg-white p-5 mb-4 shadow-2xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-ink-700 mb-3">Detailed Description</h2>
          <div className="space-y-4">
            {presentation.detailedSections.map((section, index) => (
              <section key={`${section.title}-${index}`} className="space-y-2">
                {section.title && <h3 className="text-xs font-bold uppercase tracking-wider text-ink-800">{section.title}</h3>}
                <div className="space-y-1.5">
                  {section.items.map((item, itemIndex) => item.isBullet ? (
                    <div key={`${item.text}-${itemIndex}`} className="text-xs text-ink-700 flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-ink-400 mt-1.5 shrink-0" />
                      <span className="leading-relaxed">{item.text}</span>
                    </div>
                  ) : <p key={`${item.text}-${itemIndex}`} className="text-xs text-ink-700 leading-relaxed">{item.text}</p>)}
                </div>
              </section>
            ))}
          </div>
        </div>
      ) : null}

      <div className="bg-ink-50/70 border border-ink-200 rounded-xl p-4 mb-4">
        <p className="text-xs font-bold uppercase tracking-wider text-ink-600 mb-3">Preparation & Career Tools</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <Link
            to={`/growth/skill-gaps?jobId=${job.id}`}
            className="p-3 rounded-lg bg-white border border-ink-200 hover:border-signal-500 text-xs font-medium text-ink-800 hover:text-signal-700 transition-colors shadow-2xs text-center"
          >
            📊 Skill Gap
          </Link>
          <Link
            to={`/growth/roadmap/${job.id}`}
            className="p-3 rounded-lg bg-white border border-ink-200 hover:border-signal-500 text-xs font-medium text-ink-800 hover:text-signal-700 transition-colors shadow-2xs text-center"
          >
            🗺️ Roadmap
          </Link>
          <Link
            to={`/growth/interview/${job.id}`}
            className="p-3 rounded-lg bg-white border border-ink-200 hover:border-signal-500 text-xs font-medium text-ink-800 hover:text-signal-700 transition-colors shadow-2xs text-center"
          >
            🎯 Interview Prep
          </Link>
          <Link
            to={`/copilot?job_id=${encodeURIComponent(job.id)}&company=${encodeURIComponent(job.company)}&role=${encodeURIComponent(job.title)}&prompt=${encodeURIComponent(`I am preparing to apply for the ${job.title} role at ${job.company}. How should I position my resume, what key competencies should I emphasize, and what interview strategies should I prepare?`)}`}
            className="p-3 rounded-lg bg-white border border-ink-200 hover:border-signal-500 text-xs font-medium text-ink-800 hover:text-signal-700 transition-colors shadow-2xs text-center"
          >
            🤖 Ask Copilot
          </Link>
        </div>
      </div>

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
            className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl"
          >
            <h2 id="applied-confirmation-title" className="text-base font-bold text-ink-900">
              Did you submit your application?
            </h2>
            <p className="mt-2 text-sm text-ink-600">
              RoleRadar can’t check applications on the employer’s website. If you completed the application, mark this opportunity as Applied in your tracker.
            </p>
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                disabled={markAppliedMutation.isPending}
                onClick={() => setShowAppliedConfirmation(false)}
                className="rounded-lg border border-ink-200 px-3 py-2 text-xs font-semibold text-ink-700 hover:bg-ink-50 disabled:opacity-60"
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
