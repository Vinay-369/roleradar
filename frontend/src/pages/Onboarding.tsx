import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Target, Check, ArrowRight, AlertCircle, Search, Plus, X, ShieldCheck } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../lib/apiClient";
import { useAuth } from "../context/AuthContext";
import { getCanonicalRoles, type CanonicalRole } from "../lib/learning";
import { ALL_JOB_ROLES } from "../lib/roleConstants";

const CATEGORIES = [
  { value: "FRESHER", label: "Fresher / New Graduate" },
  { value: "EXPERIENCED", label: "Experienced Professional" },
  { value: "CAREER_SWITCHER", label: "Career Switcher" },
  { value: "INTERNSHIP_SEEKER", label: "Internship Seeker" },
];

export function Onboarding() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const { data: canonicalRoles } = useQuery({
    queryKey: ["canonical-roles"],
    queryFn: getCanonicalRoles,
  });
  const roleOptions = useMemo<CanonicalRole[]>(
    () => canonicalRoles?.length
      ? canonicalRoles
      : ALL_JOB_ROLES.map((role) => ({ role, domain: "", subdomain: "", aliases: [] })),
    [canonicalRoles],
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [category, setCategory] = useState("FRESHER");
  const [experienceYears, setExperienceYears] = useState("0");
  const [targetRoles, setTargetRoles] = useState<string[]>([]);
  const [roleInput, setRoleInput] = useState("");
  const [rolesOpen, setRolesOpen] = useState(false);
  const rolePickerRef = useRef<HTMLDivElement>(null);
  const [minLpa, setMinLpa] = useState("");
  const [minStipend, setMinStipend] = useState("");
  const [internshipDuration, setInternshipDuration] = useState("");
  const [locations, setLocations] = useState("");
  const [remotePreference, setRemotePreference] = useState("any");
  const [internshipInterested, setInternshipInterested] = useState(false);
  const [careerBrief, setCareerBrief] = useState("");
  const [consentChecked, setConsentChecked] = useState(false);
  const filteredRoles = useMemo(() => {
    const terms = roleInput.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    if (!terms.length) return roleOptions;
    return roleOptions.filter((option) => {
      const searchText = [
        option.role,
        option.domain,
        option.subdomain,
        ...(option.aliases ?? []),
      ].filter(Boolean).join(" ").toLocaleLowerCase();
      return terms.every((term) => searchText.includes(term));
    });
  }, [roleInput, roleOptions]);

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

  function removeRole(role: string) {
    if (targetRoles.length > 1) {
      setTargetRoles(targetRoles.filter((selectedRole) => selectedRole !== role));
    }
  }

  function handleAddCustomRole() {
    const trimmed = roleInput.trim();
    const normalized = (value: string) => value.toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();
    const canonicalRole = roleOptions.find((option) =>
      [option.role, ...(option.aliases ?? [])].some((name) => normalized(name) === normalized(trimmed)),
    )?.role;
    const roleToAdd = canonicalRole ?? trimmed;
    if (roleToAdd && !targetRoles.some((role) => normalized(role) === normalized(roleToAdd))) {
      setTargetRoles([...targetRoles, roleToAdd]);
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

  const isExperienced = category === "EXPERIENCED";
  const isIntern = category === "INTERNSHIP_SEEKER";
  const experienceIsValid = !isExperienced || (experienceYears !== "" && Number(experienceYears) >= 0);
  const canSubmit = !submitting
    && CATEGORIES.some((option) => option.value === category)
    && targetRoles.length > 0
    && consentChecked
    && experienceIsValid;

  return (
    <main className="rr-auth-page min-h-screen overflow-x-hidden px-4 py-8 sm:py-12">
      <header className="rr-portal-header -mx-4 -mt-8 mb-8 sm:-mt-12">
        <div className="rr-portal-header-inner">
          <div className="rr-portal-brand">
            <div className="rr-portal-brand-mark"><Target size={23} strokeWidth={2.5} /></div>
            <div>
              <p className="font-display text-lg font-semibold tracking-tight text-white">Role<span className="text-cyan-300">Radar</span></p>
              <p className="text-xs font-medium text-slate-300">AI Resume Intelligence</p>
            </div>
          </div>
          <span className="rr-portal-year">AI CAREER WORKSPACE</span>
        </div>
      </header>

      <form onSubmit={handleSubmit} className="rr-onboarding-card mx-auto w-full max-w-2xl space-y-6 rounded-2xl border bg-white p-5 shadow-lg sm:p-8 dark:bg-slate-900">
        <header className="rr-onboarding-heading">
          <div className="mb-5">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="font-semibold text-indigo-700 dark:text-indigo-300">Step 1 of 2</span>
              <span className="text-slate-500 dark:text-slate-400">Career goals</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
              <div className="h-full w-1/2 rounded-full bg-indigo-600" />
            </div>
          </div>
          <div className="flex items-start gap-3">
            <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-300">
              <Target size={22} />
            </span>
            <div>
              <h1 className="font-display text-xl font-bold text-slate-900 dark:text-white sm:text-2xl">Tell us about your career goals</h1>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                These preferences drive your ATS scoring, match ranking, and skill gap roadmaps across RoleRadar.
              </p>
            </div>
          </div>
        </header>

        {error && (
          <div role="alert" className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <section className="space-y-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="career-category" className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                I am a... <span className="text-rose-500">*</span>
              </label>
              <select
                id="career-category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              >
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor={isIntern ? "minimum-stipend" : "minimum-lpa"} className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                {isIntern ? "Expected monthly stipend (₹/mo)" : "Minimum LPA"}
              </label>
              <input
                id={isIntern ? "minimum-stipend" : "minimum-lpa"}
                type="number"
                min="0"
                step={isIntern ? "1000" : "0.5"}
                value={isIntern ? minStipend : minLpa}
                onChange={(e) => isIntern ? setMinStipend(e.target.value) : setMinLpa(e.target.value)}
                placeholder={isIntern ? "e.g. 25000" : "e.g. 6"}
                className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          {isExperienced && (
            <div>
              <label htmlFor="experience-years" className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Years of experience <span className="text-rose-500">*</span>
              </label>
              <input
                id="experience-years"
                type="number"
                min="0"
                max="50"
                step="0.5"
                required
                value={experienceYears}
                onChange={(e) => setExperienceYears(e.target.value)}
                placeholder="e.g. 3"
                className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              />
            </div>
          )}

          <div
            ref={rolePickerRef}
            className="relative"
            onBlur={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                setRolesOpen(false);
              }
            }}
          >
            <div className="mb-1.5 flex items-center justify-between gap-3">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Target role(s) <span className="text-rose-500">*</span>
              </label>
              <span className="text-[11px] text-slate-500 dark:text-slate-400">Select one or more</span>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-2.5 transition focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 dark:border-slate-600 dark:bg-slate-900">
              <div className="mb-2 flex flex-wrap gap-1.5">
                {targetRoles.map((role) => (
                  <span key={role} className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 py-1 pl-2.5 pr-1.5 text-xs font-medium text-indigo-800 dark:border-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-200">
                    {role}
                    <button
                      type="button"
                      onClick={() => removeRole(role)}
                      disabled={targetRoles.length === 1}
                      aria-label={`Remove ${role}`}
                      title={targetRoles.length === 1 ? "At least one target role is required" : `Remove ${role}`}
                      className="grid size-5 place-items-center rounded-full text-indigo-600 transition hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-50 dark:text-indigo-300 dark:hover:bg-indigo-900"
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <Search size={16} className="ml-1 shrink-0 text-slate-400" />
                <input
                  value={roleInput}
                  onFocus={() => setRolesOpen(true)}
                  onChange={(e) => { setRoleInput(e.target.value); setRolesOpen(true); }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") { e.preventDefault(); handleAddCustomRole(); }
                    if (e.key === "Escape") setRolesOpen(false);
                  }}
                  placeholder={`Search ${roleOptions.length} roles or add a custom role...`}
                  aria-label="Search target roles"
                  aria-expanded={rolesOpen}
                  className="min-w-0 flex-1 bg-transparent p-1 text-sm text-slate-900 outline-none placeholder:text-slate-400 dark:text-slate-100"
                />
                <button
                  type="button"
                  onClick={handleAddCustomRole}
                  disabled={!roleInput.trim()}
                  className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-indigo-50 px-2.5 py-2 text-xs font-semibold text-indigo-700 transition hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-indigo-950/50 dark:text-indigo-300 dark:hover:bg-indigo-900/60"
                >
                  <Plus size={14} /> Add
                </button>
              </div>
            </div>
            {rolesOpen && (
              <div className="absolute inset-x-0 top-full z-20 mt-2 max-h-60 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl dark:border-slate-700 dark:bg-slate-900">
                  {filteredRoles.map(({ role, domain, subdomain }) => {
                    const isSelected = targetRoles.includes(role);
                    return (
                      <button
                        type="button"
                        key={role}
                        onClick={() => toggleRole(role)}
                        aria-pressed={isSelected}
                        className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition hover:bg-slate-50 dark:hover:bg-slate-800 ${isSelected ? "bg-indigo-50 dark:bg-indigo-950/40" : ""}`}
                      >
                        <span className="font-medium text-slate-800 dark:text-slate-100">{role}</span>
                        <span className="flex shrink-0 items-center gap-1.5 text-[10px] text-slate-500 dark:text-slate-400">
                          {[domain, subdomain].filter(Boolean).join(" · ")}
                          {isSelected && <Check size={13} className="text-indigo-600 dark:text-indigo-300" />}
                        </span>
                      </button>
                    );
                  })}
                  {!filteredRoles.length && (
                    <p className="px-3 py-3 text-xs text-slate-500 dark:text-slate-400">No supported role matches. Add your custom role above.</p>
                  )}
              </div>
            )}
          </div>

          {isIntern && (
            <div>
              <label htmlFor="internship-duration" className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">Internship duration (months)</label>
              <input
                id="internship-duration"
                type="number"
                min="1"
                max="24"
                value={internshipDuration}
                onChange={(e) => setInternshipDuration(e.target.value)}
                placeholder="e.g. 3 or 6"
                className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              />
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="remote-preference" className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">Remote preference</label>
              <select
                id="remote-preference"
                value={remotePreference}
                onChange={(e) => setRemotePreference(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              >
                <option value="any">Any</option>
                <option value="remote">Remote Only</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
            </div>
            {remotePreference !== "remote" ? (
              <div>
                <label htmlFor="preferred-locations" className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">Preferred locations</label>
                <input
                  id="preferred-locations"
                  value={locations}
                  onChange={(e) => setLocations(e.target.value)}
                  placeholder="Bangalore, Hyderabad, Pune"
                  className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
                />
              </div>
            ) : (
              <div className="flex items-end">
                <p className="w-full rounded-xl border border-indigo-100 bg-indigo-50 p-3 text-xs text-indigo-800 dark:border-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-200">
                  Remote-only roles can be found across locations.
                </p>
              </div>
            )}
          </div>

          {category !== "INTERNSHIP_SEEKER" && (
            <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600">
              <span>
                <span className="block text-sm font-semibold text-slate-800 dark:text-slate-100">Also interested in internships</span>
                <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">Include internship opportunities in your discovery feed.</span>
              </span>
              <span className="relative inline-flex shrink-0 items-center">
                <input
                  type="checkbox"
                  checked={internshipInterested}
                  onChange={(e) => setInternshipInterested(e.target.checked)}
                  className="peer sr-only"
                />
                <span className="h-6 w-11 rounded-full bg-slate-300 transition peer-checked:bg-indigo-600 peer-focus-visible:ring-2 peer-focus-visible:ring-indigo-500 peer-focus-visible:ring-offset-2 dark:bg-slate-600" />
                <span className="pointer-events-none absolute left-0.5 size-5 rounded-full bg-white shadow-sm transition peer-checked:translate-x-5" />
              </span>
            </label>
          )}

          <div>
            <label htmlFor="career-brief" className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">Career brief <span className="font-normal normal-case tracking-normal text-slate-400">(optional)</span></label>
            <textarea
              id="career-brief"
              value={careerBrief}
              onChange={(e) => setCareerBrief(e.target.value)}
              rows={3}
              placeholder="A sentence or two about your career direction..."
              className="w-full resize-y rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            />
          </div>

          <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-relaxed text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
            <input
              type="checkbox"
              required
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
              className="mt-0.5 size-4 shrink-0 accent-indigo-600"
            />
            <span className="flex gap-2">
              <ShieldCheck size={16} className="mt-0.5 shrink-0 text-indigo-600 dark:text-indigo-400" />
              <span><span className="font-semibold text-slate-800 dark:text-slate-200">Approval & privacy</span><br />{consentText}</span>
            </span>
          </label>
        </section>

        <button
          type="submit"
          disabled={!canSubmit}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3.5 text-sm font-semibold text-white shadow-md transition-all hover:bg-indigo-700 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Saving Profile..." : <>Finish Setup & Enter Dashboard <ArrowRight size={16} /></>}
        </button>
      </form>

    </main>
  );
}
