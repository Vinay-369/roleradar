import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Target,
  Map as MapIcon,
  ArrowRight,
  Info,
  ShieldAlert,
  Layers,
  Briefcase,
  CheckCircle2,
  AlertCircle,
  MinusCircle,
  FileCheck,
} from "lucide-react";
import { apiClient } from "../../lib/apiClient";
import { getProfile } from "../../lib/profile";
import {
  getCareerAlignment,
  getCanonicalRoles,
  getRoadmap,
  type SkillGap,
  type CompetencyTier,
} from "../../lib/learning";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";
import { RoleDropdownSelector } from "../../components/ui/RoleDropdownSelector";
import { ALL_JOB_ROLES } from "../../lib/roleConstants";

const TIER_METADATA: Record<
  CompetencyTier,
  { label: string; description: string; badge: string }
> = {
  FOUNDATION: {
    label: "Foundation",
    description: "Fundamental languages, systems, and core CS prerequisites",
    badge: "bg-purple-500/10 text-purple-700 border-purple-500/20",
  },
  CORE: {
    label: "Core Competencies",
    description: "Essential role architectures and primary delivery competencies",
    badge: "bg-blue-600/10 text-blue-700 border-blue-600/20",
  },
  DOMAIN_PROCESSING: {
    label: "Domain & Processing",
    description: "Domain methodologies, processing patterns, and data flows",
    badge: "bg-indigo-500/10 text-indigo-700 border-indigo-500/20",
  },
  TOOLS: {
    label: "Tools & Technologies",
    description: "Concrete frameworks, libraries, and developer tools",
    badge: "bg-teal-500/10 text-teal-700 border-teal-500/20",
  },
  CLOUD_SPECIALIZATION: {
    label: "Cloud & Specialization",
    description: "Cloud platforms, infrastructure, and advanced specialization",
    badge: "bg-sky-500/10 text-sky-700 border-sky-500/20",
  },
  ADVANCED: {
    label: "Advanced & Electives",
    description: "High-impact optional competencies that strengthen candidacy",
    badge: "bg-amber-500/10 text-amber-700 border-amber-500/20",
  },
};

