import { useEffect, useState, useMemo } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Map as MapIcon,
  Sparkles,
  BookOpen,
  ExternalLink,
  Code2,
  Info,
  ArrowRight,
  Clock3,
  ChevronDown,
  ShieldCheck,
} from "lucide-react";
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
  const [activeStep, setActiveStep] = useState(0);
  const steps = [
    { title: "Learn", content: gap.learning_guidance || gap.reason, icon: BookOpen },
    { title: "Practice", content: gap.practice_guidance || gap.project_suggestion, icon: Code2 },
    {
      title: "Prove",
      content: gap.proof_guidance || `Record the ${gap.skill} deliverable, the decisions you made, and a measurable outcome. Add that role-relevant evidence to a project or your work history.`,
      icon: ShieldCheck,
    },
  ];
  const ActiveStepIcon = steps[activeStep].icon;

  return (
    <article className="rr-interactive-card rounded-xl border border-slate-200 bg-white p-3 shadow-2xs sm:p-4">
      <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <p className="flex items-center gap-1.5 text-sm font-bold text-ink-900">
          <Code2 size={13} className="text-signal-600" /> {gap.skill}
        </p>
        <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase ${
          gap.priority === "CORE"
            ? "border-indigo-200 bg-indigo-50 text-indigo-700"
            : gap.priority === "SECONDARY"
            ? "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-300"
            : "border-emerald-200 bg-emerald-50 text-emerald-700"
        }`}>
          {gap.priority}
        </span>
      </div>
      <p className="mb-2 text-[11px] text-ink-500">
        {gap.target_job_title}{gap.subdomain ? ` · ${gap.subdomain}` : ""}
      </p>
      <span className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-ink-600">
        <Clock3 size={12} className="text-signal-600" />
        Suggested study · {gap.estimated_days} days
      </span>

      <div className="rr-learning-step-group mb-2.5 flex items-center gap-1 rounded-lg bg-slate-100 p-1" role="group" aria-label={`Learning steps for ${gap.skill}`}>
        {steps.map((step, index) => {
          const StepIcon = step.icon;
          return (
            <button
              key={step.title}
              type="button"
              onClick={() => setActiveStep(index)}
              aria-pressed={activeStep === index}
              className={`inline-flex min-w-0 flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-[10px] font-semibold transition-colors ${
                activeStep === index
                   ? "bg-sky-50 text-sky-700 shadow-2xs dark:bg-sky-950/60 dark:text-sky-300"
                   : "text-ink-700 hover:text-ink-950 dark:text-ink-200 dark:hover:text-white"
              }`}
            >
              <StepIcon size={12} className="rr-roadmap-step-icon" />
              <span className="rr-roadmap-step-label">Step {index + 1} · {step.title}</span>
            </button>
          );
        })}
      </div>
      <div className="mb-3 min-h-14 rounded-lg border border-slate-200 bg-slate-50 p-3">
        <p className="mb-1 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-ink-600">
          <ActiveStepIcon size={12} className="text-signal-600" />
          Step {activeStep + 1} · {steps[activeStep].title}
        </p>
        <p className="text-[11px] leading-relaxed text-ink-700">{steps[activeStep].content}</p>
      </div>

      {gap.resources && gap.resources.length > 0 ? (
        <div>
          <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-ink-500">
            <BookOpen size={12} className="text-signal-600" /> Curated resources
          </p>
          <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
            {gap.resources.map((url, j) => {
              const resInfo = getResourceLabel(url, j);
              return (
                <a
                  key={j}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rr-learning-resource inline-flex min-w-0 items-center gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-[11px] font-medium text-ink-800 shadow-2xs transition-colors hover:border-signal-500/40 hover:bg-signal-50/60"
                  title={`Open ${resInfo.label}: ${url}`}
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold">{resInfo.label}</span>
                    <span className="block truncate text-[9px] text-ink-500">{resInfo.tag}</span>
                  </span>
                  <ExternalLink size={12} className="shrink-0 text-signal-600" />
                </a>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
          <Sparkles size={13} className="mt-0.5 shrink-0 text-signal-600" />
          <p className="text-[10px] leading-relaxed text-ink-600">
            No curated resource yet. Use the practice step to guide your self-directed learning.
          </p>
        </div>
      )}
    </article>
  );
}

function Bucket({ id, title, subtitle, skills, gapsBySkill }: { id: string; title: string; subtitle: string; skills: string[]; gapsBySkill: Map<string, SkillGap> }) {
  const [isOpen, setIsOpen] = useState(true);
  const estimatedDays = skills.reduce(
    (total, skill) => total + (gapsBySkill.get(skill.toLowerCase())?.estimated_days ?? 0),
    0,
  );
  const durationLabel = estimatedDays > 0
    ? `~${Math.max(1, Math.ceil(estimatedDays / 7))} ${Math.ceil(estimatedDays / 7) === 1 ? "week" : "weeks"}`
    : null;

  return (
    <section id={id} className="rr-interactive-card scroll-mt-6 flex flex-col rounded-xl border border-slate-200 bg-white p-3 shadow-[0_2px_8px_rgba(0,0,0,0.04)] sm:p-4">
      <div>
        <div className="mb-3 flex items-center gap-3">
          <span aria-hidden="true" className="h-8 w-1 shrink-0 rounded-full bg-signal-500" />
          <button
            type="button"
            aria-expanded={isOpen}
            onClick={() => setIsOpen((open) => !open)}
            className="flex min-w-0 flex-1 items-center justify-between gap-2 text-left"
          >
            <span className="min-w-0">
              <span className="block truncate text-xs font-bold uppercase tracking-wider text-ink-900">{title}</span>
              <span className="mt-0.5 block text-[10px] text-ink-500">{subtitle}</span>
            </span>
            <span className="flex shrink-0 items-center gap-2">
              <span className="hidden rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-ink-600 sm:inline-flex">
                {skills.length} {skills.length === 1 ? "skill" : "skills"}{durationLabel ? ` · ${durationLabel}` : ""}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-[10px] font-semibold text-ink-600 sm:hidden">
                {skills.length}{durationLabel ? ` · ${durationLabel}` : ""}
              </span>
              <ChevronDown size={15} className={`text-ink-500 transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </span>
          </button>
        </div>

        {isOpen && (skills.length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-5 text-center text-xs text-ink-500">
            No missing competencies scheduled in this timeframe.
          </p>
        ) : (
          <div className="space-y-2.5">
            {skills.map((skill) => {
              const gap = gapsBySkill.get(skill.toLowerCase());
              return gap ? (
                <GapDetail key={skill} gap={gap} />
              ) : (
                <div key={skill} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs font-medium text-ink-800">
                  {skill}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </section>
  );
}

export function LearningRoadmap() {
  const { jobId } = useParams<{ jobId?: string }>();
  const [searchParams] = useSearchParams();
  const requestedRole = searchParams.get("role");
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });

  const defaultRole = requestedRole || profile?.target_roles?.[0] || "";
  const [selectedRole, setSelectedRole] = useState<string>(requestedRole || "");
  useEffect(() => {
    setSelectedRole(requestedRole || "");
  }, [requestedRole]);
  const [useGeneralMode, setUseGeneralMode] = useState(!jobId);

  const activeRole = selectedRole || defaultRole;

  const { data: roadmap, isLoading: roadmapLoading } = useQuery({
    queryKey: ["roadmap-custom", useGeneralMode ? null : jobId, activeRole],
    queryFn: () => {
      if (jobId && !useGeneralMode) return getRoadmap(jobId);
      return getRoadmap({ role: activeRole });
    },
    enabled: Boolean((jobId && !useGeneralMode) || activeRole),
  });

  const { data: gaps } = useQuery({
    queryKey: ["skill-gaps-custom", useGeneralMode ? null : jobId, activeRole],
    queryFn: () => {
      if (jobId && !useGeneralMode) return getSkillGaps(jobId);
      return getSkillGaps({ role: activeRole });
    },
    enabled: Boolean((jobId && !useGeneralMode) || activeRole),
  });

  const gapsBySkill = new Map((gaps ?? []).map((g) => [g.skill.toLowerCase(), g]));
  const totalScheduled = roadmap
    ? roadmap.immediate.length + roadmap.week_1.length + roadmap.week_2.length + roadmap.month_1.length
    : 0;
  const sprintItems = roadmap
    ? [
        { id: "roadmap-sprint-1", label: "Sprint 1", title: "Immediate", subtitle: "Days 1–3", skills: roadmap.immediate },
        { id: "roadmap-sprint-2", label: "Sprint 2", title: "Week 1 Foundation", subtitle: "Week 1", skills: roadmap.week_1 },
        { id: "roadmap-sprint-3", label: "Sprint 3", title: "Practical Implementation", subtitle: "Week 2", skills: roadmap.week_2 },
        { id: "roadmap-sprint-4", label: "Sprint 4", title: "Month 1 Advanced", subtitle: "Month 1", skills: roadmap.month_1 },
      ]
    : [];

  const { data: canonicalRoles } = useQuery({
    queryKey: ["canonical-roles"],
    queryFn: getCanonicalRoles,
  });

  const availableRoles = useMemo(() => {
    if (!canonicalRoles || canonicalRoles.length === 0) return ALL_JOB_ROLES;
    return canonicalRoles;
  }, [canonicalRoles]);

  return (
    <div className="rr-learning-roadmap mx-auto w-full min-w-0 max-w-5xl">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <MapIcon size={22} className="shrink-0 text-signal-600" />
          <h1 className="min-w-0 break-words font-display text-2xl font-bold text-ink-900">Learning Roadmap</h1>
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
      <p className="mb-4 text-sm leading-relaxed text-ink-500">
        Build role-ready skills through a focused, step-by-step learning plan for {activeRole}.
      </p>

      {/* Target Role Selector Card */}
      <div className="mb-5 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-[0_2px_8px_rgba(0,0,0,0.04)] transition-colors focus-within:border-signal-500/50 focus-within:ring-2 focus-within:ring-signal-500/10 sm:p-4 lg:flex-row lg:items-center">
        <RoleDropdownSelector
          label="Roadmap for Target Role:"
          selectedRole={activeRole}
          onRoleChange={setSelectedRole}
          roles={availableRoles}
          includeAllOption={false}
          helperText="Select or specify any target role to generate a personalized multi-week learning progression."
          className="min-w-0 flex-1 [&_label]:text-xs [&_input[role=combobox]]:h-11 [&_input[role=combobox]]:bg-slate-50 [&_input[role=combobox]]:py-2.5 [&_input[role=combobox]]:focus:ring-signal-500/15"
        />
        {roadmap && (
          <span className={`inline-flex shrink-0 items-center justify-center gap-1.5 self-start rounded-full border px-3 py-2 text-[10px] font-bold uppercase tracking-wide lg:self-center ${
            roadmap.personalization_status === "NONE" || (!roadmap.is_personalized && roadmap.personalization_status !== "LIMITED_EVIDENCE")
              ? "border-blue-200 bg-blue-50 text-blue-700"
              : roadmap.personalization_status === "LIMITED_EVIDENCE"
                ? "border-amber-200 bg-amber-50 text-amber-800"
                : "border-signal-500/25 bg-signal-500/10 text-signal-700"
          }`}>
            {roadmap.personalization_status === "NONE" || (!roadmap.is_personalized && roadmap.personalization_status !== "LIMITED_EVIDENCE")
              ? <><Info size={12} /> Market Benchmark</>
              : roadmap.personalization_status === "LIMITED_EVIDENCE"
                ? <><Info size={12} /> Market · Limited Evidence</>
                : <><Sparkles size={12} /> {roadmap.roadmap_type === "JOB" ? "Job-Specific Analysis" : "Candidate vs Market Analysis"}</>}
          </span>
        )}
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
            roadmap.role_context ? (
              <p className="mb-4 px-1 text-xs font-medium text-ink-500">{roadmap.role_context}</p>
            ) : null
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
        <>
        <nav aria-label="Learning roadmap sprints" className="relative mb-4 overflow-x-auto rounded-xl border border-slate-200 bg-white p-3 shadow-[0_2px_8px_rgba(0,0,0,0.04)] sm:p-4">
          <div aria-hidden="true" className="absolute left-[12.5%] right-[12.5%] top-[30px] hidden h-px bg-slate-200 dark:bg-ink-300 sm:block" />
          <ol className="relative flex min-w-[620px] items-start">
            {sprintItems.map((sprint, index) => (
              <li key={sprint.id} className="flex flex-1">
                <a
                  href={`#${sprint.id}`}
                  className="group flex min-w-0 flex-1 flex-col items-center gap-1.5 rounded-lg px-2 py-1 text-center transition-colors hover:bg-slate-50"
                >
                  <span className="z-10 flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-signal-600 text-[10px] font-bold text-white shadow-sm ring-1 ring-signal-600/20">
                    {index + 1}
                  </span>
                  <span className="text-[10px] font-bold uppercase tracking-wide text-ink-700 group-hover:text-signal-700">{sprint.label}</span>
                  <span className="max-w-full truncate text-[10px] text-ink-500">{sprint.skills.length} {sprint.skills.length === 1 ? "skill" : "skills"} · {sprint.subtitle}</span>
                </a>
              </li>
            ))}
          </ol>
        </nav>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Bucket
            id="roadmap-sprint-1"
            title="Sprint 1: Immediate"
            subtitle="Core high-priority blockers (Days 1–3)"
            skills={roadmap.immediate}
            gapsBySkill={gapsBySkill}
          />
          <Bucket
            id="roadmap-sprint-2"
            title="Sprint 2: Week 1 Foundation"
            subtitle="Foundational missing concepts (Week 1)"
            skills={roadmap.week_1}
            gapsBySkill={gapsBySkill}
          />
          <Bucket
            id="roadmap-sprint-3"
            title="Sprint 3: Practical Implementation"
            subtitle="Hands-on practice & frameworks (~Week 2)"
            skills={roadmap.week_2}
            gapsBySkill={gapsBySkill}
          />
          <Bucket
            id="roadmap-sprint-4"
            title="Sprint 4: Month 1 Advanced"
            subtitle="Architecture, scale & bonus skills (Month 1)"
            skills={roadmap.month_1}
            gapsBySkill={gapsBySkill}
          />
        </div>
        </>
      )}
    </div>
  );
}
