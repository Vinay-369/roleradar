import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  LayoutDashboard,
  FileText,
  Copy,
  Briefcase,
  GraduationCap,
  Bookmark,
  Map,
  MessageCircleQuestion,
  Bot,
  User,
  Sparkles,
  ArrowRight,
  X,
  Target,
} from "lucide-react";

interface CommandItem {
  id: string;
  title: string;
  category: "Navigation" | "Resume & Tailoring" | "Opportunities" | "Career Growth";
  path: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  shortcut?: string;
  keywords?: string[];
}

const COMMANDS: CommandItem[] = [
  { id: "dash", title: "Dashboard Overview", category: "Navigation", path: "/dashboard", icon: LayoutDashboard, keywords: ["home", "stats", "metrics"] },
  { id: "master", title: "Master Resume & ATS Audit", category: "Resume & Tailoring", path: "/resume/master", icon: FileText, keywords: ["upload", "ats", "parse", "cv"] },
  { id: "versions", title: "Tailored Resume Versions", category: "Resume & Tailoring", path: "/resume/versions", icon: Copy, keywords: ["tailor", "truth guard", "pdf", "docx"] },
  { id: "custom-tailor", title: "Custom Resume Tailoring", category: "Resume & Tailoring", path: "/resume/tailor-custom", icon: Sparkles, keywords: ["jd", "custom", "tailor"] },
  { id: "jobs", title: "Jobs For You (Full-Time)", category: "Opportunities", path: "/opportunities/jobs", icon: Briefcase, keywords: ["matches", "work", "apply"] },
  { id: "internships", title: "Internships & Early Career", category: "Opportunities", path: "/opportunities/internships", icon: GraduationCap, keywords: ["fresher", "intern", "college"] },
  { id: "saved", title: "Saved Opportunities", category: "Opportunities", path: "/opportunities/saved", icon: Bookmark, keywords: ["bookmarks", "starred", "favorites", "saved", "apply"] },
  { id: "skill-gaps", title: "Skill Gap Analysis", category: "Career Growth", path: "/growth/skill-gaps", icon: Target, keywords: ["missing", "skills", "audit"] },
  { id: "roadmap", title: "4-Sprint Learning Roadmap", category: "Career Growth", path: "/growth/roadmap", icon: Map, keywords: ["learn", "courses", "sprints"] },
  { id: "interview", title: "Interview Question Simulator", category: "Career Growth", path: "/growth/interview", icon: MessageCircleQuestion, keywords: ["prep", "questions", "star", "mock"] },
  { id: "copilot", title: "Career Copilot AI Mentor", category: "Career Growth", path: "/copilot", icon: Bot, keywords: ["chat", "ai", "advisor", "gpt"] },
  { id: "profile", title: "User Profile & Preferences", category: "Navigation", path: "/settings", icon: User, keywords: ["profile", "account", "settings", "preferences"] },
];

export function CommandPalette({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filtered = COMMANDS.filter((cmd) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    const matchTitle = cmd.title.toLowerCase().includes(q);
    const matchCat = cmd.category.toLowerCase().includes(q);
    const matchKeywords = cmd.keywords?.some((k) => k.toLowerCase().includes(q));
    return matchTitle || matchCat || matchKeywords;
  });

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleSelect = (cmd: CommandItem) => {
    onClose();
    navigate(cmd.path);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (filtered.length || 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filtered.length) % (filtered.length || 1));
    } else if (e.key === "Enter" && filtered[selectedIndex]) {
      e.preventDefault();
      handleSelect(filtered[selectedIndex]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-ink-950/60 backdrop-blur-xs transition-opacity"
        aria-hidden="true"
      />

      {/* Palette Dialog */}
      <div className="relative w-full max-w-xl rounded-2xl border border-ink-100 bg-white shadow-2xl overflow-hidden animate-scale-in flex flex-col max-h-[80vh]">
        {/* Search Header */}
        <div className="flex items-center px-4 py-3.5 border-b border-ink-100 bg-ink-50/50">
          <Search size={18} className="text-ink-400 shrink-0 mr-3" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command, page, or keyword..."
            className="flex-1 bg-transparent border-0 text-sm text-ink-900 placeholder:text-ink-400 focus:outline-hidden focus:ring-0 p-0"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="p-1 rounded-md text-ink-400 hover:text-ink-700 transition-colors mr-2"
            >
              <X size={14} />
            </button>
          )}
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-ink-200/80 text-ink-600 font-semibold shrink-0">
            ESC
          </span>
        </div>

        {/* Command List */}
        <div className="overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-xs text-ink-500">
              No matching commands or pages found for &ldquo;{query}&rdquo;
            </div>
          ) : (
            filtered.map((cmd, idx) => {
              const Icon = cmd.icon;
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={cmd.id}
                  onClick={() => handleSelect(cmd)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-colors ${
                    isSelected ? "bg-signal-500/10 text-signal-900 font-semibold" : "text-ink-700 hover:bg-ink-50"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`p-1.5 rounded-lg shrink-0 ${
                        isSelected ? "bg-signal-500/20 text-signal-700" : "bg-ink-100 text-ink-600"
                      }`}
                    >
                      <Icon size={16} />
                    </div>
                    <div className="truncate">
                      <p className="text-xs font-bold leading-snug truncate">{cmd.title}</p>
                      <p className="text-[10px] text-ink-400 font-normal leading-tight">{cmd.category}</p>
                    </div>
                  </div>

                  <ArrowRight
                    size={13}
                    className={`transition-opacity shrink-0 ml-2 ${
                      isSelected ? "text-signal-600 opacity-100" : "opacity-0"
                    }`}
                  />
                </div>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2.5 bg-ink-50 border-t border-ink-100 flex items-center justify-between text-[11px] text-ink-400">
          <div className="flex items-center gap-2">
            <span>Navigation:</span>
            <kbd className="px-1.5 py-0.5 rounded bg-white border border-ink-200 text-[10px] font-mono text-ink-600 shadow-2xs">↑</kbd>
            <kbd className="px-1.5 py-0.5 rounded bg-white border border-ink-200 text-[10px] font-mono text-ink-600 shadow-2xs">↓</kbd>
            <kbd className="px-1.5 py-0.5 rounded bg-white border border-ink-200 text-[10px] font-mono text-ink-600 shadow-2xs">↵</kbd>
          </div>
          <span>RoleRadar Command Center</span>
        </div>
      </div>
    </div>
  );
}
