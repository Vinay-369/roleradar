import { useState, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Map as MapIcon, Sparkles, BookOpen, ExternalLink, Code2, Info, ArrowRight } from "lucide-react";
import { getProfile } from "../../lib/profile";
import { getRoadmap, getSkillGaps, getCanonicalRoles, type SkillGap } from "../../lib/learning";
import { RoleDropdownSelector } from "../../components/ui/RoleDropdownSelector";
import { ALL_JOB_ROLES } from "../../lib/roleConstants";

function getResourceLabel(url: string, index: number): { label: string; tag: string } {
  const lower = url.toLowerCase();
  if (lower.includes("docs.") || lower.includes("/docs") || lower.includes("developer.mozilla.org")) {
    return { label: "Official Docs", tag: "Documentation" };
  }
  if (lower.includes("freecodecamp")) {
    return { label: "freeCodeCamp", tag: "Full Course" };
  }
  if (lower.includes("coursera")) {
    return { label: "Coursera", tag: "Guided Specialization" };
  }
  if (lower.includes("youtube")) {
    return { label: "Video Tutorial", tag: "Crash Course" };
  }
  if (lower.includes("github.com")) {
    return { label: "GitHub Repository", tag: "Source & Primer" };
  }
  if (lower.includes("leetcode")) {
    return { label: "LeetCode Practice", tag: "Hands-on Problems" };
  }
  if (lower.includes("kaggle")) {
    return { label: "Kaggle Tutorial", tag: "Interactive Notebook" };
  }
  if (lower.includes("realpython")) {
    return { label: "Real Python Guide", tag: "Deep Dive" };
  }
  if (lower.includes("baeldung")) {
    return { label: "Baeldung Guide", tag: "Deep Dive" };
  }
  return { label: `Learning Resource ${index + 1}`, tag: "Study Guide" };
}

