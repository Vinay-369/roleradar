import { useState, useEffect, useRef } from "react";
import { Outlet, useLocation, useNavigate, Link } from "react-router-dom";
import {
  Menu, Target, ArrowLeft, LogOut,
  User, Bot
} from "lucide-react";
import { Sidebar } from "./Sidebar";
import { useAuth } from "../../context/AuthContext";

function getPageTitle(pathname: string): string {
  if (pathname.startsWith("/dashboard")) return "Dashboard";
  if (pathname.startsWith("/resume/master")) return "Master Resume";
  if (pathname.startsWith("/growth/skill-gaps")) return "Skill Gaps";
  if (pathname.startsWith("/resume/versions")) return "Tailored Versions";
  if (pathname.startsWith("/resume/tailor-custom")) return "Custom Tailoring";
  if (pathname.startsWith("/resume/tailor")) return "Resume Tailor Review";
  if (pathname.startsWith("/opportunities/jobs")) return "Jobs For You";
  if (pathname.startsWith("/opportunities/internships")) return "Internships";
  if (pathname.startsWith("/opportunities/saved")) return "Saved";
  if (pathname.startsWith("/opportunities/job")) return "Opportunity Details";
  if (pathname.startsWith("/growth/roadmap")) return "Learning Roadmap";
  if (pathname.startsWith("/growth/interview")) return "Interview Preparation";
  if (pathname.startsWith("/copilot")) return "Career Copilot";
  if (pathname.startsWith("/settings") || pathname.startsWith("/profile")) return "Profile";
  return "Overview";
}

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isHome = location.pathname === "/" || location.pathname === "/dashboard";
  const pageTitle = getPageTitle(location.pathname);

  // Click outside to close user dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setUserDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleBack = () => {
    if (window.history.length > 1 && !isHome) {
      navigate(-1);
    } else {
      navigate("/dashboard");
    }
  };

  const userInitials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user?.email?.slice(0, 2).toUpperCase() || "RR";

  return (
    <div className="flex h-screen overflow-hidden flex-col md:flex-row bg-ink-50">
      {/* Mobile Top Header Bar */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 bg-ink-950 text-ink-100 border-b border-ink-800 shrink-0 z-30">
        <div className="flex items-center gap-2.5">
          {!isHome && (
            <button
              onClick={handleBack}
              className="p-1 rounded-lg text-ink-300 hover:text-white hover:bg-ink-900 transition-colors"
              aria-label="Go back"
              title="Go back"
            >
              <ArrowLeft size={18} />
            </button>
          )}
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-signal-400 to-signal-600 flex items-center justify-center shrink-0">
              <Target size={15} className="text-white" strokeWidth={2.5} />
            </div>
            <span className="font-display text-base font-semibold tracking-tight text-white">
              Role<span className="text-signal-400">Radar</span>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="p-1.5 rounded-lg text-ink-300 hover:text-white hover:bg-ink-900 transition-colors"
            aria-label="Open navigation menu"
          >
            <Menu size={20} />
          </button>
        </div>
      </header>

      {/* Sidebar (Fixed drawer on mobile, static on desktop) */}
      <Sidebar
        mobileOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area with Universal Top Bar */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Desktop Top Navigation Bar */}
        <header className="hidden md:flex items-center justify-between px-8 py-3.5 bg-white border-b border-ink-100 shrink-0 z-20">
          {/* Left: Breadcrumbs & Back */}
          <div className="flex items-center gap-3">
            {!isHome ? (
              <button
                onClick={handleBack}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-ink-700 hover:text-ink-950 bg-ink-100 hover:bg-ink-200 transition-all shadow-2xs group"
                aria-label="Go back to previous page"
                title="Go back"
              >
                <ArrowLeft size={14} className="group-hover:-translate-x-0.5 transition-transform text-ink-500 group-hover:text-ink-950" />
                <span>Back</span>
              </button>
            ) : (
              <div className="flex items-center gap-1.5 text-xs text-ink-500 font-medium">
                <Target size={14} className="text-signal-600" />
                <span>Workspace</span>
              </div>
            )}

            <div className="h-4 w-px bg-ink-100" />

            <span className="text-xs font-bold text-ink-900 tracking-tight">
              {pageTitle}
            </span>
          </div>

          {/* Right: Copilot Shortcut & User Profile Avatar */}
          <div className="flex items-center gap-3">
            <Link
              to="/copilot"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-signal-700 bg-signal-500/10 hover:bg-signal-500/15 border border-signal-500/20 transition-colors"
              title="Open AI Career Copilot"
            >
              <Bot size={14} className="text-signal-600" />
              <span className="hidden lg:inline">AI Copilot</span>
            </Link>

            {/* Profile Avatar Button & Menu */}
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setUserDropdownOpen((prev) => !prev)}
                className="w-8 h-8 rounded-xl bg-gradient-to-br from-ink-800 to-ink-950 hover:from-ink-700 hover:to-ink-900 text-white flex items-center justify-center text-xs font-bold shadow-2xs transition-all hover:scale-105 active:scale-95 cursor-pointer focus:outline-hidden"
                title={user?.full_name || "Profile"}
                aria-label="Profile"
              >
                {userInitials}
              </button>

              {userDropdownOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-2xl border border-ink-100 bg-white p-2 shadow-xl animate-scale-in z-50">
                  <div className="px-3 py-2 border-b border-ink-50 mb-1">
                    <p className="text-xs font-bold text-ink-950 truncate">
                      {user?.full_name || "RoleRadar User"}
                    </p>
                    <p className="text-[11px] text-ink-500 truncate">{user?.email}</p>
                  </div>

                  <Link
                    to="/settings"
                    onClick={() => setUserDropdownOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-ink-700 hover:bg-ink-50 transition-colors"
                  >
                    <User size={14} className="text-ink-500" />
                    <span>Profile</span>
                  </Link>

                  <div className="h-px bg-ink-100 my-1" />

                  <button
                    type="button"
                    onClick={() => {
                      setUserDropdownOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-alert-700 hover:bg-alert-500/10 transition-colors"
                  >
                    <LogOut size={14} className="text-alert-600" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Scrollable Page Body */}
        <main className={`flex-1 ${location.pathname.startsWith("/copilot") ? "overflow-hidden p-0 bg-white" : "overflow-y-auto px-4 py-6 md:px-8 md:py-8 bg-ink-50"}`}>
          <div key={location.pathname} className={`${location.pathname.startsWith("/copilot") ? "h-full w-full" : "max-w-6xl mx-auto"} rr-page-transition`}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
