import { useState, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Target,
  Map as MapIcon,
  ArrowRight,
  ShieldAlert,
  Layers,
  Briefcase,
  CheckCircle2,
  AlertCircle,
  MinusCircle,
  FileCheck,
  ChevronDown,
  ChevronUp,
  Sparkles,
  BookOpen,
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


function getEvidenceBadge(evidenceType?: string): { label: string; className: string } {
  switch ((evidenceType || "").toUpperCase()) {
    case "WORK_EXPERIENCE":
    case "EXPERIENCE":
      return {
        label: "Professional Experience",
        className: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
      };
    case "PROJECT":
      return {
        label: "Project Delivery",
        className: "bg-blue-500/10 text-blue-700 border-blue-500/20",
      };
    case "COURSEWORK":
    case "EDUCATION":
      return {
        label: "Coursework & Education",
        className: "bg-purple-500/10 text-purple-700 border-purple-500/20",
      };
    case "EXPLICIT_SKILL":
    case "EXPLICIT":
      return {
        label: "Explicit Skill Mention",
        className: "bg-teal-500/10 text-teal-700 border-teal-500/20",
      };
    case "RELATED_TECHNOLOGY":
    case "INFERRED":
      return {
        label: "Related Technology Cluster",
        className: "bg-amber-500/10 text-amber-700 border-amber-500/20",
      };
    default:
      return {
        label: evidenceType || "Resume Evidence",
        className: "bg-ink-100 text-ink-700 border-ink-200",
      };
  }
}

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


  // Mode B Tab state: "LEARN_FIRST" | "STRENGTHEN" | "LATER_SUPPORTING" | "DEMONSTRATED" | "ALL"
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  // Mode A Tab state: "ALL" | "CORE" | "IMPORTANT" | "SUPPORTING"
  const [importanceFilter, setImportanceFilter] = useState<string>("ALL");
  // Expandable details tracking
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});

  const toggleCard = (skillKey: string) => {
    setExpandedCards((prev) => ({
      ...prev,
      [skillKey]: !prev[skillKey],
    }));
  };

  // Helper to get normalized priority group
  const getEffectivePriorityGroup = (gap: SkillGap): string => {
    if (gap.priority_group) return gap.priority_group;
    if (gap.status === "DEMONSTRATED") return "DEMONSTRATED";
    if (gap.status === "PARTIALLY_DEMONSTRATED") return "STRENGTHEN";
    if (gap.importance === "CORE" || gap.priority === "CORE") return "LEARN_FIRST";
    if (gap.importance === "IMPORTANT" || gap.priority === "SECONDARY") return "STRENGTHEN";
    return "LATER_SUPPORTING";
  };

  // Filtered gaps
  const filteredGaps = useMemo(() => {
    if (!hasResume) {
      if (importanceFilter === "ALL") return gaps;
      return gaps.filter((g) => (g.importance || "CORE").toUpperCase() === importanceFilter);
    } else {
      if (priorityFilter === "ALL") return gaps;
      return gaps.filter((g) => getEffectivePriorityGroup(g) === priorityFilter);
    }
  }, [gaps, hasResume, importanceFilter, priorityFilter]);

  // Counts for Mode B
  const learnFirstCount = gaps.filter((g) => getEffectivePriorityGroup(g) === "LEARN_FIRST").length;
  const strengthenCount = gaps.filter((g) => getEffectivePriorityGroup(g) === "STRENGTHEN").length;
  const laterCount = gaps.filter((g) => getEffectivePriorityGroup(g) === "LATER_SUPPORTING").length;
  const demonstratedCount = gaps.filter((g) => g.status === "DEMONSTRATED").length;

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Target size={24} className="text-signal-600" />
          <h1 className="font-display text-2xl text-ink-900">
            {isMarketBenchmark ? "Career Skill Map" : "Canonical Career Skill Alignment"}
          </h1>
        </div>
      </div>
      <p className="text-ink-500 mb-6 text-sm">
        {isMarketBenchmark
          ? `Authoritative competency structure for ${activeRole}. Clearly categorized into Core, Important, and Supporting skills.`
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

      {/* Mode A Beginner-Friendly Summary Box: When No Resume Exists */}
      {!isLoading && isMarketBenchmark && !isLowConfidence && (
        <>
          {/* Beginner Guidance Callout */}
          <div className="rounded-xl border border-signal-500/20 bg-signal-50/60 p-4 mb-6 shadow-2xs">
            <div className="flex items-start gap-3">
              <div className="p-1.5 rounded-lg bg-signal-500/10 text-signal-700 shrink-0 mt-0.5">
                <Sparkles size={16} />
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-ink-950 text-sm">
                  What should I learn to enter {activeRole}?
                </h3>
                <p className="text-xs text-ink-600 mt-1 leading-relaxed">
                  Start with the <strong className="text-ink-900">{alignment?.summary?.core_count ?? 0} Core</strong> competencies first—these are foundational requirements expected in role interviews. Next, broaden into <strong className="text-ink-900">{alignment?.summary?.important_count ?? 0} Important</strong> domain workflows, and round out your preparation with <strong className="text-ink-900">{alignment?.summary?.supporting_count ?? 0} Supporting</strong> developer tools.
                </p>
              </div>
              <Link
                to="/resume/master"
                className="hidden sm:inline-flex items-center gap-1 text-xs font-semibold text-white bg-ink-950 hover:bg-ink-900 px-3 py-1.5 rounded-lg shrink-0 transition-colors shadow-2xs"
              >
                <span>Upload Resume</span>
                <ArrowRight size={12} />
              </Link>
            </div>
          </div>

          {/* Mode A Metrics Bar: Core vs Important vs Supporting */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <div className="bg-white p-3.5 rounded-xl border border-ink-100 shadow-2xs">
              <span className="text-[11px] font-medium text-ink-400 block">Total Competencies</span>
              <span className="text-xl font-bold text-ink-900 mt-0.5 block">
                {alignment?.summary?.total ?? gaps.length}
              </span>
            </div>
            <div className="bg-white p-3.5 rounded-xl border border-blue-500/20 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-medium text-blue-700">Core (Learn First)</span>
                <Target size={14} className="text-blue-600" />
              </div>
              <span className="text-xl font-bold text-blue-700 mt-0.5 block">
                {alignment?.summary?.core_count ?? gaps.filter((g) => g.importance === "CORE").length}
              </span>
            </div>
            <div className="bg-white p-3.5 rounded-xl border border-indigo-500/20 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-medium text-indigo-700">Important</span>
                <Layers size={14} className="text-indigo-600" />
              </div>
              <span className="text-xl font-bold text-indigo-700 mt-0.5 block">
                {alignment?.summary?.important_count ?? gaps.filter((g) => g.importance === "IMPORTANT" || g.importance === "COMMON").length}
              </span>
            </div>
            <div className="bg-white p-3.5 rounded-xl border border-teal-500/20 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-medium text-teal-700">Supporting Tools</span>
                <BookOpen size={14} className="text-teal-600" />
              </div>
              <span className="text-xl font-bold text-teal-700 mt-0.5 block">
                {alignment?.summary?.supporting_count ?? gaps.filter((g) => g.importance === "SUPPORTING" || g.importance === "OPTIONAL").length}
              </span>
            </div>
          </div>

          {/* Mode A Filter Tabs */}
          <div className="flex items-center gap-2 mb-5 overflow-x-auto pb-1">
            <button
              onClick={() => setImportanceFilter("ALL")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                importanceFilter === "ALL"
                  ? "bg-ink-900 text-white shadow-2xs"
                  : "bg-white text-ink-600 hover:bg-ink-50 border border-ink-200"
              }`}
            >
              All Requirements ({gaps.length})
            </button>
            <button
              onClick={() => setImportanceFilter("CORE")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                importanceFilter === "CORE"
                  ? "bg-blue-600 text-white shadow-2xs"
                  : "bg-white text-blue-700 hover:bg-blue-50 border border-blue-200"
              }`}
            >
              Core Foundations ({alignment?.summary?.core_count ?? 0})
            </button>
            <button
              onClick={() => setImportanceFilter("IMPORTANT")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                importanceFilter === "IMPORTANT"
                  ? "bg-indigo-600 text-white shadow-2xs"
                  : "bg-white text-indigo-700 hover:bg-indigo-50 border border-indigo-200"
              }`}
            >
              Important ({alignment?.summary?.important_count ?? 0})
            </button>
            <button
              onClick={() => setImportanceFilter("SUPPORTING")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                importanceFilter === "SUPPORTING"
                  ? "bg-teal-600 text-white shadow-2xs"
                  : "bg-white text-teal-700 hover:bg-teal-50 border border-teal-200"
              }`}
            >
              Supporting Tools ({alignment?.summary?.supporting_count ?? 0})
            </button>
          </div>
        </>
      )}

      {/* Mode B Metrics Bar: When Resume Exists */}
      {!isLoading && !isMarketBenchmark && alignment?.summary && (
        <>
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

          {/* Mode B Prioritized Action Tabs */}
          <div className="flex items-center gap-2 mb-5 overflow-x-auto pb-1">
            <button
              onClick={() => setPriorityFilter("ALL")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                priorityFilter === "ALL"
                  ? "bg-ink-900 text-white shadow-2xs"
                  : "bg-white text-ink-600 hover:bg-ink-50 border border-ink-200"
              }`}
            >
              All Gaps ({gaps.length})
            </button>
            <button
              onClick={() => setPriorityFilter("LEARN_FIRST")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                priorityFilter === "LEARN_FIRST"
                  ? "bg-alert-700 text-white shadow-2xs"
                  : "bg-white text-alert-700 hover:bg-alert-50 border border-alert-200"
              }`}
            >
              Learn First ({learnFirstCount})
            </button>
            <button
              onClick={() => setPriorityFilter("STRENGTHEN")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                priorityFilter === "STRENGTHEN"
                  ? "bg-amber-600 text-white shadow-2xs"
                  : "bg-white text-amber-700 hover:bg-amber-50 border border-amber-200"
              }`}
            >
              Strengthen ({strengthenCount})
            </button>
            <button
              onClick={() => setPriorityFilter("LATER_SUPPORTING")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                priorityFilter === "LATER_SUPPORTING"
                  ? "bg-teal-600 text-white shadow-2xs"
                  : "bg-white text-teal-700 hover:bg-teal-50 border border-teal-200"
              }`}
            >
              Later / Supporting ({laterCount})
            </button>
            <button
              onClick={() => setPriorityFilter("DEMONSTRATED")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                priorityFilter === "DEMONSTRATED"
                  ? "bg-emerald-600 text-white shadow-2xs"
                  : "bg-white text-emerald-700 hover:bg-emerald-50 border border-emerald-200"
              }`}
            >
              Demonstrated ({demonstratedCount})
            </button>
          </div>
        </>
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

      {/* Competency Card List with Progressive Disclosure */}
      <div className="space-y-3">
        {filteredGaps.map((gap: SkillGap, i: number) => {
          const status = gap.status || "NO_RESUME_EVIDENCE";
          const isDemonstrated = status === "DEMONSTRATED";
          const isPartial = status === "PARTIALLY_DEMONSTRATED";
          const isNoEvidence = status === "NO_RESUME_EVIDENCE";
          const priorityGroup = getEffectivePriorityGroup(gap);
          const isExpanded = !!expandedCards[gap.skill];

          const tierMeta = TIER_METADATA[(gap.tier as CompetencyTier) || "CORE"] || {
            label: gap.tier || "Core",
            badge: "bg-ink-100 text-ink-700 border-ink-200",
          };

          return (
            <div
              key={`${gap.skill}-${i}`}
              className={`rounded-xl border transition-shadow hover:shadow-xs p-4.5 ${
                isDemonstrated
                  ? "border-emerald-500/20 bg-emerald-500/[0.02]"
                  : isPartial
                  ? "border-amber-500/20 bg-amber-500/[0.02]"
                  : priorityGroup === "LEARN_FIRST"
                  ? "border-signal-500/30 bg-signal-500/[0.01]"
                  : "border-ink-100 bg-white"
              }`}
            >
              <div className="flex items-start justify-between mb-2 flex-wrap gap-2">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-ink-900 text-sm">{gap.skill}</h3>

                    {/* Mode B: Canonical Status Badge */}
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
                    ) : null}

                    {/* Mode A & B Priority Group Badge */}
                    {hasResume && !isDemonstrated && (
                      <span
                        className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                          priorityGroup === "LEARN_FIRST"
                            ? "bg-alert-600/10 text-alert-700 border-alert-600/20"
                            : priorityGroup === "STRENGTHEN"
                            ? "bg-amber-500/10 text-amber-700 border-amber-500/20"
                            : "bg-teal-500/10 text-teal-700 border-teal-500/20"
                        }`}
                      >
                        {priorityGroup === "LEARN_FIRST"
                          ? "Learn First"
                          : priorityGroup === "STRENGTHEN"
                          ? "Strengthen"
                          : "Later / Supporting"}
                      </span>
                    )}

                    {/* Importance Level */}
                    {gap.importance && (
                      <span
                        className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded border ${
                          gap.importance === "CORE"
                            ? "bg-blue-500/10 text-blue-700 border-blue-500/20 font-semibold"
                            : gap.importance === "IMPORTANT" || gap.importance === "COMMON"
                            ? "bg-indigo-500/10 text-indigo-700 border-indigo-500/20"
                            : "bg-ink-50 text-ink-500 border-ink-100"
                        }`}
                      >
                        {gap.importance}
                      </span>
                    )}

                    {/* Tier Badge */}
                    {gap.tier && (
                      <span
                        className={`text-[10px] uppercase font-mono px-1.5 py-0.5 rounded border ${tierMeta.badge}`}
                      >
                        {tierMeta.label}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[11px] text-ink-400 font-mono">
                    Estimated study: ~{gap.estimated_days} days
                  </span>
                  <button
                    onClick={() => toggleCard(gap.skill)}
                    className="p-1 rounded text-ink-400 hover:text-ink-700 hover:bg-ink-50 transition-colors"
                    aria-label="Toggle details"
                  >
                    {isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                  </button>
                </div>
              </div>

              {/* Concise summary reason */}
              <p className="text-xs text-ink-600 mb-2 leading-relaxed">
                {gap.explanation || gap.reason}
              </p>

              {/* Evidence Provenance Section (When Resume Exists & Evidence Found) */}
              {hasResume && gap.evidence && gap.evidence.length > 0 && (
                <div className="mt-2 mb-2 p-2.5 rounded-lg bg-ink-50/70 border border-ink-100 text-[11px] space-y-1">
                  <div className="flex items-center gap-1.5 text-ink-700 font-medium flex-wrap">
                    <FileCheck size={12} className="text-signal-600 shrink-0" />
                    <span>Evidence Source: {gap.evidence[0].entity_name || gap.evidence[0].section}</span>
                    {gap.evidence[0].evidence_type && (
                      <span
                        className={`text-[9.5px] px-1.5 py-0.2 rounded border font-sans font-semibold ${
                          getEvidenceBadge(gap.evidence[0].evidence_type).className
                        }`}
                      >
                        {getEvidenceBadge(gap.evidence[0].evidence_type).label}
                      </span>
                    )}
                  </div>
                  {gap.evidence[0].text && (
                    <p className="text-ink-600 italic text-[10.5px] line-clamp-2">
                      "{gap.evidence[0].text}"
                    </p>
                  )}
                </div>
              )}

              {/* Progressive Disclosure Section (Expanded) */}
              {isExpanded && (
                <div className="mt-3 pt-3 border-t border-ink-100 space-y-2 text-xs">
                  {gap.project_suggestion && (
                    <div className="p-2.5 rounded-lg bg-signal-50/50 border border-signal-500/10">
                      <span className="font-semibold text-ink-900 block mb-0.5">
                        💡 Hands-on Practice Suggestion:
                      </span>
                      <p className="text-ink-600 leading-snug">{gap.project_suggestion}</p>
                    </div>
                  )}
                  {isNoEvidence && (
                    <p className="text-[11px] text-ink-400 italic">
                      Tip: If you have experience with {gap.skill}, ensure it is explicitly listed in your work history or project highlights.
                    </p>
                  )}
                </div>
              )}

              {/* Action Footer */}
              {!isDemonstrated && (
                <div className="pt-2.5 mt-2 border-t border-ink-100/70 flex items-center justify-between gap-2">
                  <span className="text-[11px] text-ink-400">
                    Step-by-step roadmap available in learning progression
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
  );
}
