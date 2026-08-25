import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Sparkles, Target, Map as MapIcon, ArrowRight } from "lucide-react";
import { getProfile } from "../../lib/profile";
import { getSkillGaps, type SkillGap } from "../../lib/learning";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";
import { RoleDropdownSelector } from "../../components/ui/RoleDropdownSelector";
import { ALL_JOB_ROLES } from "../../lib/roleConstants";

const PRIORITY_STYLE: Record<SkillGap["priority"], { badge: string; label: string }> = {
  CORE: { badge: "bg-alert-600/10 text-alert-600 border border-alert-600/20", label: "Critical Missing Skill" },
  SECONDARY: { badge: "bg-amber-500/10 text-amber-700 border border-amber-500/20", label: "Partially Covered" },
  BONUS: { badge: "bg-signal-500/10 text-signal-700 border border-signal-500/20", label: "Bonus / Recommended" },
};

export function SkillGaps() {
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });

  const defaultRole = profile?.target_roles?.[0] || "Full Stack Developer";
  const [selectedRole, setSelectedRole] = useState<string>("");

  const activeRole = selectedRole || defaultRole;

  const { data: gaps, isLoading, error } = useQuery({
    queryKey: ["skill-gaps-role", activeRole],
    queryFn: () => getSkillGaps({ role: activeRole }),
    enabled: !!activeRole,
  });

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Target size={24} className="text-signal-600" />
          <h1 className="font-display text-2xl text-ink-900">Skill Gap Analysis</h1>
        </div>
      </div>
      <p className="text-ink-500 mb-6 text-sm">
        Aggregated market expectations synthesized across real-world requirements for your target role, compared directly with your master resume.
      </p>

      {/* Target Role Selector Bar */}
      <div className="bg-white rounded-lg border border-ink-100 p-4 mb-6 shadow-xs">
        <RoleDropdownSelector
          label="Analyzing Gaps For Target Role:"
          selectedRole={activeRole}
          onRoleChange={setSelectedRole}
          roles={ALL_JOB_ROLES}
          includeAllOption={false}
          helperText="Select or specify any target role to evaluate market competencies and missing skill priorities."
        />
      </div>

      {isLoading && <SkeletonCard count={3} />}

      {error && (
        <div className="rounded-xl bg-alert-600/10 border border-alert-600/20 p-4 text-xs text-alert-800 mb-4">
          <p>{(error as any)?.response?.data?.detail || "Unable to evaluate skill gaps for this role. Please retry."}</p>
        </div>
      )}

      {gaps && gaps.length === 0 && (
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

      <div className="space-y-3">
        {gaps?.map((gap, i) => {
          const style = PRIORITY_STYLE[gap.priority] || PRIORITY_STYLE.CORE;
          return (
            <div key={i} className="rounded-xl border border-ink-100 bg-white p-5 transition-shadow hover:shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-ink-900 text-base">{gap.skill}</h3>
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${style.badge}`}>
                    {style.label}
                  </span>
                </div>
                <span className="text-xs text-ink-400 font-mono">
                  ~{gap.estimated_days} days to learn
                </span>
              </div>

              <p className="text-xs text-ink-600 mb-3 leading-relaxed">{gap.reason}</p>

              <div className="pt-3 border-t border-ink-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <span className="text-[11px] text-ink-400">
                  Ready to master this skill with guided projects and resources?
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
