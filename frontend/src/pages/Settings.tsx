import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BriefcaseBusiness,
  Check,
  Clock3,
  Info,
  LogOut,
  Mail,
  MapPin,
  MonitorSmartphone,
  UserRound,
  Wallet,
} from "lucide-react";
import { apiClient } from "../lib/apiClient";
import { useAuth } from "../context/AuthContext";

type Profile = {
  category: string;
  target_roles: string[];
  min_lpa: number | null;
  min_stipend: number | null;
  internship_duration_months: number | null;
  preferred_locations: string[];
  remote_preference: string;
  internship_interested: boolean;
  career_brief: string | null;
  auto_apply_settings: { tier: string; min_match_score: number; max_per_day: number };
};

export function Settings() {
  const { user, logout } = useAuth();
  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: async () => (await apiClient.get<Profile | null>("/profile/me")).data,
  });
  const fullName = user?.full_name?.trim() || "RoleRadar Candidate";
  const initials = fullName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  const displayCategory = profile?.category.replaceAll("_", " ").toLowerCase();
  const accountType = displayCategory
    ? `${displayCategory.replace(/\b\w/g, (letter) => letter.toUpperCase())} account`
    : "Candidate account";
  const tier = profile?.auto_apply_settings.tier ?? "manual";
  const tierLabel = tier.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

  return (
    <div className="mx-auto w-full min-w-0 max-w-4xl space-y-6 pb-8">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-signal-700 dark:text-signal-300">Account settings</p>
        <h1 className="mt-1 font-display text-3xl font-bold tracking-tight text-ink-950 dark:text-white">Profile</h1>
        <p className="mt-1 text-sm text-ink-500 dark:text-slate-400">Manage your account and career preferences.</p>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-signal-500 to-indigo-600 text-xl font-bold text-white shadow-sm" aria-label={`${fullName} initials`}>
            {initials || <UserRound size={25} />}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="truncate font-display text-xl font-bold text-ink-950 dark:text-white">{fullName}</h2>
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <BriefcaseBusiness size={12} />
                {accountType}
              </span>
              {profile?.target_roles?.[0] && (
                <span className="max-w-full truncate text-xs text-ink-500 dark:text-slate-400">
                  Focus: {profile.target_roles[0]}
                </span>
              )}
            </div>
          </div>
          <Link to="/onboarding" className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-xs font-semibold text-ink-700 transition-colors hover:border-slate-400 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800">
            Edit Profile <ArrowRight size={14} />
          </Link>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-6">
        <div className="mb-4">
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink-500 dark:text-slate-400">Account</p>
          <h2 className="mt-1 text-base font-bold text-ink-900 dark:text-white">Account details</h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-700 dark:bg-slate-800">
            <div className="mb-2 flex items-center gap-2 text-[11px] font-medium text-ink-500 dark:text-slate-400"><UserRound size={14} /> Name</div>
            <p className="break-words text-sm font-semibold text-ink-900 dark:text-white">{fullName}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-700 dark:bg-slate-800">
            <div className="mb-2 flex items-center gap-2 text-[11px] font-medium text-ink-500 dark:text-slate-400"><Mail size={14} /> Email</div>
            <p className="break-words text-sm font-semibold text-ink-900 dark:text-white">{user?.email || "—"}</p>
          </div>
        </div>
      </section>

      {isLoading && (
        <div role="status" className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-ink-500 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
          Loading career preferences…
        </div>
      )}

      {profile && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink-500 dark:text-slate-400">Career preferences</p>
              <h2 className="mt-1 text-base font-bold text-ink-900 dark:text-white">Your opportunity criteria</h2>
            </div>
            <Link to="/onboarding" className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 px-3 text-xs font-semibold text-ink-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
              Edit preferences <ArrowRight size={13} />
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-700 dark:bg-slate-800">
              <p className="text-[11px] font-medium text-ink-500 dark:text-slate-400">Category</p>
              <p className="mt-1 text-sm font-semibold capitalize text-ink-900 dark:text-white">{profile.category.replaceAll("_", " ").toLowerCase()}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-700 dark:bg-slate-800">
              <p className="mb-2 text-[11px] font-medium text-ink-500 dark:text-slate-400">Target roles</p>
              <div className="flex flex-wrap gap-1.5">
                {profile.target_roles.length ? profile.target_roles.map((role) => (
                  <span key={role} className="rounded-full border border-signal-500/20 bg-signal-500/10 px-2.5 py-1 text-[11px] font-semibold text-signal-800 dark:text-signal-200">{role}</span>
                )) : <span className="text-sm text-ink-500 dark:text-slate-400">Not set</span>}
              </div>
            </div>
            {profile.category === "INTERNSHIP_SEEKER" ? (
              <>
                <PreferenceValue icon={Wallet} label="Minimum stipend" value={profile.min_stipend ? `₹${profile.min_stipend.toLocaleString()}/month` : "Not set"} />
                {profile.internship_duration_months && <PreferenceValue icon={Clock3} label="Preferred duration" value={`${profile.internship_duration_months} months`} />}
              </>
            ) : (
              <PreferenceValue icon={Wallet} label="Minimum compensation" value={profile.min_lpa ? `${profile.min_lpa} LPA` : "Not set"} />
            )}
            <PreferenceValue icon={MapPin} label="Preferred locations" value={profile.preferred_locations.length ? profile.preferred_locations.join(", ") : "Any location"} />
            <PreferenceValue icon={MonitorSmartphone} label="Work arrangement" value={profile.remote_preference || "Not set"} />
          </div>
        </section>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink-500 dark:text-slate-400">Smart Apply</p>
            <h2 className="mt-1 text-base font-bold text-ink-900 dark:text-white">Review-first application support</h2>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-[11px] font-bold text-indigo-700 dark:border-indigo-900 dark:bg-indigo-950/50 dark:text-indigo-300">
            <Check size={13} /> {tierLabel} tier
          </span>
        </div>
        <div className="mt-4 flex gap-3 rounded-xl border border-sky-200 bg-sky-50 p-3.5 text-sky-950 dark:border-sky-900 dark:bg-sky-950/30 dark:text-sky-100">
          <Info size={17} className="mt-0.5 shrink-0 text-sky-700 dark:text-sky-300" />
          <p className="text-xs leading-relaxed">
            RoleRadar prepares an application package for you to review. It never submits an application on your behalf. You can adjust this setting during onboarding.
          </p>
        </div>
      </section>

      <div className="flex justify-end border-t border-slate-200 pt-4 dark:border-slate-800">
        <button onClick={logout} className="inline-flex h-10 items-center gap-2 rounded-lg px-4 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/30">
          <LogOut size={15} />
          Log out
        </button>
      </div>
    </div>
  );
}

function PreferenceValue({ icon: Icon, label, value }: { icon: typeof Wallet; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center gap-2 text-[11px] font-medium text-ink-500 dark:text-slate-400">
        <Icon size={14} />
        {label}
      </div>
      <p className="mt-1 text-sm font-semibold text-ink-900 dark:text-white">{value}</p>
    </div>
  );
}