function GapDetail({ gap }: { gap: SkillGap }) {
  return (
    <div className="rounded-lg bg-ink-50/70 p-3.5 border border-ink-100/70 shadow-2xs">
      <div className="flex items-center justify-between mb-1.5">
        <p className="text-xs font-bold text-ink-900 flex items-center gap-1.5">
          <Code2 size={13} className="text-signal-600" /> {gap.skill}
        </p>
        <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
          gap.priority === "CORE"
            ? "text-alert-700 bg-alert-600/10 border border-alert-600/20"
            : gap.priority === "SECONDARY"
            ? "text-amber-700 bg-amber-500/10 border border-amber-500/20"
            : "text-signal-700 bg-signal-500/10 border border-signal-500/20"
        }`}>
          {gap.priority}
        </span>
      </div>
      <p className="text-[11px] text-ink-600 mb-2 leading-relaxed">{gap.reason}</p>
      
      <div className="bg-white/80 p-2.5 rounded-md border border-ink-100 mb-2.5">
        <p className="text-[11px] font-semibold text-ink-800 flex items-center gap-1 mb-0.5">
          💡 Recommended Practice Project:
        </p>
        <p className="text-[11px] text-ink-600 leading-snug">{gap.project_suggestion}</p>
      </div>

      {gap.resources && gap.resources.length > 0 ? (
        <div>
          <p className="text-[10px] uppercase font-bold tracking-wider text-ink-400 mb-1.5 flex items-center gap-1">
            <BookOpen size={11} className="text-signal-600" /> Recommended Study Resources:
          </p>
          <div className="flex flex-wrap gap-1.5">
            {gap.resources.map((url, j) => {
              const resInfo = getResourceLabel(url, j);
              return (
                <a
                  key={j}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group inline-flex items-center gap-1.5 text-[11px] font-medium text-ink-800 bg-white hover:bg-signal-500 hover:text-white px-2.5 py-1 rounded-md border border-ink-200 transition-all shadow-2xs"
                >
                  <span className="font-semibold">{resInfo.label}</span>
                  <span className="text-[9px] opacity-75 group-hover:text-white">({resInfo.tag})</span>
                  <ExternalLink size={10} className="shrink-0" />
                </a>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="text-[11px] text-ink-400 italic">
          Curated study resource currently unavailable for this specialized competency.
        </p>
      )}
    </div>
  );
}

function Bucket({ title, subtitle, skills, gapsBySkill }: { title: string; subtitle: string; skills: string[]; gapsBySkill: Map<string, SkillGap> }) {
  return (
    <div className="rounded-xl border border-ink-100 bg-white p-4 shadow-xs flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-1 pb-1">
          <p className="text-xs font-bold uppercase tracking-wider text-ink-900">{title}</p>
          <span className="text-[10px] font-semibold bg-ink-100 text-ink-700 px-2 py-0.5 rounded-full">
            {skills.length} {skills.length === 1 ? "skill" : "skills"}
          </span>
        </div>
        <p className="text-[11px] text-ink-400 mb-3">{subtitle}</p>

        {skills.length === 0 ? (
          <p className="text-xs text-ink-400 italic py-6 text-center">No missing competencies scheduled in this timeframe.</p>
        ) : (
          <div className="space-y-3">
            {skills.map((s) => {
              const gap = gapsBySkill.get(s.toLowerCase());
              return gap ? (
                <GapDetail key={s} gap={gap} />
              ) : (
                <div key={s} className="p-3 bg-ink-50 rounded-lg text-xs font-medium text-ink-800">
                  {s}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export function LearningRoadmap() {
  const { jobId } = useParams<{ jobId?: string }>();
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });

  const defaultRole = profile?.target_roles?.[0] || "Full Stack Developer";
  const [selectedRole, setSelectedRole] = useState<string>("");
  const [useGeneralMode, setUseGeneralMode] = useState(!jobId);

  const activeRole = selectedRole || defaultRole;

  const { data: roadmap, isLoading: roadmapLoading } = useQuery({
    queryKey: ["roadmap-custom", useGeneralMode ? null : jobId, activeRole],
    queryFn: () => {
      if (jobId && !useGeneralMode) return getRoadmap(jobId);
      return getRoadmap({ role: activeRole });
    },
  });

  const { data: gaps } = useQuery({
    queryKey: ["skill-gaps-custom", useGeneralMode ? null : jobId, activeRole],
    queryFn: () => {
      if (jobId && !useGeneralMode) return getSkillGaps(jobId);
      return getSkillGaps({ role: activeRole });
    },
  });

  const gapsBySkill = new Map((gaps ?? []).map((g) => [g.skill.toLowerCase(), g]));
  const totalScheduled = roadmap
    ? roadmap.immediate.length + roadmap.week_1.length + roadmap.week_2.length + roadmap.month_1.length
    : 0;

  const { data: canonicalRoles } = useQuery({
    queryKey: ["canonical-roles"],
    queryFn: getCanonicalRoles,
  });

  const availableRoles = useMemo(() => {
    if (!canonicalRoles || canonicalRoles.length === 0) return ALL_JOB_ROLES;
    return canonicalRoles.map((r) => r.role);
  }, [canonicalRoles]);

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <MapIcon size={24} className="text-signal-600" />
          <h1 className="font-display text-2xl text-ink-900">Learning Roadmap</h1>
        </div>
        {jobId && (
          <button
            onClick={() => setUseGeneralMode(!useGeneralMode)}
            className="text-xs font-semibold px-3 py-1.5 rounded-full border border-ink-200 text-ink-700 hover:bg-ink-100 transition-colors"
          >
            {useGeneralMode ? "Focus on Job Listing" : "Switch to Role-General"}
          </button>
        )}
      </div>
      <p className="text-ink-500 mb-6 text-sm">
        A step-by-step learning progression built from real market requirements with curated study resources and project guides.
      </p>

      {/* Target Role Selector Card */}
      <div className="bg-white rounded-xl border border-ink-100 p-4 mb-6 shadow-xs">
        <RoleDropdownSelector
          label="Roadmap for Target Role:"
          selectedRole={activeRole}
          onRoleChange={setSelectedRole}
          roles={availableRoles}
          includeAllOption={false}
          helperText="Select or specify any target role to generate a personalized multi-week learning progression."
        />
      </div>

      {roadmapLoading && (
        <div className="p-8 text-center bg-white rounded-lg border border-ink-100 shadow-xs">
          <span className="inline-block w-3 h-3 rounded-full bg-signal-500 animate-pulse mb-2" />
          <p className="text-sm text-ink-600 font-medium">Building personalized learning roadmap for {activeRole}…</p>
        </div>
      )}

      {roadmap && (
        <>
          {roadmap.personalization_status === "NONE" || (!roadmap.is_personalized && roadmap.personalization_status !== "LIMITED_EVIDENCE") ? (
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 mb-6 shadow-2xs flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-700 shrink-0 mt-0.5">
                  <Info size={16} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-500/10 text-blue-700 px-2 py-0.5 rounded-full border border-blue-500/20">
                      Market Benchmark
                    </span>
                  </div>
                  <p className="text-xs text-ink-700 mt-1 leading-relaxed">
                    This is a market-standard skill roadmap for <strong className="text-ink-900">{activeRole}</strong>. Upload your resume to see your personal skill gaps.
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
          ) : roadmap.personalization_status === "LIMITED_EVIDENCE" ? (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 mb-6 shadow-2xs flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-700 shrink-0 mt-0.5">
                  <Info size={16} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-700 px-2 py-0.5 rounded-full border border-amber-500/20">
                      Market / Limited Evidence
                    </span>
                  </div>
                  <p className="text-xs text-ink-700 mt-1 leading-relaxed">
                    Your uploaded resume contains limited skill evidence for a reliable personal gap analysis. This roadmap reflects market requirements for <strong className="text-ink-900">{activeRole}</strong> — consider updating your resume with more technical project & skill details.
                  </p>
                </div>
              </div>
              <Link
                to="/resume/master"
                className="inline-flex items-center gap-1 text-xs font-semibold text-amber-800 bg-amber-500/15 hover:bg-amber-500/25 px-3 py-1.5 rounded-lg shrink-0 transition-colors border border-amber-500/30"
              >
                <span>Update Resume</span>
                <ArrowRight size={12} />
              </Link>
            </div>
          ) : (
            <div className="flex items-center justify-between px-1 mb-4">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wider bg-signal-500/10 text-signal-700 px-2.5 py-0.5 rounded-full border border-signal-500/20 flex items-center gap-1">
                  <Sparkles size={11} /> {roadmap.roadmap_type === "JOB" ? "Job-Specific Personalization" : "Candidate vs Market Analysis"}
                </span>
                {roadmap.role_context && (
                  <span className="text-xs text-ink-500 font-medium">
                    • {roadmap.role_context}
                  </span>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {roadmap && totalScheduled === 0 && (
        roadmap.role_confidence === "LOW" ? (
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-8 text-center mb-6">
            <Info className="mx-auto text-amber-600 mb-2" size={28} />
            <h3 className="text-base font-bold text-amber-900">Limited Market Evidence For This Role</h3>
            <p className="text-xs text-ink-600 mt-1 max-w-md mx-auto leading-relaxed">
              {roadmap.message || `We couldn't confidently determine role-specific skill requirements for "${activeRole}". Add a job description for a more precise analysis.`}
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-signal-500/20 bg-signal-500/5 p-8 text-center mb-6">
            <Sparkles className="mx-auto text-signal-600 mb-2" size={28} />
            <h3 className="text-base font-bold text-signal-800">All Key Competencies Covered!</h3>
            <p className="text-xs text-ink-600 mt-1 max-w-md mx-auto leading-relaxed">
              Your resume already demonstrates coverage for the essential technical skills required for {activeRole}. You can practice interview questions or start applying now.
            </p>
          </div>
        )
      )}

      {roadmap && totalScheduled > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Bucket
            title="Sprint 1: Immediate"
            subtitle="Core high-priority blockers (Days 1–3)"
            skills={roadmap.immediate}
            gapsBySkill={gapsBySkill}
          />
          <Bucket
            title="Sprint 2: Week 1 Foundation"
            subtitle="Foundational missing concepts (Week 1)"
            skills={roadmap.week_1}
            gapsBySkill={gapsBySkill}
          />
          <Bucket
            title="Sprint 3: Practical Implementation"
            subtitle="Hands-on practice & frameworks (~Week 2)"
            skills={roadmap.week_2}
            gapsBySkill={gapsBySkill}
          />
          <Bucket
            title="Sprint 4: Month 1 Advanced"
            subtitle="Architecture, scale & bonus skills (Month 1)"
            skills={roadmap.month_1}
            gapsBySkill={gapsBySkill}
          />
        </div>
      )}
    </div>
  );
}
