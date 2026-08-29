import { useState, useMemo, useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  MessageCircleQuestion, ExternalLink, Sparkles,
  ChevronDown, ChevronUp, AlertTriangle, Lightbulb,
  Video, Code2, Users, Briefcase, Star, CheckCircle2,
  Timer, Play, RotateCcw, Bot,
} from "lucide-react";
import { getProfile } from "../../lib/profile";
import { type InterviewQuestion } from "../../lib/interview";
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

import {
  FULL_STACK_QUESTIONS,
  BACKEND_QUESTIONS,
  FRONTEND_QUESTIONS,
  DATA_SCIENCE_QUESTIONS,
  DEVOPS_QUESTIONS,
  CORE_SWE_QUESTIONS,
} from "./interviewRoleData";

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
    <div className="p-3.5 bg-ink-50 rounded-xl border border-ink-100 space-y-2 mt-2">
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
    <div className={`rounded-xl border transition-all ${
      isMastered
        ? "border-signal-500/40 bg-white shadow-xs"
        : "border-ink-100 bg-white shadow-xs hover:shadow-md"
    } p-5`}>
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider border ${badgeStyle}`}>
            {roundName}
          </span>
          <span className="text-[11px] text-ink-400 font-mono">Q{index + 1}</span>
          <span className="text-[11px] text-ink-500 font-medium hidden sm:inline">• {role}</span>
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
            className={`p-1.5 rounded-lg transition-colors ${
              isBookmarked
                ? "text-amber-500 bg-amber-500/10"
                : "text-ink-400 hover:text-amber-500 hover:bg-ink-100"
            }`}
            title={isBookmarked ? "Remove Bookmark" : "Bookmark for Revision"}
          >
            <Star size={14} className={isBookmarked ? "fill-amber-500" : ""} />
          </button>

          {/* Mastered Checkbox Button */}
          <button
            onClick={onToggleMastered}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
              isMastered
                ? "bg-signal-500 text-white shadow-2xs"
                : "bg-ink-100 text-ink-700 hover:bg-ink-200"
            }`}
            title={isMastered ? "Mark as Pending" : "Mark as Mastered"}
          >
            <CheckCircle2 size={13} />
            <span>{isMastered ? "Mastered" : "Mark Done"}</span>
          </button>
        </div>
      </div>

      <h3 className="text-sm font-semibold text-ink-900 mb-2 leading-relaxed">
        {q.question}
      </h3>

      {q.star_hint && (
        <div className="rounded-lg bg-ink-50/80 p-3 mb-3 border border-ink-100/60">
          <p className="text-xs font-semibold text-ink-700 mb-0.5 flex items-center gap-1.5">
            <Sparkles size={12} className="text-signal-600" /> Focus Strategy:
          </p>
          <p className="text-xs text-ink-600 leading-relaxed">{q.star_hint}</p>
        </div>
      )}

      {/* Action Buttons: Expand Answer & Practice Timer */}
      <div className="flex flex-col sm:flex-row gap-2 mt-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex-1 flex items-center justify-between px-3.5 py-2 rounded-lg bg-ink-50 hover:bg-ink-100 text-ink-800 text-xs font-semibold transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <Lightbulb size={14} className="text-amber-500" />
            {expanded ? "Hide Answer Strategy" : "💡 How to Answer & Sample Model Response"}
          </span>
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        <button
          onClick={() => setShowPracticeTimer(!showPracticeTimer)}
          className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-ink-50 hover:bg-ink-100 text-ink-700 text-xs font-medium transition-colors"
          title="Practice answering in 2 minutes"
        >
          <Timer size={13} className="text-signal-500" />
          <span>{showPracticeTimer ? "Hide Timer" : "⏱️ Practice (2m)"}</span>
        </button>
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

      {/* Ask Copilot for Detailed Information & Presentation Strategy Button */}
      <Link
        to={`/copilot?role=${encodeURIComponent(role)}&category=${encodeURIComponent(q.category)}&prompt=${encodeURIComponent(`For the interview question: "${q.question}" (in a ${roundName} for ${role}):\n\nPlease provide detailed guidance on:\n1. How to approach and structure the answer\n2. How to present and communicate key points effectively\n3. Key technical/architectural concepts or STAR talking points to mention\n4. What mistakes or red flags to avoid`)}`}
        className="w-full mt-3 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-signal-500/10 hover:bg-signal-500/20 text-signal-800 text-xs font-bold transition-all border border-signal-500/20"
      >
        <Bot size={14} className="text-signal-600" />
        <span>Ask Copilot for detailed information & how to present ↗</span>
      </Link>
    </div>
  );
}

