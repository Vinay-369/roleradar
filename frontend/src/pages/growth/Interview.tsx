import { useState, useMemo, useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  MessageCircleQuestion, Sparkles,
  ChevronDown, ChevronUp, AlertTriangle, Lightbulb,
  Video, Code2, Users, Briefcase, Star, CheckCircle2,
  Timer, Play, RotateCcw, Bot, BookOpen,
  Search, Terminal, ArrowUpRight,
} from "lucide-react";
import { getProfile } from "../../lib/profile";
import {
  getCuratedInterviewQuestions,
  getInterviewQuestions,
  type InterviewPrep,
  type InterviewQuestion,
} from "../../lib/interview";
import { getCanonicalRoles } from "../../lib/learning";
import { RoleDropdownSelector } from "../../components/ui/RoleDropdownSelector";
import { ALL_JOB_ROLES } from "../../lib/roleConstants";

const MOCK_PLATFORMS = [
  {
    name: "Pramp",
    url: "https://www.pramp.com/",
    desc: "Free 1-on-1 peer technical and behavioral mock interviews with live video & collaborative code editor.",
    tag: "Free Peer Mocks",
  },
  {
    name: "interviewing.io",
    url: "https://interviewing.io/",
    desc: "Free recorded technical mock interviews with senior FAANG and Tier-1 engineers.",
    tag: "Real FAANG Recordings",
  },
  {
    name: "LeetCode Discuss",
    url: "https://leetcode.com/discuss/interview-question",
    desc: "Active community repository of real interview questions reported by candidates across companies.",
    tag: "Company Question Sets",
  },
  {
    name: "Exponent",
    url: "https://www.tryexponent.com/",
    desc: "Free system design breakdowns and behavioral frameworks for technical candidates.",
    tag: "Framework Guides",
  },
  {
    name: "Tech Interview Handbook",
    url: "https://www.techinterviewhandbook.org/",
    desc: "Curated algorithms cheat sheets, behavioral STAR guides, and resume preparation tips.",
    tag: "Free Guides & Cheatsheets",
  },
];

const MOCK_PLATFORM_ICONS = [Users, Video, Code2, Briefcase, BookOpen];

