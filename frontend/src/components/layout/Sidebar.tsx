import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, FileText, Copy, Target,
  Briefcase, GraduationCap, ClipboardCheck,
  Map, MessageCircleQuestion, Bot, X, Bookmark, Settings, Sun, Moon,
  PanelLeftClose, PanelLeftOpen,
} from "lucide-react";
import { useTheme } from "../../context/ThemeContext";

type NavItem = { label: string; to: string; icon: React.ComponentType<{ size?: number; className?: string }> };
type NavGroup = { label: string; items: NavItem[] };

const groups: NavGroup[] = [
  { label: "", items: [{ label: "Dashboard", to: "/dashboard", icon: LayoutDashboard }] },
  {
    label: "Explore",
    items: [
      { label: "Jobs For You", to: "/opportunities/jobs", icon: Briefcase },
      { label: "Internships", to: "/opportunities/internships", icon: GraduationCap },
      { label: "Saved Opportunities", to: "/opportunities/saved", icon: Bookmark },
      { label: "Paste External JD", to: "/resume/tailor-custom", icon: FileText },
    ],
  },
  {
    label: "Career Growth",
    items: [
      { label: "Skill Map & Gaps", to: "/growth/skill-gaps", icon: Target },
      { label: "Learning Roadmap", to: "/growth/roadmap", icon: Map },
      { label: "Interview Preparation", to: "/growth/interview", icon: MessageCircleQuestion },
    ],
  },
  {
    label: "Resume",
    items: [
      { label: "Master Resume", to: "/resume/master", icon: FileText },
      { label: "Tailored Resumes", to: "/resume/versions", icon: Copy },
    ],
  },
  {
    label: "Tracking",
    items: [
      { label: "Applications Tracker", to: "/applications", icon: ClipboardCheck },
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
  collapsed = false,
  onToggleCollapsed,
}: {
  mobileOpen?: boolean;
  onClose?: () => void;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
}) {
  const { theme, toggleTheme } = useTheme();

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
        className={`fixed md:static inset-y-0 left-0 z-50 w-64 shrink-0 bg-ink-950 text-ink-100 h-screen overflow-y-auto px-4 py-6 flex flex-col transition-all duration-200 ease-in-out md:translate-x-0 ${
          collapsed ? "md:w-16 md:px-2" : ""
        } ${
          mobileOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className={`px-2 mb-8 flex items-center ${collapsed ? "md:flex-col md:items-end md:gap-2" : "justify-between"}`}>
          <div className={`flex items-center gap-2 ${collapsed ? "md:w-full md:justify-center" : ""}`}>
            <div className="w-8 h-8 rounded-md bg-gradient-to-br from-signal-400 to-signal-600 flex items-center justify-center shrink-0">
              <Target size={16} className="text-white" strokeWidth={2.5} />
            </div>
            <span className={`font-display text-lg tracking-tight text-white ${collapsed ? "md:hidden" : ""}`}>
              Role<span className="text-signal-400">Radar</span>
            </span>
          </div>
          {onToggleCollapsed && !collapsed && (
            <button
              type="button"
              onClick={onToggleCollapsed}
              className="hidden md:inline-flex items-center justify-center w-7 h-7 shrink-0 rounded-md text-ink-400 hover:text-white hover:bg-ink-900 transition-colors"
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <PanelLeftClose size={16} />
            </button>
          )}
          {onToggleCollapsed && collapsed && (
            <button
              type="button"
              onClick={onToggleCollapsed}
              className="hidden md:inline-flex items-center justify-center w-7 h-7 shrink-0 rounded-md text-ink-400 hover:text-white hover:bg-ink-900 transition-colors"
              aria-label="Expand sidebar"
              title="Expand sidebar"
            >
              <PanelLeftOpen size={16} />
            </button>
          )}
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

        <nav className={`flex-1 space-y-6 ${collapsed ? "md:space-y-3" : ""}`}>
          {groups.map((group, gIdx) => (
            <div key={gIdx} className={collapsed ? "md:space-y-1" : ""}>
              {group.label && !collapsed && (
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
                            collapsed ? "md:justify-center md:px-0" : ""} ${
                            isActive
                              ? "bg-ink-800 text-white font-semibold shadow-2xs"
                              : "text-ink-300 hover:text-white hover:bg-ink-900"
                          }`
                        }
                      >
                        {({ isActive }) => (
                          <>
                            <Icon size={16} className={isActive ? "text-signal-400" : "text-ink-500 group-hover:text-ink-200"} />
                            <span className={collapsed ? "md:hidden" : ""}>{item.label}</span>
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

        <div className={`mt-6 border-t border-ink-800 pt-4 space-y-1 ${collapsed ? "md:mt-3 md:pt-3" : ""}`}>
          <NavLink
            to="/settings"
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium transition-all ${collapsed ? "md:justify-center md:px-0" : ""} ${
                isActive
                  ? "bg-ink-800 text-white font-semibold"
                  : "text-ink-300 hover:text-white hover:bg-ink-900"
              }`
            }
          >
            <Settings size={16} className="text-ink-400" />
            <span className={collapsed ? "md:hidden" : ""}>Profile & Settings</span>
          </NavLink>
          <button
            type="button"
            onClick={toggleTheme}
            className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium text-ink-300 hover:text-white hover:bg-ink-900 transition-colors ${collapsed ? "md:justify-center md:px-0" : ""}`}
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          >
            {theme === "light" ? <Moon size={16} className="text-ink-400" /> : <Sun size={16} className="text-amber-400" />}
            <span className={collapsed ? "md:hidden" : ""}>{theme === "light" ? "Dark mode" : "Light mode"}</span>
          </button>
        </div>
      </aside>
    </>
  );
}
