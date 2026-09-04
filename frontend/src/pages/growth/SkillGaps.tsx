import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Sparkles, Target, Map as MapIcon, ArrowRight, Info, ShieldAlert, Layers, Briefcase } from "lucide-react";
import { apiClient } from "../../lib/apiClient";
import { getProfile } from "../../lib/profile";
import { getSkillGaps, getRoadmap, type SkillGap } from "../../lib/learning";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";
import { RoleDropdownSelector } from "../../components/ui/RoleDropdownSelector";
import { ALL_JOB_ROLES } from "../../lib/roleConstants";

const MARKET_PRIORITY_STYLE: Record<SkillGap["priority"], { badge: string; label: string }> = {
  CORE: { badge: "bg-blue-600/10 text-blue-700 border border-blue-600/20", label: "Core Competency" },
  SECONDARY: { badge: "bg-amber-500/10 text-amber-700 border border-amber-500/20", label: "Common Competency" },
  BONUS: { badge: "bg-signal-500/10 text-signal-700 border border-signal-500/20", label: "Optional / Specialization" },
};

const PERSONALIZED_PRIORITY_STYLE: Record<SkillGap["priority"], { badge: string; label: string }> = {
  CORE: { badge: "bg-alert-600/10 text-alert-600 border border-alert-600/20", label: "Critical Missing Skill" },
  SECONDARY: { badge: "bg-amber-500/10 text-amber-700 border border-amber-500/20", label: "Partially Covered" },
  BONUS: { badge: "bg-signal-500/10 text-signal-700 border border-signal-500/20", label: "Bonus / Recommended" },
};

