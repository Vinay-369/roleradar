import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Target, Check, ArrowRight, AlertCircle } from "lucide-react";
import { apiClient } from "../lib/apiClient";
import { useAuth } from "../context/AuthContext";

const CATEGORIES = [
  { value: "FRESHER", label: "Fresher / New Graduate" },
  { value: "EXPERIENCED", label: "Experienced Professional" },
  { value: "CAREER_SWITCHER", label: "Career Switcher" },
  { value: "INTERNSHIP_SEEKER", label: "Internship Seeker" },
];

const SUGGESTED_ROLES = [
  "Full Stack Developer",
  "Backend Developer",
  "Frontend Developer",
  "Data Scientist",
  "DevOps Engineer",
  "Machine Learning Engineer",
  "Software Engineer",
  "Cloud Architect",
];

export function Onboarding() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [category, setCategory] = useState("FRESHER");
  const [experienceYears, setExperienceYears] = useState("0");
  const [targetRoles, setTargetRoles] = useState<string[]>(["Full Stack Developer"]);
  const [roleInput, setRoleInput] = useState("");
  const [minLpa, setMinLpa] = useState("");
  const [minStipend, setMinStipend] = useState("");
  const [internshipDuration, setInternshipDuration] = useState("");
  const [locations, setLocations] = useState("");
  const [remotePreference, setRemotePreference] = useState("any");
  const [internshipInterested, setInternshipInterested] = useState(false);
  const [careerBrief, setCareerBrief] = useState("");
  const [consentChecked, setConsentChecked] = useState(false);

  const consentText =
    "I understand RoleRadar will analyze my resume and job data to generate " +
    "recommendations, and that any resume changes or applications require my explicit approval before being used or submitted.";

  function toggleRole(role: string) {
    if (targetRoles.includes(role)) {
      if (targetRoles.length > 1) {
        setTargetRoles(targetRoles.filter((r) => r !== role));
      }
    } else {
      setTargetRoles([...targetRoles, role]);
    }
  }

  function handleAddCustomRole() {
    const trimmed = roleInput.trim();
    if (trimmed && !targetRoles.includes(trimmed)) {
      setTargetRoles([...targetRoles, trimmed]);
      setRoleInput("");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (targetRoles.length === 0) {
      setError("Please select or enter at least one target role.");
      return;
    }
    if (!consentChecked) {
      setError("Please accept the consent statement to continue.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const isIntern = category === "INTERNSHIP_SEEKER";
      await apiClient.post("/profile/onboarding/complete", {
        category,
        experience_years: category === "EXPERIENCED" ? Number(experienceYears) || 0 : 0,
        target_roles: targetRoles,
        min_lpa: isIntern ? null : (minLpa ? Number(minLpa) : null),
        min_stipend: isIntern ? (minStipend ? Number(minStipend) : null) : null,
        internship_duration_months: isIntern ? (internshipDuration ? Number(internshipDuration) : null) : null,
        preferred_locations: remotePreference === "remote" ? ["Remote"] : locations.split(",").map((s) => s.trim()).filter(Boolean),
        remote_preference: remotePreference,
        internship_interested: isIntern ? true : internshipInterested,
        career_brief: careerBrief || null,
        consent_text: consentText,
      });
      await refreshUser();
      navigate("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Something went wrong saving your profile.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-ink-50 flex items-center justify-center py-12 px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-lg bg-white rounded-xl shadow-sm border border-ink-100 p-8">
        <div className="flex items-center gap-2 mb-1">
          <Target size={22} className="text-signal-600" />
          <h1 className="font-display text-xl text-ink-900">Tell us about your career goals</h1>
        </div>
        <p className="text-xs text-ink-500 mb-6 leading-relaxed">
          These required preferences drive your ATS scoring, match ranking, and skill gap roadmaps across RoleRadar.
        </p>

        {error && (
          <div className="mb-4 rounded-md bg-alert-600/10 p-3 text-sm text-alert-600 flex items-center gap-2">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700 mb-1.5">
          I am a... <span className="text-alert-600">*</span>
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full mb-4 rounded-md border border-ink-100 bg-white px-3 py-2.5 text-sm outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-shadow"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>

        {category === "EXPERIENCED" && (
          <div className="mb-4">
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700 mb-1.5">
              Years of Experience <span className="text-alert-600">*</span>
            </label>
            <input
              type="number"
              min="0"
              max="50"
              step="0.5"
              value={experienceYears}
              onChange={(e) => setExperienceYears(e.target.value)}
              placeholder="e.g. 3"
              className="w-full rounded-md border border-ink-100 px-3 py-2 text-sm outline-none focus:border-signal-500"
            />
          </div>
        )}

        <div className="mb-5">
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700">
              Target Role(s) <span className="text-alert-600">*</span>
            </label>
            <span className="text-[11px] text-ink-400">Select one or more</span>
          </div>
          <div className="flex flex-wrap gap-1.5 mb-2.5">
            {SUGGESTED_ROLES.map((role) => {
              const isSelected = targetRoles.includes(role);
              return (
                <button
                  type="button"
                  key={role}
                  onClick={() => toggleRole(role)}
                  className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    isSelected
                      ? "bg-ink-950 text-white shadow-xs"
                      : "bg-ink-50 text-ink-700 hover:bg-ink-100"
                  }`}
                >
                  {isSelected && <Check size={12} className="text-signal-400" />}
                  {role}
                </button>
              );
            })}
          </div>

          <div className="flex gap-2">
            <input
              value={roleInput}
              onChange={(e) => setRoleInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddCustomRole())}
              placeholder="Add other target role (e.g. DevOps Engineer)…"
              className="flex-1 rounded-md border border-ink-100 px-3 py-2 text-xs outline-none focus:border-signal-500"
            />
            <button
              type="button"
              onClick={handleAddCustomRole}
              disabled={!roleInput.trim()}
              className="rounded-md bg-ink-100 hover:bg-ink-200 text-ink-800 px-3 py-2 text-xs font-medium disabled:opacity-50"
            >
              Add
            </button>
          </div>
        </div>

        {category === "INTERNSHIP_SEEKER" ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700 mb-1.5">
                Expected Monthly Stipend (₹/mo)
              </label>
              <input
                type="number"
                min="0"
                step="1000"
                value={minStipend}
                onChange={(e) => setMinStipend(e.target.value)}
                placeholder="e.g. 25000"
                className="w-full rounded-md border border-ink-100 px-3 py-2 text-sm outline-none focus:border-signal-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700 mb-1.5">
                Duration (Months)
              </label>
              <input
                type="number"
                min="1"
                max="24"
                value={internshipDuration}
                onChange={(e) => setInternshipDuration(e.target.value)}
                placeholder="e.g. 3 or 6"
                className="w-full rounded-md border border-ink-100 px-3 py-2 text-sm outline-none focus:border-signal-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700 mb-1.5">
                Remote Preference
              </label>
              <select
                value={remotePreference}
                onChange={(e) => setRemotePreference(e.target.value)}
                className="w-full rounded-md border border-ink-100 bg-white px-3 py-2 text-sm outline-none focus:border-signal-500"
              >
                <option value="any">Any</option>
                <option value="remote">Remote Only</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700 mb-1.5">
                Minimum LPA
              </label>
              <input
                type="number"
                min="0"
                step="0.5"
                value={minLpa}
                onChange={(e) => setMinLpa(e.target.value)}
                placeholder="e.g. 6"
                className="w-full rounded-md border border-ink-100 px-3 py-2 text-sm outline-none focus:border-signal-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700 mb-1.5">
                Remote Preference
              </label>
              <select
                value={remotePreference}
                onChange={(e) => setRemotePreference(e.target.value)}
                className="w-full rounded-md border border-ink-100 bg-white px-3 py-2 text-sm outline-none focus:border-signal-500"
              >
                <option value="any">Any</option>
                <option value="remote">Remote Only</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
            </div>
          </div>
        )}

        {remotePreference !== "remote" && (
          <div className="mb-4">
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700 mb-1.5">
              Preferred Locations (comma-separated)
            </label>
            <input
              value={locations}
              onChange={(e) => setLocations(e.target.value)}
              placeholder="e.g. Bangalore, Hyderabad, Pune"
              className="w-full rounded-md border border-ink-100 px-3 py-2 text-sm outline-none focus:border-signal-500"
            />
          </div>
        )}

        {category !== "INTERNSHIP_SEEKER" && (
          <label className="flex items-center gap-2 mb-4 text-xs text-ink-700 font-medium">
            <input
              type="checkbox"
              checked={internshipInterested}
              onChange={(e) => setInternshipInterested(e.target.checked)}
              className="rounded border-ink-300"
            />
            I'm also interested in internship opportunities
          </label>
        )}

        <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700 mb-1.5">
          Career Brief (optional)
        </label>
        <textarea
          value={careerBrief}
          onChange={(e) => setCareerBrief(e.target.value)}
          rows={2}
          placeholder="Brief 1-2 sentence overview of your career direction…"
          className="w-full mb-4 rounded-md border border-ink-100 px-3 py-2 text-xs outline-none focus:border-signal-500"
        />

        <label className="flex items-start gap-2 mb-6 text-xs text-ink-500 leading-relaxed cursor-pointer">
          <input
            type="checkbox"
            required
            checked={consentChecked}
            onChange={(e) => setConsentChecked(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            <span className="text-alert-600 font-bold">* </span>
            {consentText}
          </span>
        </label>

        <button
          type="submit"
          disabled={submitting || targetRoles.length === 0 || !consentChecked}
          className="w-full flex items-center justify-center gap-1.5 rounded-md bg-signal-500 hover:bg-signal-600 text-white py-2.5 text-sm font-medium disabled:opacity-50 transition-all active:scale-[0.99] shadow-xs"
        >
          {submitting ? "Saving Profile…" : <>Finish Setup & Enter Dashboard <ArrowRight size={15} /></>}
        </button>
      </form>
    </div>
  );
}