export function Interview() {
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });

  const defaultRole = profile?.target_roles?.[0] || "Full Stack Developer";
  const [selectedRole, setSelectedRole] = useState<string>(defaultRole);
  const [activeTab, setActiveTab] = useState<"technical" | "managerial" | "hr">("technical");
  const [filterView, setFilterView] = useState<"all" | "bookmarked" | "pending">("all");

  const effectiveRole = selectedRole || defaultRole;

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

  // Resolve role-specific questions
  const roleBank = useMemo(() => {
    const lower = effectiveRole.toLowerCase();
    if (lower.includes("frontend") || lower.includes("react") || lower.includes("ui") || lower.includes("vue") || lower.includes("angular")) {
      return FRONTEND_QUESTIONS;
    }
    if (lower.includes("backend") || lower.includes("node") || lower.includes("python") || lower.includes("java") || lower.includes("api") || lower.includes("golang")) {
      return BACKEND_QUESTIONS;
    }
    if (lower.includes("data") || lower.includes("machine learning") || lower.includes("ai") || lower.includes("ml") || lower.includes("analyst")) {
      return DATA_SCIENCE_QUESTIONS;
    }
    if (lower.includes("devops") || lower.includes("cloud") || lower.includes("sre") || lower.includes("infra") || lower.includes("kubernetes")) {
      return DEVOPS_QUESTIONS;
    }
    if (lower.includes("full stack") || lower.includes("fullstack") || lower.includes("web developer")) {
      return FULL_STACK_QUESTIONS;
    }
    return CORE_SWE_QUESTIONS;
  }, [effectiveRole]);

  const currentQuestions = useMemo(() => {
    return roleBank[activeTab] || roleBank.technical;
  }, [roleBank, activeTab]);

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

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <MessageCircleQuestion size={24} className="text-signal-600" />
          <h1 className="font-display text-2xl text-ink-900">Interview Preparation</h1>
        </div>
        <p className="text-ink-500 text-sm">
          Job-role specific interview questions. Master the Top 20 essential questions for your chosen discipline across Technical, Managerial, and HR rounds with model answers, 2-minute mock timers, and free peer practice links.
        </p>
      </div>

      {/* Target Role Dropdown Card */}
      <div className="bg-white rounded-xl border border-ink-100 p-5 shadow-xs">
        <RoleDropdownSelector
          label="Select Target Job Role:"
          selectedRole={selectedRole}
          onRoleChange={setSelectedRole}
          roles={ALL_JOB_ROLES}
          includeAllOption={false}
          helperText="Select or type any job role to load specialized technical, managerial, and HR interview questions."
        />
      </div>

      {/* Mastery Progress Card */}
      <div className="bg-white rounded-xl border border-ink-100 p-4 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2.5">
          <div>
            <span className="text-xs font-bold text-ink-900 flex items-center gap-1.5">
              <CheckCircle2 size={15} className="text-signal-600" />
              Round Readiness: {masteredCount} / {currentQuestions.length} Questions Mastered ({Math.round((masteredCount / (currentQuestions.length || 1)) * 100)}%)
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <button
              onClick={() => setFilterView("all")}
              className={`px-2.5 py-1 rounded-md transition-colors font-medium ${
                filterView === "all"
                  ? "bg-ink-950 text-white"
                  : "bg-ink-50 text-ink-600 hover:bg-ink-100"
              }`}
            >
              All ({currentQuestions.length})
            </button>
            <button
              onClick={() => setFilterView("bookmarked")}
              className={`px-2.5 py-1 rounded-md transition-colors font-medium flex items-center gap-1 ${
                filterView === "bookmarked"
                  ? "bg-amber-500 text-white"
                  : "bg-ink-50 text-ink-600 hover:bg-ink-100"
              }`}
            >
              <Star size={11} className={bookmarkCount > 0 ? "fill-amber-400" : ""} />
              Saved ({bookmarkCount})
            </button>
            <button
              onClick={() => setFilterView("pending")}
              className={`px-2.5 py-1 rounded-md transition-colors font-medium ${
                filterView === "pending"
                  ? "bg-ink-950 text-white"
                  : "bg-ink-50 text-ink-600 hover:bg-ink-100"
              }`}
            >
              Pending ({currentQuestions.length - masteredCount})
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full h-2 rounded-full bg-ink-100 overflow-hidden">
          <div
            className="h-full bg-signal-500 rounded-full transition-all duration-300"
            style={{ width: `${(masteredCount / (currentQuestions.length || 1)) * 100}%` }}
          />
        </div>
      </div>

      {/* Categorized Round Tabs (Technical, Managerial, HR) */}
      <div className="flex border-b border-ink-100 gap-2 pb-1">
        <button
          onClick={() => setActiveTab("technical")}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-all flex items-center gap-1.5 ${
            activeTab === "technical"
              ? "border-b-2 border-signal-600 text-signal-700 bg-signal-500/5 shadow-2xs"
              : "text-ink-500 hover:text-ink-800"
          }`}
        >
          <Code2 size={14} /> 💻 Technical Round (Top 20)
        </button>
        <button
          onClick={() => setActiveTab("managerial")}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-all flex items-center gap-1.5 ${
            activeTab === "managerial"
              ? "border-b-2 border-purple-600 text-purple-700 bg-purple-500/5 shadow-2xs"
              : "text-ink-500 hover:text-ink-800"
          }`}
        >
          <Users size={14} /> 👔 Managerial Round (Top 20)
        </button>
        <button
          onClick={() => setActiveTab("hr")}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-all flex items-center gap-1.5 ${
            activeTab === "hr"
              ? "border-b-2 border-amber-600 text-amber-700 bg-amber-500/5 shadow-2xs"
              : "text-ink-500 hover:text-ink-800"
          }`}
        >
          <Briefcase size={14} /> 🤝 HR & Culture Round (Top 20)
        </button>
      </div>

      {/* Round Header Summary */}
      <div className="flex items-center justify-between px-1 text-xs text-ink-500">
        <span>
          Showing <strong>{displayedQuestions.length} essential questions</strong> specifically tailored for <strong>{effectiveRole}</strong>
        </span>
        <span className="text-[11px] font-semibold text-signal-700">Interactive Model Answers & Timers Included ✓</span>
      </div>

      {/* Question Cards List */}
      <div className="space-y-4">
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
      </div>

      {/* Free Mock Interview Practice Platforms */}
      <div className="rounded-xl border border-ink-100 bg-white p-5 shadow-xs">
        <h3 className="font-display text-base text-ink-900 mb-1 flex items-center gap-2">
          <Video size={18} className="text-signal-600" /> Free Mock Interview Practice Platforms
        </h3>
        <p className="text-xs text-ink-500 mb-4">
          Practice live technical coding and behavioral mock interviews for free with peer candidates and engineers.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {MOCK_PLATFORMS.map((plat) => (
            <a
              key={plat.name}
              href={plat.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-3.5 rounded-lg border border-ink-100 bg-ink-50/40 hover:bg-white hover:border-signal-500 hover:shadow-xs transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs text-ink-900 group-hover:text-signal-700">{plat.name}</span>
                  <span className="text-[10px] font-semibold text-signal-700 bg-signal-500/10 px-2 py-0.5 rounded-full">
                    {plat.tag}
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-snug">{plat.desc}</p>
              </div>
              <span className="text-[11px] font-semibold text-signal-600 mt-2 flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                Practice on {plat.name} <ExternalLink size={10} />
              </span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