export function SkillGaps() {
  const [searchParams] = useSearchParams();
  const targetJobId = searchParams.get("jobId") || searchParams.get("targetJobId");

  const { data: targetJob } = useQuery({
    queryKey: ["job-detail", targetJobId],
    queryFn: () => apiClient.get(`/jobs/${targetJobId}`).then((r) => r.data),
    enabled: !!targetJobId,
  });

  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });

  const defaultRole = targetJob?.title || profile?.target_roles?.[0] || "Full Stack Developer";
  const [selectedRole, setSelectedRole] = useState<string>("");

  const activeRole = selectedRole || defaultRole;

  const { data: roadmap, isLoading: roadmapLoading } = useQuery({
    queryKey: ["roadmap-role", activeRole],
    queryFn: () => getRoadmap({ role: activeRole }),
    enabled: !!activeRole,
  });

  const { data: gaps, isLoading: gapsLoading, error } = useQuery({
    queryKey: ["skill-gaps-role", activeRole],
    queryFn: () => getSkillGaps({ role: activeRole }),
    enabled: !!activeRole,
  });

  const isLoading = gapsLoading || roadmapLoading;

  const isMarketBenchmark =
    roadmap?.roadmap_type === "MARKET" ||
    roadmap?.personalization_status === "NONE" ||
    (gaps && gaps.length > 0 && gaps[0].current_evidence === "MARKET_REQUIREMENT");

  const isLowConfidence =
    roadmap?.role_confidence === "LOW" ||
    (gaps && gaps.length > 0 && gaps[0].confidence === "LOW");

  const firstGap = gaps && gaps.length > 0 ? gaps[0] : null;

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Target size={24} className="text-signal-600" />
          <h1 className="font-display text-2xl text-ink-900">
            {isMarketBenchmark ? "Market Skill Benchmark" : "Personalized Skill Gap Analysis"}
          </h1>
        </div>
      </div>
      <p className="text-ink-500 mb-6 text-sm">
        {isMarketBenchmark
          ? `Skills commonly expected across the industry for ${activeRole}. Upload your resume to see your personalized gaps.`
          : `Direct comparison between your verified resume evidence and market requirements for ${activeRole}.`}
      </p>

      {/* P3-02 Target Opportunity Context Banner */}
      {targetJob && (
        <div className="rounded-xl border border-signal-500/20 bg-signal-50/60 p-4 mb-6 shadow-2xs">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-signal-500/10 text-signal-700 shrink-0 mt-0.5">
                <Briefcase size={18} />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-signal-700 block mb-0.5">
                  Target Opportunity Context
                </span>
                <h3 className="font-bold text-ink-950 text-sm">
                  {targetJob.title} at {targetJob.company}
                </h3>
                <p className="text-xs text-ink-600 mt-0.5">
                  Evaluating specific skill alignment and learning priorities required for this requisition.
                </p>
                {targetJob.skills_required && targetJob.skills_required.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1 mt-2">
                    <span className="text-[11px] font-semibold text-ink-700 mr-1">Requisition Skills:</span>
                    {targetJob.skills_required.slice(0, 8).map((s: string) => (
                      <span key={s} className="px-1.5 py-0.5 bg-white border border-ink-200 text-ink-800 rounded text-[10px]">
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <Link
              to={`/resume/tailor/${targetJob.id}`}
              className="shrink-0 px-3 py-1.5 rounded-lg bg-signal-600 hover:bg-signal-700 text-white text-xs font-semibold shadow-2xs self-start"
            >
              Tailor for this role
            </Link>
          </div>
        </div>
      )}

      {/* Target Role Selector Bar */}
      <div className="bg-white rounded-lg border border-ink-100 p-4 mb-6 shadow-xs">
        <RoleDropdownSelector
          label="Analyzing Gaps For Target Role:"
          selectedRole={activeRole}
          onRoleChange={setSelectedRole}
          roles={ALL_JOB_ROLES}
          includeAllOption={false}
          helperText="Select or specify any target role across software, data, engineering, design, healthcare, business, or education."
        />
      </div>

      {isLoading && <SkeletonCard count={3} />}

      {error && (
        <div className="rounded-xl bg-alert-600/10 border border-alert-600/20 p-4 text-xs text-alert-800 mb-4">
          <p>{(error as any)?.response?.data?.detail || "Unable to evaluate skill gaps for this role. Please retry."}</p>
        </div>
      )}

      {/* Mode A Notice Banner: When No Resume Exists */}
      {!isLoading && isMarketBenchmark && !isLowConfidence && (
        <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 mb-6 shadow-2xs flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-700 shrink-0 mt-0.5">
              <Info size={16} />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-500/10 text-blue-700 px-2 py-0.5 rounded-full border border-blue-500/20">
                  Market Skill Benchmark
                </span>
                {firstGap?.domain && (
                  <span className="text-[11px] text-ink-600 font-medium flex items-center gap-1">
                    <Layers size={11} className="text-ink-400" />
                    <span>Domain: {firstGap.domain}</span>
                    {firstGap.subdomain && <span className="text-ink-400">({firstGap.subdomain})</span>}
                  </span>
                )}
              </div>
              <p className="text-xs text-ink-700 mt-1.5 leading-relaxed">
                This is a market benchmark, not a personalized assessment. Upload your master resume to discover which competencies you already demonstrate and which are personal gaps.
              </p>
            </div>
          </div>
          <Link
            to="/resume/master"
            className="inline-flex items-center gap-1 text-xs font-semibold text-white bg-ink-950 hover:bg-ink-900 px-3 py-1.5 rounded-lg shrink-0 transition-colors shadow-2xs"
          >
            <span>Upload Resume</span>
            <ArrowRight size={12} />
          </Link>
        </div>
      )}

      {/* Low Confidence State: Arbitrary or Unknown Role */}
      {!isLoading && isLowConfidence && (!gaps || gaps.length === 0) && (
        <EmptyState
          icon={ShieldAlert}
          title="Limited market evidence for this role"
          description={
            roadmap?.message ||
            `We couldn't confidently determine role-specific skill requirements for "${activeRole}". Add a job description or choose a standard industry role for a more precise analysis.`
          }
          actionText="Explore Job Openings"
          actionHref="/opportunities/jobs"
          secondaryActionText="Browse Standard Roles"
          secondaryActionHref="/growth/roadmap"
        />
      )}

      {/* Zero Gaps Detected (When personalized & candidate covered all) */}
      {!isLoading && !isLowConfidence && gaps && gaps.length === 0 && (
        <EmptyState
          icon={Sparkles}
          title="Zero skill gaps detected!"
          description={`Your resume demonstrates comprehensive coverage of all market competencies required for ${activeRole}.`}
          actionText="Practice Interview Questions"
          actionHref="/growth/interview"
          secondaryActionText="Explore Job Openings"
          secondaryActionHref="/opportunities/jobs"
        />
      )}

      {/* Gaps List */}
      <div className="space-y-3">
        {gaps?.map((gap, i) => {
          const styleMap = isMarketBenchmark ? MARKET_PRIORITY_STYLE : PERSONALIZED_PRIORITY_STYLE;
          const style = styleMap[gap.priority] || styleMap.CORE;

          return (
            <div key={i} className="rounded-xl border border-ink-100 bg-white p-5 transition-shadow hover:shadow-xs">
              <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-semibold text-ink-900 text-base">{gap.skill}</h3>
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${style.badge}`}>
                    {style.label}
                  </span>
                  {gap.source && (
                    <span className="text-[10px] text-ink-400 bg-ink-50 border border-ink-100 px-2 py-0.5 rounded-md font-mono">
                      {gap.source === "ROLE_TAXONOMY_AND_MARKET"
                        ? "Taxonomy + Market Postings"
                        : gap.source === "ROLE_TAXONOMY"
                        ? "Role Taxonomy"
                        : gap.source === "JOB_REQUIREMENTS"
                        ? "Job Posting"
                        : gap.source}
                    </span>
                  )}
                </div>
                <span className="text-xs text-ink-400 font-mono">
                  Estimated study: ~{gap.estimated_days} days
                </span>
              </div>

              <p className="text-xs text-ink-600 mb-3 leading-relaxed">{gap.reason}</p>

              <div className="pt-3 border-t border-ink-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <span className="text-[11px] text-ink-400">
                  Ready to develop this competency with guided study resources?
                </span>
                <Link
                  to="/growth/roadmap"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-signal-500/10 hover:bg-signal-500/20 text-signal-700 text-xs font-bold transition-colors shrink-0"
                >
                  <MapIcon size={13} className="text-signal-600" />
                  <span>Follow in Learning Roadmap</span>
                  <ArrowRight size={12} />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
