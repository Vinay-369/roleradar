import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Menu, Target } from "lucide-react";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden flex-col md:flex-row bg-ink-50">
      {/* Mobile Top Header Bar */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 bg-ink-950 text-ink-100 border-b border-ink-800 shrink-0 z-30">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-signal-400 to-signal-600 flex items-center justify-center shrink-0">
            <Target size={15} className="text-white" strokeWidth={2.5} />
          </div>
          <span className="font-display text-base font-semibold tracking-tight text-white">
            Role<span className="text-signal-400">Radar</span>
          </span>
        </div>
        <button
          onClick={() => setMobileMenuOpen(true)}
          className="p-1.5 rounded-lg text-ink-300 hover:text-white hover:bg-ink-900 transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu size={20} />
        </button>
      </header>

      {/* Sidebar (Fixed drawer on mobile, static on desktop) */}
      <Sidebar
        mobileOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8">
        <div key={location.pathname} className="max-w-6xl mx-auto rr-page-transition">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
