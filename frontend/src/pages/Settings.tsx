import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiClient } from "../lib/apiClient";
import { useAuth } from "../context/AuthContext";

type Profile = {
  category: string;
  target_roles: string[];
  min_lpa: number | null;
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

  return (
    <div className="max-w-xl">
      <h1 className="font-display text-2xl text-ink-900 mb-6">Settings</h1>

      <div className="rounded-lg border border-ink-100 bg-white p-5 mb-4">
        <p className="text-xs font-medium uppercase tracking-wider text-ink-500 mb-3">Account</p>
        <dl className="grid grid-cols-3 gap-y-2 text-sm">
          <dt className="text-ink-500">Name</dt><dd className="col-span-2">{user?.full_name}</dd>
          <dt className="text-ink-500">Email</dt><dd className="col-span-2">{user?.email}</dd>
        </dl>
      </div>

      {isLoading && <p className="text-sm text-ink-500">Loading profile…</p>}

      {profile && (
        <div className="rounded-lg border border-ink-100 bg-white p-5 mb-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium uppercase tracking-wider text-ink-500">Career Preferences</p>
            <Link to="/onboarding" className="text-xs text-signal-600 hover:underline">Edit →</Link>
          </div>
          <dl className="grid grid-cols-3 gap-y-2 text-sm">
            <dt className="text-ink-500">Category</dt><dd className="col-span-2">{profile.category}</dd>
            <dt className="text-ink-500">Target roles</dt><dd className="col-span-2">{profile.target_roles.join(", ") || "—"}</dd>
            <dt className="text-ink-500">Min LPA</dt><dd className="col-span-2">{profile.min_lpa ?? "—"}</dd>
            <dt className="text-ink-500">Locations</dt><dd className="col-span-2">{profile.preferred_locations.join(", ") || "—"}</dd>
            <dt className="text-ink-500">Remote pref.</dt><dd className="col-span-2">{profile.remote_preference}</dd>
          </dl>
        </div>
      )}

      <div className="rounded-lg border border-ink-100 bg-white p-5 mb-4">
        <p className="text-xs font-medium uppercase tracking-wider text-ink-500 mb-3">Smart Apply</p>
        <p className="text-sm text-ink-700 mb-1">
          Tier: <span className="font-medium">{profile?.auto_apply_settings.tier ?? "manual"}</span>
        </p>
        <p className="text-xs text-ink-500">
          RoleRadar always prepares a package for you to review — it never submits an application on your behalf. Change this during onboarding.
        </p>
      </div>

      <button onClick={logout} className="text-sm text-alert-600 hover:underline">
        Log out
      </button>
    </div>
  );
}
