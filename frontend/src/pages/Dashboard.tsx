import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Sparkles, Briefcase, Kanban, ArrowRight, FileText,
  ShieldCheck, Map, MessageCircleQuestion,
} from "lucide-react";
import { getDashboard } from "../lib/dashboard";
import { useAuth } from "../context/AuthContext";
import { ScoreRing } from "../components/ui/ScoreRing";

function CareerLoopHub() {
  const stages = [
    { label: "Master Resume", desc: "Intelligence & Score", to: "/resume/master", icon: FileText },
    { label: "Live Matches", desc: "Target Job Search", to: "/opportunities/jobs", icon: Briefcase },
    { label: "Truth Guard Tailor", desc: "Evidence-Backed Export", to: "/resume/versions", icon: ShieldCheck },
    { label: "Application CRM", desc: "Pipeline Tracker", to: "/applications/tracker", icon: Kanban },
    { label: "Skill Roadmap", desc: "Bridging Missing Gaps", to: "/growth/roadmap", icon: Map },
    { label: "Interview Prep", desc: "Targeted Simulation", to: "/growth/interview", icon: MessageCircleQuestion },
  ];

  return (
    <div className="rounded-xl border border-ink-100 bg-white p-5 mb-6 shadow-xs">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-bold uppercase tracking-wider text-ink-500 flex items-center gap-1.5">
          <Sparkles size={14} className="text-signal-600" /> Connected Career Loop
        </p>
        <span className="text-[10px] font-semibold text-signal-700 bg-signal-500/10 px-2 py-0.5 rounded-full">
          All-in-One Engine
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
        {stages.map((st, idx) => {
          const Icon = st.icon;
          return (
            <Link
              key={st.to}
              to={st.to}
              className="group p-2.5 rounded-lg border border-ink-100 bg-ink-50/40 hover:bg-white hover:border-signal-500 hover:shadow-xs transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-bold text-ink-400 group-hover:text-signal-600">0{idx + 1}</span>
                  <Icon size={14} className="text-ink-400 group-hover:text-signal-600 transition-colors" />
                </div>
                <p className="text-xs font-bold text-ink-900 group-hover:text-signal-700 leading-tight">{st.label}</p>
                <p className="text-[10px] text-ink-500 mt-0.5 leading-tight">{st.desc}</p>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="max-w-4xl space-y-6">
      <div className="rr-skeleton h-8 w-64 rounded-md" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[0, 1, 2].map((i) => <div key={i} className="rr-skeleton h-32 rounded-lg" />)}
      </div>
      <div className="rr-skeleton h-20 rounded-lg" />
    </div>
  );
}

export function Dashboard() {
  const { user } = useAuth();
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });

  if (isLoading) return <DashboardSkeleton />;
  if (!data) return null;

  const totalApplications = Object.values(data.application_counts).reduce((a, b) => a + b, 0);

  return (
    <div className="max-w-4xl">
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-ink-950 via-ink-900 to-ink-950 px-5 py-6 sm:px-6 sm:py-7 mb-6">
        <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full bg-signal-500/20 blur-3xl" />
        <div className="absolute right-20 bottom-0 w-24 h-24 rounded-full bg-signal-400/10 blur-2xl" />
        <div className="relative">
          <h1 className="font-display text-xl sm:text-2xl text-white mb-1">
            Welcome back{user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}
          </h1>
          <p className="text-ink-300 text-xs sm:text-sm">Here's where you stand right now.</p>
        </div>
      </div>

      <CareerLoopHub />

      {!data.resume_uploaded ? (
        <div className="rounded-lg border border-signal-500/30 bg-signal-500/5 p-5 sm:p-6 mb-6">
          <p className="text-ink-900 font-medium mb-2">Get started</p>
          <p className="text-sm text-ink-500 mb-4">{data.recommended_next_action}</p>
          <Link to="/resume/master" className="inline-flex items-center gap-1 rounded-md bg-signal-500 hover:bg-signal-600 text-white px-4 py-2 text-sm font-medium transition-transform active:scale-95">
            Upload your resume <ArrowRight size={14} />
          </Link>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
            <div className="rounded-lg border border-ink-100 bg-white p-5 flex flex-col items-center transition-shadow hover:shadow-md">
              <ScoreRing value={data.role_readiness_index} label="Role Readiness Index" />
            </div>
            <div className="rounded-lg border border-ink-100 bg-white p-5 flex flex-col items-center transition-shadow hover:shadow-md">
              <ScoreRing value={data.ats_compatibility} label="ATS Compatibility" />
            </div>
            <div className="rounded-lg border border-ink-100 bg-white p-5 flex flex-col items-center transition-shadow hover:shadow-md">
              <ScoreRing value={data.skill_coverage} label="Top Match Skill Coverage" />
            </div>
          </div>

          <div className="rounded-lg border border-signal-500/20 bg-gradient-to-r from-signal-500/5 to-transparent p-4 sm:p-5 mb-6">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles size={14} className="text-signal-600" />
              <p className="text-xs font-medium uppercase tracking-wider text-signal-600">Recommended next action</p>
            </div>
            <p className="text-sm text-ink-900">{data.recommended_next_action}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Briefcase size={14} className="text-ink-500" />
                <p className="text-xs font-medium uppercase tracking-wider text-ink-500">Top Matches</p>
              </div>
              <div className="space-y-2">
                {data.top_matches.length === 0 && <p className="text-sm text-ink-500">Complete onboarding to see matches.</p>}
                {data.top_matches.map((m) => (
                  <Link
                    key={m.job_id}
                    to={`/opportunities/job/${m.job_id}`}
                    className="block rounded-lg border border-ink-100 bg-white p-3 hover:border-signal-500 hover:shadow-md transition-all duration-200"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-ink-900">{m.job_title}</p>
                        <p className="text-xs text-ink-500">{m.company}</p>
                      </div>
                      <span className="text-sm font-display text-ink-900">{m.overall_score}%</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Kanban size={14} className="text-ink-500" />
                <p className="text-xs font-medium uppercase tracking-wider text-ink-500">
                  Applications ({totalApplications})
                </p>
              </div>
              <div className="rounded-lg border border-ink-100 bg-white p-4 space-y-1.5">
                {totalApplications === 0 && <p className="text-sm text-ink-500">No applications yet.</p>}
                {Object.entries(data.application_counts).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between text-sm">
                    <span className="text-ink-500">{status}</span>
                    <span className="text-ink-900 font-medium">{count}</span>
                  </div>
                ))}
              </div>
              <Link to="/applications/tracker" className="inline-flex items-center gap-1 mt-2 text-xs text-signal-600 hover:underline">
                View tracker <ArrowRight size={11} />
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
