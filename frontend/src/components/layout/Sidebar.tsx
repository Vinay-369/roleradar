import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, FileText, Copy, Target,
  Briefcase, GraduationCap, Bookmark,
  Map, MessageCircleQuestion, Bot, X,
} from "lucide-react";

type NavItem = { label: string; to: string; icon: React.ComponentType<{ size?: number; className?: string }> };
type NavGroup = { label: string; items: NavItem[] };

const groups: NavGroup[] = [
  { label: "", items: [{ label: "Dashboard", to: "/dashboard", icon: LayoutDashboard }] },
  {
    label: "Resume",
    items: [
      { label: "Master Resume", to: "/resume/master", icon: FileText },
      { label: "Tailored Versions", to: "/resume/versions", icon: Copy },
    ],
  },
  {
    label: "Opportunities",
    items: [
      { label: "Jobs For You", to: "/opportunities/jobs", icon: Briefcase },
      { label: "Internships", to: "/opportunities/internships", icon: GraduationCap },
      { label: "Saved", to: "/opportunities/saved", icon: Bookmark },
    ],
  },
  {
    label: "Career Growth",
    items: [
      { label: "Skill Gaps", to: "/growth/skill-gaps", icon: Target },
      { label: "Learning Roadmap", to: "/growth/roadmap", icon: Map },
      { label: "Interview Preparation", to: "/growth/interview", icon: MessageCircleQuestion },
    ],
  },
  {
    label: "AI Strategist",
    items: [
      { label: "Career Copilot", to: "/copilot", icon: Bot },
    ],
  },
];

export function Sidebar({
  mobileOpen = false,
  onClose,
}: {
  mobileOpen?: boolean;
  onClose?: () => void;
}) {
  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 md:hidden transition-opacity"
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 w-64 shrink-0 bg-ink-950 text-ink-100 h-screen overflow-y-auto px-4 py-6 flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 ${
          mobileOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className="px-2 mb-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-md bg-gradient-to-br from-signal-400 to-signal-600 flex items-center justify-center shrink-0">
              <Target size={16} className="text-white" strokeWidth={2.5} />
            </div>
            <span className="font-display text-lg tracking-tight text-white">
              Role<span className="text-signal-400">Radar</span>
            </span>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded-md text-ink-400 hover:text-white hover:bg-ink-900 md:hidden transition-colors"
              aria-label="Close menu"
            >
              <X size={18} />
            </button>
          )}
        </div>

        <nav className="flex-1 space-y-6">
          {groups.map((group, gIdx) => (
            <div key={gIdx}>
              {group.label && (
                <p className="px-2 mb-2 text-[10px] font-bold uppercase tracking-wider text-ink-500">
                  {group.label}
                </p>
              )}
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        onClick={onClose}
                        className={({ isActive }) =>
                          `group flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium transition-all ${
                            isActive
                              ? "bg-ink-800 text-white font-semibold shadow-2xs"
                              : "text-ink-300 hover:text-white hover:bg-ink-900"
                          }`
                        }
                      >
                        {({ isActive }) => (
                          <>
                            <Icon size={16} className={isActive ? "text-signal-400" : "text-ink-500 group-hover:text-ink-200"} />
                            {item.label}
                          </>
                        )}
                      </NavLink>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}
