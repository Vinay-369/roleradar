import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sparkles, Target, BookOpen } from "lucide-react";
import { getProfile } from "../../lib/profile";
import { getSkillGaps, type SkillGap } from "../../lib/learning";

const PRIORITY_STYLE: Record<SkillGap["priority"], { badge: string; label: string }> = {
  CORE: { badge: "bg-alert-600/10 text-alert-600 border border-alert-600/20", label: "Critical Missing Skill" },
  SECONDARY: { badge: "bg-amber-500/10 text-amber-700 border border-amber-500/20", label: "Partially Covered" },
  BONUS: { badge: "bg-signal-500/10 text-signal-700 border border-signal-500/20", label: "Bonus / Recommended" },
};

export function SkillGaps() {
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const targetRoles = profile?.target_roles && profile.target_roles.length > 0
    ? profile.target_roles
    : ["Full Stack Developer", "Backend Developer", "Frontend Developer", "Data Analyst", "Machine Learning Engineer"];

  const [selectedRole, setSelectedRole] = useState<string>("");
  const [customRoleInput, setCustomRoleInput] = useState<string>("");

  const activeRole = selectedRole || customRoleInput || targetRoles[0];

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
        <p className="text-xs font-medium uppercase tracking-wider text-ink-500 mb-3">
          Analyzing Gaps For Target Role:
        </p>
        <div className="flex flex-wrap gap-2 items-center mb-3">
          {targetRoles.map((role) => {
            const isSelected = activeRole.toLowerCase() === role.toLowerCase();
            return (
              <button
                key={role}
                onClick={() => {
                  setSelectedRole(role);
                  setCustomRoleInput("");
                }}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  isSelected
                    ? "bg-ink-950 text-white shadow-xs"
                    : "bg-ink-50 text-ink-700 hover:bg-ink-100"
                }`}
              >
                {role}
              </button>
            );
          })}
        </div>

        <div className="flex gap-2">
          <input
            value={customRoleInput}
            onChange={(e) => {
              setCustomRoleInput(e.target.value);
              setSelectedRole("");
            }}
            placeholder="Or type any other custom target role (e.g. Cloud Architect, DevOps Engineer)…"
            className="flex-1 rounded-md border border-ink-100 px-3 py-2 text-xs outline-none focus:border-signal-500"
          />
        </div>
      </div>

      {isLoading && <p className="text-ink-500">Evaluating resume against {activeRole} requirements…</p>}

      {error && (
        <div className="rounded-lg bg-alert-600/10 border border-alert-600/20 p-4 text-sm text-alert-700 mb-4">
          <p>{(error as any)?.response?.data?.detail || "Unable to evaluate skill gaps for this role. Please retry."}</p>
        </div>
      )}

      {gaps && gaps.length === 0 && (
        <div className="rounded-lg border border-signal-500/20 bg-signal-500/5 p-6 text-center">
          <Sparkles className="mx-auto text-signal-600 mb-2" size={24} />
          <p className="text-sm font-medium text-signal-700">Zero Skill Gaps Detected!</p>
          <p className="text-xs text-ink-500 mt-1">
            Your resume fully covers the required competencies for {activeRole}.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {gaps?.map((gap, i) => {
          const style = PRIORITY_STYLE[gap.priority] || PRIORITY_STYLE.CORE;
          return (
            <div key={i} className="rounded-lg border border-ink-100 bg-white p-5 transition-shadow hover:shadow-xs">
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

              <p className="text-sm text-ink-600 mb-3">{gap.reason}</p>

              <div className="rounded-md bg-ink-50 p-3 mb-3">
                <p className="text-xs font-medium text-ink-700 mb-1 flex items-center gap-1">
                  <Sparkles size={13} className="text-amber-600" /> Recommended Project Proof:
                </p>
                <p className="text-xs text-ink-600">{gap.project_suggestion}</p>
              </div>

              {gap.resources && gap.resources.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <span className="text-xs font-medium text-ink-500 flex items-center gap-1">
                    <BookOpen size={12} /> Learning Resources:
                  </span>
                  {gap.resources.map((url, j) => (
                    <a
                      key={j}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-signal-600 hover:text-signal-700 font-medium hover:underline bg-signal-500/10 px-2 py-0.5 rounded"
                    >
                      Guide {j + 1} ↗
                    </a>
                  ))}
                </div>
              )}

              <div className="flex items-center gap-3 pt-2.5 border-t border-ink-50">
                <a
                  href="/growth/roadmap"
                  className="text-xs font-semibold text-signal-600 hover:underline"
                >
                  Follow in Learning Roadmap →
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