function PracticeTimer() {
  const [secondsLeft, setSecondsLeft] = useState(120);
  const [isActive, setIsActive] = useState(false);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;
    if (isActive && secondsLeft > 0) {
      interval = setInterval(() => setSecondsLeft((s) => s - 1), 1000);
    } else if (secondsLeft === 0) {
      setIsActive(false);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isActive, secondsLeft]);

  const mins = Math.floor(secondsLeft / 60);
  const secs = secondsLeft % 60;
  const timeFormatted = `${mins}:${secs < 10 ? "0" : ""}${secs}`;

  return (
    <div className="mt-2 space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-ink-800 flex items-center gap-1.5">
          <Timer size={14} className="text-signal-500" />
          2-Minute Mock Answer Practice:
        </span>
        <div className="flex items-center gap-2">
          <span className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${secondsLeft <= 30 ? "bg-alert-600/10 text-alert-600" : "bg-signal-500/10 text-signal-700"}`}>
            {timeFormatted}
          </span>
          <button
            onClick={() => setIsActive(!isActive)}
            className="p-1 rounded bg-signal-500 hover:bg-signal-600 text-white text-xs font-medium transition-colors"
            title={isActive ? "Pause" : "Start Timer"}
          >
            <Play size={11} className={isActive ? "rotate-90" : ""} />
          </button>
          <button
            onClick={() => {
              setIsActive(false);
              setSecondsLeft(120);
            }}
            className="p-1 rounded bg-ink-200 hover:bg-ink-300 text-ink-700 text-xs transition-colors"
            title="Reset Timer"
          >
            <RotateCcw size={11} />
          </button>
        </div>
      </div>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Type key talking points / STAR outline while speaking your answer out loud…"
        rows={2}
        className="w-full text-xs p-2 rounded-lg border border-ink-100 bg-white text-ink-900 outline-none focus:border-signal-500 shadow-2xs resize-none"
      />
    </div>
  );
}

function QuestionCard({
  q,
  index,
  role,
  isMastered,
  isBookmarked,
  onToggleMastered,
  onToggleBookmarked,
}: {
  q: InterviewQuestion;
  index: number;
  role: string;
  isMastered: boolean;
  isBookmarked: boolean;
  onToggleMastered: () => void;
  onToggleBookmarked: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showPracticeTimer, setShowPracticeTimer] = useState(false);

  const isTechnical = q.category === "technical";
  const isManagerial = q.category === "managerial" || q.category === "project_defense";

  const badgeStyle = isTechnical
    ? "bg-signal-500/10 text-signal-700 border-signal-500/20"
    : isManagerial
    ? "bg-purple-500/10 text-purple-700 border-purple-500/20"
    : "bg-amber-500/10 text-amber-700 border-amber-500/20";

  const roundName = isTechnical
    ? "Technical Round"
    : isManagerial
    ? "Managerial Round"
    : "HR & Culture Round";

  return (
    <article className={`rounded-xl border border-slate-200 p-4 shadow-[0_2px_8px_rgba(0,0,0,0.04)] transition-all hover:shadow-md sm:p-5 ${
      isMastered
        ? "border-signal-500/40 bg-white"
        : "bg-white"
    }`}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${badgeStyle}`}>
            {roundName}
          </span>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-bold font-mono text-slate-600">Q{index + 1}</span>
          <span className="hidden max-w-40 truncate text-[11px] font-medium text-ink-500 sm:inline">{role}</span>
          {isMastered && (
            <span className="text-[10px] font-semibold text-signal-700 bg-signal-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
              <CheckCircle2 size={10} /> Mastered
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Bookmark Button */}
          <button
            onClick={onToggleBookmarked}
            aria-label={isBookmarked ? "Remove bookmark" : "Save question"}
            className={`inline-flex h-9 w-9 items-center justify-center rounded-lg border transition-colors ${
              isBookmarked
                ? "border-amber-200 bg-amber-50 text-amber-600"
                : "border-slate-200 bg-white text-ink-400 hover:border-amber-200 hover:bg-amber-50 hover:text-amber-600"
            }`}
            title={isBookmarked ? "Remove Bookmark" : "Bookmark for Revision"}
          >
            <Star size={14} className={isBookmarked ? "fill-amber-500" : ""} />
          </button>

          {/* Mastered Checkbox Button */}
          <button
            onClick={onToggleMastered}
            aria-pressed={isMastered}
            className={`inline-flex h-9 items-center gap-1.5 rounded-lg border px-3 text-xs font-semibold transition-all ${
              isMastered
                ? "border-signal-600 bg-signal-600 text-white shadow-2xs hover:bg-signal-700"
                : "border-slate-200 bg-white text-ink-700 hover:border-signal-500/40 hover:bg-signal-50"
            }`}
            title={isMastered ? "Mark as Pending" : "Mark as Mastered"}
          >
            <CheckCircle2 size={13} />
            <span>{isMastered ? "Mastered" : "Mark Done"}</span>
          </button>
        </div>
      </div>

      <h3 className="mb-3 text-sm font-semibold leading-relaxed text-ink-900 sm:text-base">
        {q.question}
      </h3>

      {q.star_hint && (
        <div className="mb-3 rounded-lg border border-indigo-100 border-l-4 border-l-indigo-500 bg-indigo-50/50 p-3">
          <p className="mb-0.5 flex items-center gap-1.5 text-xs font-semibold text-indigo-800">
            <Sparkles size={13} className="text-indigo-600" /> Focus Strategy
          </p>
          <p className="text-xs text-ink-600 leading-relaxed">{q.star_hint}</p>
        </div>
      )}

      {/* Action Buttons: Expand Answer & Practice Timer */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          className="inline-flex min-h-9 flex-1 items-center justify-between gap-2 rounded-full border border-slate-200 bg-white px-3.5 py-2 text-left text-xs font-semibold text-ink-700 transition-colors hover:border-signal-500/40 hover:bg-slate-50 sm:flex-none"
        >
          <span className="flex items-center gap-1.5">
            <Lightbulb size={14} className="shrink-0 text-amber-500" />
            {expanded ? "Hide Answer Strategy" : "How to Answer & Sample Response"}
          </span>
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        <button
          type="button"
          onClick={() => setShowPracticeTimer(!showPracticeTimer)}
          aria-expanded={showPracticeTimer}
          className="inline-flex min-h-9 items-center justify-center gap-1.5 rounded-full border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-ink-700 transition-colors hover:border-signal-500/40 hover:bg-slate-50"
          title="Practice answering in 2 minutes"
        >
          <Timer size={13} className="text-signal-500" />
          <span>{showPracticeTimer ? "Hide Timer" : "Practice (2m)"}</span>
        </button>
        <Link
          to={`/copilot?role=${encodeURIComponent(role)}&category=${encodeURIComponent(q.category)}&prompt=${encodeURIComponent(`For the interview question: "${q.question}" (in a ${roundName} for ${role}):\n\nPlease provide detailed guidance on:\n1. How to approach and structure the answer\n2. How to present and communicate key points effectively\n3. Key technical/architectural concepts or STAR talking points to mention\n4. What mistakes or red flags to avoid`)}`}
          className="inline-flex min-h-9 items-center justify-center gap-1.5 rounded-full border border-signal-500/25 bg-signal-500/5 px-3.5 py-2 text-xs font-semibold text-signal-800 transition-colors hover:bg-signal-500/10"
        >
          <Bot size={14} className="text-signal-600" />
          Ask Copilot
          <ArrowUpRight size={12} />
        </Link>
      </div>

      {showPracticeTimer && <PracticeTimer />}

      {expanded && (
        <div className="mt-3 pt-3 border-t border-ink-100 space-y-3 text-xs animate-fade-in-up">
          {q.strategy && (
            <div className="p-3 bg-signal-500/5 border border-signal-500/20 rounded-lg">
              <p className="font-bold text-signal-800 uppercase tracking-wider text-[11px] mb-1 flex items-center gap-1">
                🎯 Structured Attempt Strategy:
              </p>
              <p className="text-ink-700 leading-relaxed font-sans">{q.strategy}</p>
            </div>
          )}

          {q.sample_answer && (
            <div className="p-3 bg-ink-50 rounded-lg border border-ink-100">
              <p className="font-bold text-ink-900 uppercase tracking-wider text-[11px] mb-1 flex items-center gap-1">
                💬 Sample Model Response:
              </p>
              <p className="text-ink-700 leading-relaxed italic font-sans">{q.sample_answer}</p>
            </div>
          )}

          {q.pitfalls && (
            <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
              <p className="font-bold text-amber-800 uppercase tracking-wider text-[11px] mb-1 flex items-center gap-1">
                <AlertTriangle size={12} className="text-amber-600" /> Key Pitfall to Avoid:
              </p>
              <p className="text-amber-900/90 leading-relaxed">{q.pitfalls}</p>
            </div>
          )}
        </div>
      )}

    </article>
  );
}