const TIER_ORDER: CompetencyTier[] = [
  "FOUNDATION",
  "CORE",
  "DOMAIN_PROCESSING",
  "TOOLS",
  "CLOUD_SPECIALIZATION",
  "ADVANCED",
];

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

  const { data: canonicalRoles } = useQuery({
    queryKey: ["canonical-roles"],
    queryFn: getCanonicalRoles,
  });

  const roleOptions =
    canonicalRoles && canonicalRoles.length > 0
      ? canonicalRoles.map((r) => r.role)
      : ALL_JOB_ROLES;

  const { data: roadmap, isLoading: roadmapLoading } = useQuery({
    queryKey: ["roadmap-role", activeRole],
    queryFn: () => getRoadmap({ role: activeRole }),
    enabled: !!activeRole,
  });

  const { data: alignment, isLoading: gapsLoading, error } = useQuery({
    queryKey: ["career-alignment-role", activeRole, targetJobId],
    queryFn: () =>
      getCareerAlignment(targetJobId ? { jobId: targetJobId } : { role: activeRole }),
    enabled: !!activeRole,
  });

  const isLoading = gapsLoading || roadmapLoading;
  const gaps = alignment?.competencies || [];
  const hasResume = alignment?.has_resume ?? false;

  const isMarketBenchmark =
    !hasResume ||
    roadmap?.roadmap_type === "MARKET" ||
    roadmap?.personalization_status === "NONE" ||
    (gaps.length > 0 && gaps[0].current_evidence === "MARKET_REQUIREMENT");

  const isLowConfidence =
    roadmap?.role_confidence === "LOW" ||
    (alignment && alignment.confidence === "LOW");

  const firstGap = gaps.length > 0 ? gaps[0] : null;

  // Group competencies by Tier preserving TIER_ORDER
  const groupedByTier = TIER_ORDER.map((tierKey) => {
    const items = gaps.filter(
      (g) => (g.tier || "CORE").toUpperCase() === tierKey.toUpperCase()
    );
    return {
      tierKey,
      meta: TIER_METADATA[tierKey] || {
        label: tierKey,
        description: "",
        badge: "bg-ink-100 text-ink-700",
      },
      items,
    };
  }).filter((group) => group.items.length > 0);

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Target size={24} className="text-signal-600" />
          <h1 className="font-display text-2xl text-ink-900">
            {isMarketBenchmark ? "Career Competency Map" : "Canonical Career Skill Alignment"}
          </h1>
        </div>
      </div>
      <p className="text-ink-500 mb-6 text-sm">
        {isMarketBenchmark
          ? `Canonical role competency structure for ${activeRole}. Upload your resume to evaluate demonstrated evidence against this structure.`
          : `Verified alignment between your resume evidence and canonical competencies for ${activeRole}.`}
      </p>

      {/* Target Opportunity Context Banner */}
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
                      <span
                        key={s}
                        className="px-1.5 py-0.5 bg-white border border-ink-200 text-ink-800 rounded text-[10px]"
                      >
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
          label="Analyzing Career Role:"
          selectedRole={activeRole}
          onRoleChange={setSelectedRole}
          roles={roleOptions}
          includeAllOption={false}
          helperText="Select any canonical career role from RoleRadar's authoritative competency taxonomy."
        />
      </div>

      {isLoading && <SkeletonCard count={3} />}

      {error && (
        <div className="rounded-xl bg-alert-600/10 border border-alert-600/20 p-4 text-xs text-alert-800 mb-4">
          <p>
            {(error as any)?.response?.data?.detail ||
              "Unable to evaluate career competencies for this role. Please retry."}
          </p>
        </div>
      )}

      {/* Summary Metrics Bar */}
      {!isLoading && alignment?.summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-white p-3.5 rounded-xl border border-ink-100 shadow-2xs">
            <span className="text-[11px] font-medium text-ink-400 block">Total Competencies</span>
            <span className="text-xl font-bold text-ink-900 mt-0.5 block">
              {alignment.summary.total}
            </span>
          </div>
          <div className="bg-white p-3.5 rounded-xl border border-emerald-500/20 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium text-emerald-700">Demonstrated</span>
              <CheckCircle2 size={14} className="text-emerald-600" />
            </div>
            <span className="text-xl font-bold text-emerald-700 mt-0.5 block">
              {alignment.summary.demonstrated}
            </span>
          </div>
          <div className="bg-white p-3.5 rounded-xl border border-amber-500/20 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium text-amber-700">Partially Demonstrated</span>
              <AlertCircle size={14} className="text-amber-600" />
            </div>
            <span className="text-xl font-bold text-amber-700 mt-0.5 block">
              {alignment.summary.partially_demonstrated}
            </span>
          </div>
          <div className="bg-white p-3.5 rounded-xl border border-ink-200 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium text-ink-500">No Resume Evidence</span>
              <MinusCircle size={14} className="text-ink-400" />
            </div>
            <span className="text-xl font-bold text-ink-700 mt-0.5 block">
              {alignment.summary.no_resume_evidence}
            </span>
          </div>
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
                  Market Benchmark View
                </span>
                {firstGap?.domain && (
                  <span className="text-[11px] text-ink-600 font-medium flex items-center gap-1">
                    <Layers size={11} className="text-ink-400" />
                    <span>Domain: {firstGap.domain}</span>
                    {firstGap.subdomain && (
                      <span className="text-ink-400">({firstGap.subdomain})</span>
                    )}
                  </span>
                )}
              </div>
              <p className="text-xs text-ink-700 mt-1.5 leading-relaxed">
                Viewing canonical competencies for {activeRole}. Upload your master resume to see what skills you currently demonstrate and what evidence is missing.
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
      {!isLoading && isLowConfidence && gaps.length === 0 && (
        <EmptyState
          icon={ShieldAlert}
          title="Limited evidence for this role"
          description={
            alignment?.message ||
            roadmap?.message ||
            `We couldn't confidently determine role-specific skill requirements for "${activeRole}". Select a canonical role from the taxonomy for full analysis.`
          }
          actionText="Explore Job Openings"
          actionHref="/opportunities/jobs"
          secondaryActionText="Browse Standard Roles"
          secondaryActionHref="/growth/roadmap"
        />
      )}

      {/* Structured Competency Groups by Tier */}
      <div className="space-y-8">
        {groupedByTier.map((group) => (
          <div key={group.tierKey} className="space-y-3">
            <div className="flex items-center justify-between pb-1 border-b border-ink-100">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 text-[11px] font-bold rounded-md uppercase tracking-wider ${group.meta.badge}`}>
                  {group.meta.label}
                </span>
                <span className="text-xs text-ink-400">({group.items.length})</span>
              </div>
              <span className="text-[11px] text-ink-400 hidden sm:inline">{group.meta.description}</span>
            </div>

            <div className="space-y-3">
              {group.items.map((gap: SkillGap, i: number) => {
                const status = gap.status || "NO_RESUME_EVIDENCE";
                const isDemonstrated = status === "DEMONSTRATED";
                const isPartial = status === "PARTIALLY_DEMONSTRATED";

                return (
                  <div
                    key={`${gap.skill}-${i}`}
                    className={`rounded-xl border p-4.5 transition-shadow hover:shadow-xs ${
                      isDemonstrated
                        ? "border-emerald-500/20 bg-emerald-500/[0.02]"
                        : isPartial
                        ? "border-amber-500/20 bg-amber-500/[0.02]"
                        : "border-ink-100 bg-white"
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2 flex-wrap gap-2">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-semibold text-ink-900 text-sm">{gap.skill}</h3>

                          {/* Canonical Status Badge */}
                          {hasResume ? (
                            isDemonstrated ? (
                              <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-semibold bg-emerald-500/10 text-emerald-700 border border-emerald-500/20">
                                <CheckCircle2 size={11} />
                                <span>Demonstrated</span>
                              </span>
                            ) : isPartial ? (
                              <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-semibold bg-amber-500/10 text-amber-700 border border-amber-500/20">
                                <AlertCircle size={11} />
                                <span>Partially Demonstrated</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-medium bg-ink-100 text-ink-600 border border-ink-200">
                                <MinusCircle size={11} />
                                <span>No Resume Evidence</span>
                              </span>
                            )
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium bg-blue-500/10 text-blue-700 border border-blue-500/20">
                              Standard Requirement
                            </span>
                          )}

                          {/* Importance Badge */}
                          {gap.importance && (
                            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-ink-50 text-ink-500 border border-ink-100">
                              {gap.importance}
                            </span>
                          )}
                        </div>
                      </div>

                      <span className="text-[11px] text-ink-400 font-mono">
                        Estimated study: ~{gap.estimated_days} days
                      </span>
                    </div>

                    <p className="text-xs text-ink-600 mb-2 leading-relaxed">
                      {gap.explanation || gap.reason}
                    </p>

                    {/* Evidence Provenance Section */}
                    {hasResume && gap.evidence && gap.evidence.length > 0 && (
                      <div className="mt-2 mb-2 p-2.5 rounded-lg bg-ink-50/70 border border-ink-100 text-[11px] space-y-1">
                        <div className="flex items-center gap-1.5 text-ink-700 font-medium">
                          <FileCheck size={12} className="text-signal-600 shrink-0" />
                          <span>
                            Evidence: {gap.evidence[0].entity_name || gap.evidence[0].section}
                          </span>
                          <span className="text-[10px] text-ink-400 font-mono">
                            ({gap.evidence[0].evidence_type})
                          </span>
                        </div>
                        {gap.evidence[0].text && (
                          <p className="text-ink-600 italic text-[10.5px] line-clamp-2">
                            "{gap.evidence[0].text}"
                          </p>
                        )}
                      </div>
                    )}

                    {/* Action Footer */}
                    {status !== "DEMONSTRATED" && (
                      <div className="pt-2.5 border-t border-ink-100/70 flex items-center justify-between gap-2">
                        <span className="text-[11px] text-ink-400">
                          Add this competency to your study roadmap?
                        </span>
                        <Link
                          to="/growth/roadmap"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-signal-500/10 hover:bg-signal-500/20 text-signal-700 text-[11px] font-semibold transition-colors shrink-0"
                        >
                          <MapIcon size={11} className="text-signal-600" />
                          <span>View in Roadmap</span>
                          <ArrowRight size={10} />
                        </Link>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
