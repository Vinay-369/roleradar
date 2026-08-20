import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, FileText, Copy, Target,
  Briefcase, GraduationCap, Bookmark, ListChecks, Kanban,
  Map, MessageCircleQuestion, Bot, Settings as SettingsIcon, LogOut, X,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

type NavItem = { label: string; to: string; icon: React.ComponentType<{ size?: number; className?: string }> };
type NavGroup = { label: string; items: NavItem[] };

const groups: NavGroup[] = [
  { label: "", items: [{ label: "Dashboard", to: "/dashboard", icon: LayoutDashboard }] },
  {
    label: "Resume",
    items: [
      { label: "Master Resume", to: "/resume/master", icon: FileText },
      { label: "Skill Gaps", to: "/growth/skill-gaps", icon: Target },
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
    label: "Applications",
    items: [
      { label: "Application Queue", to: "/applications/queue", icon: ListChecks },
      { label: "Application Tracker", to: "/applications/tracker", icon: Kanban },
    ],
  },
  {
    label: "Career Growth",
    items: [
      { label: "Learning Roadmap", to: "/growth/roadmap", icon: Map },
      { label: "Interview Preparation", to: "/growth/interview", icon: MessageCircleQuestion },
    ],
  },
  { label: "", items: [{ label: "Career Copilot", to: "/copilot", icon: Bot }] },
  { label: "", items: [{ label: "Settings", to: "/settings", icon: SettingsIcon }] },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ mobileOpen = false, onClose }: SidebarProps) {
  const { user, logout } = useAuth();

  const handleNavClick = () => {
    if (onClose) {
      onClose();
    }
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
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

        <nav className="space-y-6 flex-1">
          {groups.map((group, i) => (
            <div key={i}>
              {group.label && (
                <p className="px-2 mb-2 text-xs font-medium uppercase tracking-wider text-ink-500">
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
                        onClick={handleNavClick}
                        className={({ isActive }) =>
                          `group flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-all duration-150 relative ${
                            isActive
                              ? "bg-ink-800 text-white"
                              : "text-ink-300 hover:bg-ink-900 hover:text-white hover:translate-x-0.5"
                          }`
                        }
                      >
                        {({ isActive }) => (
                          <>
                            {isActive && (
                              <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-signal-400" />
                            )}
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

        <div className="px-2 pt-4 border-t border-ink-800">
          {user && <p className="text-xs text-ink-500 mb-2 truncate">{user.email}</p>}
          <button
            onClick={logout}
            className="flex items-center gap-2 text-sm text-ink-300 hover:text-white transition-colors"
          >
            <LogOut size={14} />
            Log out
          </button>
        </div>
      </aside>
    </>
  );
}