export function Interview() {
  const profileQuery = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const profile = profileQuery.data;
  const { data: canonicalRoles } = useQuery({
    queryKey: ["canonical-roles"],
    queryFn: getCanonicalRoles,
  });

  const defaultRole = profile?.target_roles?.[0] || "";
  const [selectedRole, setSelectedRole] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"technical" | "managerial" | "hr">("technical");
  const [filterView, setFilterView] = useState<"all" | "bookmarked" | "pending">("all");

  const effectiveRole = selectedRole || defaultRole;
  const roleOptions = canonicalRoles?.length ? canonicalRoles : ALL_JOB_ROLES;

  const interviewQuery = useQuery({
    queryKey: ["interview-questions", effectiveRole],
    queryFn: async (): Promise<InterviewPrep & { usedCuratedFallback?: boolean }> => {
      try {
        return await getInterviewQuestions({ role: effectiveRole });
      } catch (generationError) {
        try {
          return {
            ...(await getCuratedInterviewQuestions(effectiveRole)),
            usedCuratedFallback: true,
          };
        } catch {
          throw generationError;
        }
      }
    },
    enabled: Boolean(effectiveRole) && profileQuery.isFetched,
    staleTime: 5 * 60 * 1000,
  });

  // Stored mastered and bookmarked questions
  const [masteredMap, setMasteredMap] = useState<Record<string, boolean>>(() => {
    try {
      const stored = localStorage.getItem("roleradar_mastered_questions");
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  const [bookmarkMap, setBookmarkMap] = useState<Record<string, boolean>>(() => {
    try {
      const stored = localStorage.getItem("roleradar_bookmarked_questions");
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("roleradar_mastered_questions", JSON.stringify(masteredMap));
    } catch {
      // ignore
    }
  }, [masteredMap]);

  useEffect(() => {
    try {
      localStorage.setItem("roleradar_bookmarked_questions", JSON.stringify(bookmarkMap));
    } catch {
      // ignore
    }
  }, [bookmarkMap]);

  const toggleMastered = (qKey: string) => {
    setMasteredMap((prev) => ({ ...prev, [qKey]: !prev[qKey] }));
  };

  const toggleBookmarked = (qKey: string) => {
    setBookmarkMap((prev) => ({ ...prev, [qKey]: !prev[qKey] }));
  };

  const currentQuestions = useMemo(() => {
    return (interviewQuery.data?.questions ?? []).filter((question) => {
      const category = question.category.toLowerCase();
      if (activeTab === "hr") return category === "hr" || category === "behavioral";
      if (activeTab === "managerial") return category === "managerial" || category === "project_defense";
      return category === "technical" || category === "role_specific";
    });
  }, [interviewQuery.data?.questions, activeTab]);

  // Compute stats
  const masteredCount = useMemo(() => {
    return currentQuestions.filter((q) => masteredMap[`${effectiveRole}_${activeTab}_${q.question}`]).length;
  }, [currentQuestions, effectiveRole, activeTab, masteredMap]);

  const bookmarkCount = useMemo(() => {
    return currentQuestions.filter((q) => bookmarkMap[`${effectiveRole}_${activeTab}_${q.question}`]).length;
  }, [currentQuestions, effectiveRole, activeTab, bookmarkMap]);

  // Filtered view
  const displayedQuestions = useMemo(() => {
    return currentQuestions.filter((q) => {
      const qKey = `${effectiveRole}_${activeTab}_${q.question}`;
      if (filterView === "bookmarked") return !!bookmarkMap[qKey];
      if (filterView === "pending") return !masteredMap[qKey];
      return true;
    });
  }, [currentQuestions, effectiveRole, activeTab, filterView, bookmarkMap, masteredMap]);

  const readinessPercent = currentQuestions.length > 0
    ? Math.round((masteredCount / currentQuestions.length) * 100)
    : 0;

  return (
    <div className="mx-auto w-full min-w-0 max-w-5xl space-y-4">
      <div>
        <div className="mb-1 flex items-center gap-2">
          <MessageCircleQuestion size={22} className="shrink-0 text-signal-600" />
          <h1 className="min-w-0 break-words font-display text-2xl font-bold text-ink-900">Interview Preparation</h1>
        </div>
        <p className="text-sm leading-relaxed text-ink-500">
          Interview questions are generated for your selected role and experience, with model answers, 2-minute practice timers, and free peer practice links.
        </p>
      </div>

      {/* Target Role Dropdown Card */}
      <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-[0_2px_8px_rgba(0,0,0,0.04)] transition-all hover:border-signal-500/25 focus-within:border-signal-500/50 focus-within:ring-2 focus-within:ring-signal-500/10 sm:p-4">
        <div className="mb-2 flex items-center justify-between gap-3">
          <span className="inline-flex items-center gap-2 text-xs font-bold text-ink-800">
            <Search size={14} className="text-signal-600" />
            Prepare for your target role
          </span>
          <span className="hidden items-center gap-1.5 rounded-full border border-signal-500/20 bg-signal-500/5 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wide text-signal-700 sm:inline-flex">
            <Sparkles size={11} />
            Role-specific question set
          </span>
        </div>
        <RoleDropdownSelector
          label="Select Target Job Role:"
          selectedRole={selectedRole}
          onRoleChange={setSelectedRole}
          roles={roleOptions}
          includeAllOption={false}
          helperText="Choose a specialized role or enter a custom title to generate role-specific interview questions."
          className="[&_label]:text-xs [&_input[role=combobox]]:h-11 [&_input[role=combobox]]:bg-slate-50 [&_input[role=combobox]]:py-2.5 [&_input[role=combobox]]:focus:ring-signal-500/15"
        />
      </div>

      {/* Readiness, filters, and interview round navigation */}
      <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-[0_2px_8px_rgba(0,0,0,0.04)] dark:border-ink-200 dark:bg-ink-900 sm:p-4">
        <div className="mb-3 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="flex items-center gap-1.5 text-xs font-bold text-ink-900">
                <CheckCircle2 size={15} className="text-signal-600" />
                Round Readiness
              </span>
              <span className="text-xs font-semibold tabular-nums text-ink-600">
                {masteredCount}/{currentQuestions.length} mastered · {readinessPercent}%
              </span>
            </div>
            <div
              className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100"
              role="progressbar"
              aria-label="Round readiness"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={readinessPercent}
            >
              <div
                className="h-full rounded-full bg-gradient-to-r from-signal-500 to-emerald-500 transition-all duration-500"
                style={{ width: `${readinessPercent}%` }}
              />
            </div>
          </div>

            <div role="group" aria-label="Filter questions" className="flex shrink-0 items-center gap-1 rounded-full bg-slate-100 p-1 dark:bg-ink-800">
            {([
              ["all", "All", currentQuestions.length],
              ["bookmarked", "Saved", bookmarkCount],
              ["pending", "Pending", currentQuestions.length - masteredCount],
            ] as const).map(([filter, label, count]) => (
              <button
                key={filter}
                type="button"
                onClick={() => setFilterView(filter)}
                aria-pressed={filterView === filter}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-semibold transition-colors ${
                  filterView === filter
                    ? "bg-white text-ink-900 shadow-2xs dark:bg-ink-950 dark:text-white"
                    : "text-ink-600 hover:text-ink-900 dark:text-ink-300 dark:hover:text-white"
                }`}
              >
                {filter === "bookmarked" && <Star size={11} className={bookmarkCount > 0 ? "fill-amber-400 text-amber-500" : ""} />}
                {label}
                <span className="text-[10px] opacity-70">{count}</span>
              </button>
            ))}
          </div>
        </div>

      <div role="group" aria-label="Interview rounds" className="grid grid-cols-1 gap-1.5 border-t border-slate-100 pt-3 dark:border-ink-200 sm:grid-cols-3">
        <button
          type="button"
          onClick={() => setActiveTab("technical")}
          aria-pressed={activeTab === "technical"}
          className={`flex min-w-fit items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-semibold transition-all sm:px-4 ${
            activeTab === "technical"
              ? "border border-signal-500/25 bg-signal-500/10 text-signal-800 shadow-2xs dark:border-signal-400/30 dark:bg-signal-500/15 dark:text-signal-300"
              : "border border-transparent text-ink-500 hover:border-slate-200 hover:bg-slate-50 hover:text-ink-800 dark:text-ink-300 dark:hover:border-ink-300 dark:hover:bg-ink-800 dark:hover:text-white"
          }`}
        >
          <Terminal size={15} /> Technical Round
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("managerial")}
          aria-pressed={activeTab === "managerial"}
          className={`flex min-w-fit items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-semibold transition-all sm:px-4 ${
            activeTab === "managerial"
              ? "border border-purple-200 bg-purple-50 text-purple-800 shadow-2xs dark:border-purple-400/30 dark:bg-purple-500/15 dark:text-purple-200"
              : "border border-transparent text-ink-500 hover:border-slate-200 hover:bg-slate-50 hover:text-ink-800 dark:text-ink-300 dark:hover:border-ink-300 dark:hover:bg-ink-800 dark:hover:text-white"
          }`}
        >
          <Users size={15} /> Managerial Round
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("hr")}
          aria-pressed={activeTab === "hr"}
          className={`flex min-w-fit items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-semibold transition-all sm:px-4 ${
            activeTab === "hr"
              ? "border border-amber-200 bg-amber-50 text-amber-800 shadow-2xs dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-200"
              : "border border-transparent text-ink-500 hover:border-slate-200 hover:bg-slate-50 hover:text-ink-800 dark:text-ink-300 dark:hover:border-ink-300 dark:hover:bg-ink-800 dark:hover:text-white"
          }`}
        >
          <Briefcase size={15} /> HR & Culture Round
        </button>
      </div>
      </section>

      {/* Round Header Summary */}
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 px-1 text-xs text-ink-500">
        <span>
          Showing <strong>{displayedQuestions.length} essential questions</strong> specifically tailored for <strong>{effectiveRole}</strong>
        </span>
        <span className="text-[11px] font-semibold text-signal-700">Interactive Model Answers & Timers Included ✓</span>
      </div>

      {/* Question Cards List */}
      <div className="space-y-4">
        {interviewQuery.isLoading ? (
          <div className="rounded-xl border border-ink-100 bg-white p-8 text-center text-sm text-ink-500">
            Preparing role-specific questions for {effectiveRole}…
          </div>
        ) : interviewQuery.isError ? (
          <div className="rounded-xl border border-alert-600/20 bg-alert-600/5 p-6 text-center">
            <p className="text-sm font-semibold text-alert-700">Interview questions could not be loaded.</p>
            <p className="text-xs text-ink-600 mt-1">
              Generated and curated questions are unavailable. Please try again; your selected role is unchanged.
            </p>
            <button
              onClick={() => void interviewQuery.refetch()}
              className="mt-3 rounded-lg bg-ink-950 px-3 py-1.5 text-xs font-semibold text-white hover:bg-ink-800"
            >
              Try again
            </button>
          </div>
        ) : displayedQuestions.length === 0 ? (
          <div className="rounded-xl border border-ink-100 bg-white p-6 text-center text-sm text-ink-500">
            No questions are available for this round yet. Choose another round or try generating the questions again.
          </div>
        ) : (
          <>
          {interviewQuery.data?.usedCuratedFallback && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Showing curated questions because personalized generation is temporarily unavailable.
            </p>
          )}
          {displayedQuestions.map((q, idx) => {
          const qKey = `${effectiveRole}_${activeTab}_${q.question}`;
          return (
            <QuestionCard
              key={idx}
              q={q}
              index={idx}
              role={effectiveRole}
              isMastered={!!masteredMap[qKey]}
              isBookmarked={!!bookmarkMap[qKey]}
              onToggleMastered={() => toggleMastered(qKey)}
              onToggleBookmarked={() => toggleBookmarked(qKey)}
            />
          );
          })}
          </>
        )}
      </div>

      {/* Free Mock Interview Practice Platforms */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.04)] sm:p-5">
        <h3 className="mb-1 flex items-center gap-2 font-display text-base font-bold text-ink-900">
          <Video size={18} className="text-signal-600" /> Free Mock Interview Practice Platforms
        </h3>
        <p className="mb-4 text-xs leading-relaxed text-ink-500">
          Practice live technical coding and behavioral mock interviews for free with peer candidates and engineers.
        </p>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {MOCK_PLATFORMS.map((plat, index) => {
            const PlatformIcon = MOCK_PLATFORM_ICONS[index];
            return (
              <article
                key={plat.name}
                className="group flex min-h-44 flex-col rounded-xl border border-slate-200 bg-slate-50/70 p-4 transition-all hover:-translate-y-0.5 hover:border-signal-500/35 hover:bg-white hover:shadow-md"
              >
                <div className="mb-3 flex items-start justify-between gap-2">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-signal-700 shadow-2xs">
                    <PlatformIcon size={17} />
                  </span>
                  <span className="rounded-full border border-signal-500/20 bg-signal-500/5 px-2 py-1 text-[9px] font-semibold text-signal-700">
                    {plat.tag}
                  </span>
                </div>
                <h4 className="text-sm font-bold text-ink-900">{plat.name}</h4>
                <p className="mt-1 flex-1 text-[11px] leading-relaxed text-ink-500">{plat.desc}</p>
                <a
                  href={plat.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-flex min-h-9 items-center justify-center gap-1.5 rounded-lg bg-signal-600 px-3 py-2 text-[11px] font-semibold text-white shadow-2xs transition-colors hover:bg-signal-700"
                >
                  Practice on {plat.name}
                  <ArrowUpRight size={12} />
                </a>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
