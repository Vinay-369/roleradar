import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Sparkles, Briefcase, Bookmark, ArrowRight, FileText, Building2,
  ShieldCheck, Map, MessageCircleQuestion, CheckCircle2,
  TrendingUp, Compass, Zap, Target, FileEdit,
} from "lucide-react";
import { getDashboard } from "../lib/dashboard";
import { getProfile } from "../lib/profile";
import { useAuth } from "../context/AuthContext";
import { ScoreRing } from "../components/ui/ScoreRing";

function CareerLoopHub() {
  const stages = [
    { label: "Master Resume", desc: "ATS Audit & Scores", to: "/resume/master", icon: FileText, color: "text-signal-600" },
    { label: "Live Matches", desc: "Real Job Openings", to: "/opportunities/jobs", icon: Briefcase, color: "text-blue-600" },
    { label: "Truth Guard Tailor", desc: "1-Page Tailored PDF", to: "/resume/versions", icon: ShieldCheck, color: "text-purple-600" },
    { label: "Saved Roles", desc: "Bookmarked Openings", to: "/applications?tab=SAVED", icon: Bookmark, color: "text-amber-600" },
    { label: "Skill Roadmap", desc: "4-Sprint Bridge", to: "/growth/roadmap", icon: Map, color: "text-emerald-600" },
    { label: "Interview Prep", desc: "Top 20 Questions", to: "/growth/interview", icon: MessageCircleQuestion, color: "text-indigo-600" },
  ];

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-4 mb-5 shadow-sm transition-shadow hover:shadow-md sm:p-5">
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-2">
          <span className="p-1 rounded-md bg-indigo-50 text-indigo-600">
            <Sparkles size={14} />
          </span>
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Connected Career Acceleration Loop
          </h2>
        </div>
        <span className="text-[11px] font-semibold text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200/60">
          6-Stage Integrated Engine
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5">
        {stages.map((st, idx) => {
          const Icon = st.icon;
          return (
            <Link
              key={st.to}
              to={st.to}
              className="rr-interactive-card group flex flex-col justify-between rounded-xl border border-slate-200/80 bg-white p-3 shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono font-semibold text-indigo-600">
                    0{idx + 1}
                  </span>
                  <Icon size={16} className={`${st.color} transition-transform group-hover:scale-110`} />
                </div>
                <p className="text-xs font-bold leading-tight text-slate-900 group-hover:text-indigo-700">
                  {st.label}
                </p>
                <p className="mt-1 text-[11px] leading-snug text-slate-500">
                  {st.desc}
                </p>
              </div>
              <span className="mt-2.5 flex items-center gap-1 text-[10px] font-semibold text-indigo-600 opacity-0 transition-opacity group-hover:opacity-100">
                Open <ArrowRight size={10} />
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="max-w-5xl space-y-6">
      <div className="rr-skeleton h-28 rounded-2xl" />
      <div className="rr-skeleton h-36 rounded-2xl" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="rr-skeleton h-44 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}

function getMatchScoreStyle(score: number): string {
  if (score > 70) return "border-emerald-200 bg-emerald-50 text-emerald-600";
  if (score >= 50) return "border-amber-200 bg-amber-50 text-amber-600";
  return "border-rose-200 bg-rose-50 text-rose-600";
}

export function Dashboard() {
  const { user } = useAuth();
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });

  if (isLoading) return <DashboardSkeleton />;
  if (!data) return null;

  const totalApplications = Object.values(data.application_counts).reduce((a, b) => a + b, 0);
  const targetRole = profile?.target_roles?.[0] || "Software Engineer";

  return (
    <div className="max-w-6xl space-y-5 animate-fade-in-up">
      {/* 1. Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-gradient-to-r from-indigo-50/60 to-white p-6 text-slate-900 shadow-sm sm:p-7 dark:border-ink-200 dark:from-ink-950 dark:via-ink-900 dark:to-ink-950 dark:text-white">
        <div className="absolute -right-12 -top-12 h-48 w-48 rounded-full bg-indigo-300/20 blur-3xl animate-pulse-soft dark:bg-signal-500/20" />
        <div className="absolute right-32 bottom-0 h-32 w-32 rounded-full bg-indigo-200/30 blur-2xl dark:bg-signal-400/15" />

        <div className="relative flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-2.5">
              <div className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200/60 bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 dark:border-white/15 dark:bg-white/10 dark:text-signal-300">
                <span className="h-2 w-2 rounded-full bg-indigo-500 animate-ping dark:bg-signal-400" />
                <span>RoleRadar Intelligence Active</span>
              </div>
              <Link
                to="/growth/skill-gaps"
                className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200/60 bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 transition-colors hover:bg-indigo-100 dark:border-signal-400/30 dark:bg-signal-500/20 dark:text-signal-200 dark:hover:bg-signal-500/30"
                title="View canonical career skill map and gaps for this role"
              >
                <Target size={11} className="text-indigo-600 dark:text-signal-400" />
                <span>Targeting: {targetRole}</span>
              </Link>
            </div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl dark:text-white">
              Welcome back{user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}
            </h1>
            <p className="mt-1 max-w-xl text-xs text-slate-600 sm:text-sm dark:text-ink-300">
              {data.resume_uploaded
                ? `Track your ATS screening fit for ${targetRole}, discover verified live job openings, and tailor resumes in seconds.`
                : `Upload your resume to begin ATS analysis for ${targetRole}, discover live job openings, and tailor your resume in seconds.`}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <Link
              to="/opportunities/jobs"
              className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm shadow-indigo-500/20 transition-all hover:bg-indigo-700 active:scale-[0.98]"
            >
              <Compass size={14} />
              <span>Explore Jobs</span>
            </Link>
            <Link
              to="/growth/interview"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 transition-all hover:bg-slate-50 active:scale-[0.98] dark:border-white/20 dark:bg-white/10 dark:text-white dark:hover:bg-white/20"
            >
              <Zap size={14} className="text-amber-400" />
              <span>Mock Interview</span>
            </Link>
          </div>
        </div>
      </div>

      {/* 2. Connected Career Loop */}
      <CareerLoopHub />

      {!data.resume_uploaded ? (
        <div className="rounded-2xl border border-signal-500/30 bg-gradient-to-r from-signal-500/10 via-signal-500/5 to-white p-6 shadow-xs card-hover">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-signal-500 text-white flex items-center justify-center shrink-0 shadow-xs">
              <FileText size={20} />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-bold text-ink-900 mb-1">Upload Your Master Resume to Unlock AI Match Scoring</h3>
              <p className="text-xs text-ink-600 mb-4 max-w-xl leading-relaxed">
                {data.recommended_next_action || "Upload your PDF or DOCX resume to get an instant strict enterprise ATS score, identify missing skills, and unlock 1-click tailoring."}
              </p>
              <Link
                to="/resume/master"
                className="inline-flex items-center gap-1.5 rounded-xl bg-ink-950 hover:bg-ink-900 text-white px-4 py-2.5 text-xs font-semibold shadow-sm transition-all active:scale-95"
              >
                <span>Upload Master Resume</span>
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* 3. Core Benchmark KPI Rings */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div
              title="Role readiness combines ATS parseability and recruiter-impact signals."
              className="rounded-2xl border border-ink-100 bg-white p-5 shadow-xs flex flex-col items-center justify-between text-center card-hover"
            >
              <div className="w-full flex items-center justify-between text-xs text-ink-500 mb-2">
                <span className="font-semibold text-ink-700">Readiness</span>
                <TrendingUp size={14} className="text-signal-600" />
              </div>
              <ScoreRing value={data.role_readiness_index} label="Role Readiness Index" size={84} strokeWidth={7} />
              <p className="text-[11px] text-ink-500 mt-2">Composite blend of ATS parseability & recruiter impact</p>
            </div>

            <div
              title="ATS compatibility evaluates resume structure, keyword density, and parseability."
              className="rounded-2xl border border-ink-100 bg-white p-5 shadow-xs flex flex-col items-center justify-between text-center card-hover"
            >
              <div className="w-full flex items-center justify-between text-xs text-ink-500 mb-2">
                <span className="font-semibold text-ink-700">Strict ATS Screening</span>
                <CheckCircle2 size={14} className="text-signal-600" />
              </div>
              <ScoreRing value={data.ats_compatibility} label="ATS Screening Compatibility" size={84} strokeWidth={7} />
              <p className="text-[11px] text-ink-500 mt-2">ATS format compatibility: section structure, keyword density, and parse-ability</p>
            </div>

            <div
              title="Skill coverage measures keyword alignment against live target job postings."
              className="rounded-2xl border border-ink-100 bg-white p-5 shadow-xs flex flex-col items-center justify-between text-center card-hover"
            >
              <div className="w-full flex items-center justify-between text-xs text-ink-500 mb-2">
                <span className="font-semibold text-ink-700">Skill Coverage</span>
                <Compass size={14} className="text-amber-500" />
              </div>
              <ScoreRing value={data.skill_coverage} label="Top Match Skill Coverage" size={84} strokeWidth={7} />
              <p className="text-[11px] text-ink-500 mt-2">Keyword alignment against live target job postings</p>
            </div>
          </div>

          {/* 4. Actionable Next Step Banner */}
          <div className="rounded-2xl border border-signal-500/20 bg-gradient-to-r from-signal-500/10 via-signal-500/5 to-white p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-xl bg-signal-500 text-white shrink-0 mt-0.5">
                <Sparkles size={16} />
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-signal-700">Recommended Next Step</p>
                <p className="text-sm font-semibold text-ink-900 mt-0.5">{data.recommended_next_action}</p>
              </div>
            </div>
            <Link
              to="/opportunities/jobs"
              className="inline-flex items-center gap-1 text-xs font-bold text-signal-700 hover:text-signal-800 bg-white border border-signal-500/30 hover:border-signal-500 px-3.5 py-2 rounded-xl shadow-2xs transition-all shrink-0"
            >
              Take Action <ArrowRight size={13} />
            </Link>
          </div>

          {/* 5. Top Live Matches & Applications Tracker Grid */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Top Matches Widget */}
            <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm transition-shadow hover:shadow-md sm:p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Briefcase size={16} className="text-signal-600" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-ink-700">Top Recommended Matches</h3>
                </div>
                <Link to="/opportunities/jobs" className="shrink-0 text-xs font-semibold text-signal-600 hover:underline">
                  View all <ArrowRight size={12} />
                </Link>
              </div>

              <div className="space-y-2.5">
                {data.top_matches.length === 0 && (
                  <div className="rounded-xl border border-dashed border-ink-200 bg-ink-50/60 px-4 py-6 text-center">
                    <p className="text-xs text-ink-500">Complete onboarding to see matched job listings.</p>
                  </div>
                )}
                {data.top_matches.slice(0, 4).map((m) => (
                  <div
                    key={m.job_id}
                    className="group grid grid-cols-1 gap-3 rounded-xl border border-ink-100 bg-ink-50/40 p-3.5 transition-all duration-200 hover:border-signal-500/40 hover:bg-white hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)] sm:p-4"
                  >
                    <Link
                      to={`/opportunities/job/${m.job_id}`}
                      className="flex min-w-0 flex-1 items-center gap-3"
                    >
                      <div
                        aria-hidden="true"
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-ink-100 bg-white text-signal-700 shadow-2xs transition-colors group-hover:border-signal-500/30 group-hover:bg-signal-500/5"
                      >
                        <Building2 size={18} strokeWidth={1.8} />
                      </div>
                      <div className="min-w-0">
                        <p className="line-clamp-2 text-xs font-bold leading-tight text-ink-900 group-hover:text-signal-700">{m.job_title}</p>
                        <p className="text-[11px] text-ink-500 mt-0.5 truncate">{m.company}</p>
                      </div>
                    </Link>
                    <div className="flex w-full shrink-0 items-center justify-end gap-2">
                      <span
                        title="Match score reflects skill coverage, role alignment, experience, location, compensation, and industry fit."
                        aria-label={`${m.overall_score}% match. Based on skills, role, experience, location, compensation, and industry fit.`}
                        className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-bold tabular-nums font-display whitespace-nowrap ${getMatchScoreStyle(m.overall_score)}`}
                      >
                        {m.overall_score}% match
                      </span>
                      <Link
                        to={`/resume/tailor/${m.job_id}`}
                        title={`Tailor resume for ${m.job_title} at ${m.company}`}
                        className="inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border border-ink-200 bg-white px-3 py-2 text-[11px] font-semibold text-ink-700 transition-all hover:border-ink-300 hover:bg-ink-50 hover:text-ink-900 active:scale-[0.98]"
                      >
                        <FileEdit size={11} />
                        <span>{data.top_matches[0]?.job_id === m.job_id ? "Tailor top match" : "Tailor"}</span>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Saved Opportunities Widget */}
            <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm transition-shadow hover:shadow-md sm:p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Bookmark size={16} className="text-amber-500" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-ink-700">
                    Saved Opportunities ({totalApplications})
                  </h3>
                </div>
                {totalApplications > 0 && (
                  <Link to="/applications?tab=SAVED" className="shrink-0 text-xs font-semibold text-signal-600 hover:underline">
                    View all <ArrowRight size={12} />
                  </Link>
                )}
              </div>

              {totalApplications === 0 ? (
                <div className="flex min-h-40 flex-col items-center justify-center rounded-xl border border-dashed border-ink-200 bg-ink-50/40 p-5 text-center">
                  <Bookmark size={19} className="mb-2 text-ink-400" />
                  <p className="max-w-xs text-xs leading-relaxed text-ink-500">
                    No saved opportunities yet. Bookmark target roles to access them quickly here.
                  </p>
                  <Link
                    to="/opportunities/jobs"
                    className="mt-4 inline-flex items-center justify-center gap-1.5 rounded-lg bg-signal-600 px-4 py-2.5 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-signal-700"
                  >
                    Explore opportunities
                    <ArrowRight size={13} />
                  </Link>
                </div>
              ) : (
                <div className="min-h-40 rounded-xl border border-ink-100 bg-ink-50/40 p-4">
                  <div className="space-y-2">
                    <p className="text-xs text-ink-600 font-medium">
                      You have <strong className="text-ink-950">{totalApplications}</strong> bookmarked {totalApplications === 1 ? "role" : "roles"} ready for tailored resume reviews and direct applications.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
