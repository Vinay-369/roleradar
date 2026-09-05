import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { GraduationCap, ArrowRight, Sparkles, Search } from "lucide-react";
import { getRecommendedMatches } from "../../lib/jobs";
import { JobMatchCard } from "../../components/jobs/JobMatchCard";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";
import { RoleDropdownSelector } from "../../components/ui/RoleDropdownSelector";
import { ALL_INTERNSHIP_ROLES } from "../../lib/roleConstants";

export function Internships() {
  const [regionScope, setRegionScope] = useState<"india" | "global">("india");

  const { data: matches, isLoading } = useQuery({
    queryKey: ["matches", "internship", regionScope],
    queryFn: () => getRecommendedMatches("internship", false, { region: regionScope }),
  });

  const [selectedRole, setSelectedRole] = useState<string>("ALL");
  const [minStipend, setMinStipend] = useState<string>("ALL");
  const [remoteFilter, setRemoteFilter] = useState<string>("ALL");
  const [experienceFilter, setExperienceFilter] = useState<string>("ALL");
  const [locationPreset, setLocationPreset] = useState<string>("ALL");
  const [onlyEligible, setOnlyEligible] = useState<boolean>(false);
  const [dateFilter, setDateFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<"recent" | "match" | "stipend">("recent");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const hasResume = useMemo(() => {
    return matches?.some((m) => m.has_match) ?? false;
  }, [matches]);

  const filteredInternships = useMemo(() => {
    if (!matches) return [];

    let list = matches.filter((job) => {
      // 1. Role filter
      if (selectedRole !== "ALL") {
        const titleLower = job.job_title.toLowerCase();
        const selectedLower = selectedRole.toLowerCase().replace(" intern", "");
        if (!titleLower.includes(selectedLower) && !selectedLower.includes(titleLower)) {
          return false;
        }
      }

      // 2. Min Stipend filter
      if (minStipend !== "ALL") {
        const minVal = Number(minStipend);
        const stVal = job.stipend || job.stipend_min;
        if (stVal !== undefined && stVal !== null && stVal < minVal) {
          return false;
        }
      }

      // 3. Remote / Workplace filter
      if (remoteFilter === "remote") {
        if (!job.is_remote && !job.location?.toLowerCase().includes("remote")) {
          return false;
        }
      } else if (remoteFilter === "hybrid") {
        if (!job.location?.toLowerCase().includes("hybrid")) {
          return false;
        }
      } else if (remoteFilter === "onsite") {
        if (job.is_remote || job.location?.toLowerCase().includes("remote")) {
          return false;
        }
      }

      // 4. Candidate Stage / Experience
      if (experienceFilter !== "ALL") {
        const titleLower = job.job_title.toLowerCase();
        if (experienceFilter === "student") {
          if (titleLower.includes("graduate") || titleLower.includes("post-grad")) return false;
        }
      }

      // 5. India Location Preset Filter
      if (locationPreset !== "ALL") {
        const locNorm = (job.normalized_location || "").toLowerCase();
        const locRaw = (job.location || "").toLowerCase();
        const presetLower = locationPreset.toLowerCase();
        if (!locNorm.includes(presetLower) && !locRaw.includes(presetLower)) {
          if (presetLower === "delhi ncr") {
            const isNcr = ["delhi", "noida", "gurugram", "gurgaon"].some((c) => locNorm.includes(c) || locRaw.includes(c));
            if (!isNcr) return false;
          } else {
            return false;
          }
        }
      }

      // 6. Explicit "Only Eligible" Filter
      if (onlyEligible) {
        if (hasResume) {
          const isEligible = job.eligibility?.status === "ELIGIBLE" || job.eligibility?.status === "LIKELY_ELIGIBLE";
          if (!isEligible) return false;
        } else {
          if (!job.student_eligible && !job.fresher_eligible) return false;
        }
      }

      // 7. Date Posted Recency Filter
      if (dateFilter !== "ALL") {
        const maxDays = Number(dateFilter);
        if (job.posted_days_ago !== undefined && job.posted_days_ago > maxDays) {
          return false;
        }
      }

      // 8. Keyword query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = job.job_title.toLowerCase().includes(q);
        const matchCompany = job.company.toLowerCase().includes(q);
        const skillsToCheck = job.skills_required && job.skills_required.length > 0 ? job.skills_required : job.matched_skills;
        const matchSkills = skillsToCheck.some((s) => s.toLowerCase().includes(q));
        if (!matchTitle && !matchCompany && !matchSkills) {
          return false;
        }
      }

      return true;
    });

    const isIndia = (j: (typeof list)[0]) => j.country === "India" || (j.normalized_location && j.normalized_location !== "Other");

    // Default: India-first sorting, then user selected criterion
    if (sortBy === "recent") {
      return list.sort((a, b) => {
        const aInd = isIndia(a) ? 0 : 1;
        const bInd = isIndia(b) ? 0 : 1;
        if (aInd !== bInd) return aInd - bInd;
        return (a.posted_days_ago ?? 0) - (b.posted_days_ago ?? 0);
      });
    } else if (sortBy === "match") {
      return list.sort((a, b) => {
        const aInd = isIndia(a) ? 0 : 1;
        const bInd = isIndia(b) ? 0 : 1;
        if (aInd !== bInd) return aInd - bInd;
        return (b.overall_score ?? 0) - (a.overall_score ?? 0);
      });
    } else if (sortBy === "stipend") {
      return list.sort((a, b) => {
        const aInd = isIndia(a) ? 0 : 1;
        const bInd = isIndia(b) ? 0 : 1;
        if (aInd !== bInd) return aInd - bInd;
        return ((b.stipend || b.stipend_min) ?? 0) - ((a.stipend || a.stipend_min) ?? 0);
      });
    }

    return list;
  }, [matches, selectedRole, minStipend, remoteFilter, experienceFilter, locationPreset, onlyEligible, dateFilter, sortBy, searchQuery, hasResume]);

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div className="flex items-center gap-2">
          <GraduationCap size={24} className="text-signal-600" />
          <h1 className="font-display text-2xl text-ink-900">Internships</h1>
        </div>
        <div className="flex items-center gap-2">
          {/* P1-01 India-First vs Global Scope Explorer */}
          <div className="inline-flex rounded-lg border border-ink-200 bg-ink-50 p-1 text-xs font-semibold shrink-0">
            <button
              type="button"
              onClick={() => setRegionScope("india")}
              className={`px-3 py-1.5 rounded-md transition-all ${
                regionScope === "india"
                  ? "bg-white text-signal-700 shadow-xs font-bold border border-ink-100"
                  : "text-ink-600 hover:text-ink-950"
              }`}
            >
              🇮🇳 India
            </button>
            <button
              type="button"
              onClick={() => setRegionScope("global")}
              className={`px-3 py-1.5 rounded-md transition-all ${
                regionScope === "global"
                  ? "bg-white text-signal-700 shadow-xs font-bold border border-ink-100"
                  : "text-ink-600 hover:text-ink-950"
              }`}
            >
              🌐 Global / All Locations
            </button>
          </div>
          <Link
            to="/resume/tailor-custom"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-ink-800 hover:text-ink-950 bg-white hover:bg-ink-50 border border-ink-200 px-3 py-1.5 rounded-md transition-colors shadow-2xs"
          >
            <Sparkles size={13} className="text-signal-600" />
            <span>Paste External JD</span>
            <ArrowRight size={13} />
          </Link>
        </div>
      </div>

      <p className="text-ink-500 mb-5 text-sm">
        Real-time verified internship openings sorted by most recent posting date.
      </p>

      {/* Pre-Resume Discovery Banner */}
      {!hasResume && !isLoading && matches && matches.length > 0 && (
        <div className="mb-5 rounded-xl border border-signal-500/20 bg-signal-500/5 p-3.5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-signal-500/10 flex items-center justify-center text-signal-600 shrink-0">
              <Sparkles size={15} />
            </div>
            <div>
              <p className="text-xs font-semibold text-ink-900">Browsing live opportunities</p>
              <p className="text-[11px] text-ink-500">
                You can search, filter, view details, save, and apply to internships right away. Upload your resume to see personalized match scores.
              </p>
            </div>
          </div>
          <Link
            to="/resume/master"
            className="shrink-0 text-xs font-semibold text-white bg-signal-600 hover:bg-signal-700 px-3 py-1.5 rounded-lg transition-colors shadow-2xs"
          >
            Upload Resume
          </Link>
        </div>
      )}

      {/* Target Role & Advanced Filters Card */}
      <div className="bg-white rounded-xl border border-ink-100 p-4 mb-6 shadow-xs space-y-4">
        {/* Target Internship Role Dropdown Selector */}
        <RoleDropdownSelector
          label="Filter by Target Internship Role:"
          selectedRole={selectedRole}
          onRoleChange={setSelectedRole}
          roles={ALL_INTERNSHIP_ROLES}
          includeAllOption={true}
          allOptionLabel="All Openings"
        />

        {/* Multi-Filter Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5 pt-3 border-t border-ink-50">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search title, company, skill…"
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-ink-100 text-xs outline-none focus:border-signal-500 shadow-2xs"
            />
          </div>

          <div>
            <select
              value={minStipend}
              onChange={(e) => setMinStipend(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg border border-ink-100 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              <option value="ALL">Min Stipend: Any</option>
              <option value="10000">Min ₹10,000 / mo</option>
              <option value="20000">Min ₹20,000 / mo</option>
              <option value="30000">Min ₹30,000 / mo</option>
              <option value="50000">Min ₹50,000 / mo</option>
            </select>
          </div>

          <div>
            <select
              value={remoteFilter}
              onChange={(e) => setRemoteFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg border border-ink-100 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              <option value="ALL">Workplace: Any</option>
              <option value="remote">Remote Only</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">Onsite / Office</option>
            </select>
          </div>

          <div>
            <select
              value={experienceFilter}
              onChange={(e) => setExperienceFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg border border-ink-100 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              <option value="ALL">Applicant Stage: Any</option>
              <option value="student">Current Student / Pre-Final</option>
              <option value="graduate">Recent Graduate / Fresher</option>
            </select>
          </div>
        </div>

        {/* India Metros & Eligibility Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-3 border-t border-ink-50">
          <div>
            <select
              value={locationPreset}
              onChange={(e) => setLocationPreset(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg border border-ink-100 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              <option value="ALL">City / Metro: All India</option>
              <option value="Bengaluru">Bengaluru / Bangalore</option>
              <option value="Delhi NCR">Delhi NCR (Noida/Gurugram)</option>
              <option value="Hyderabad">Hyderabad</option>
              <option value="Pune">Pune</option>
              <option value="Mumbai">Mumbai</option>
              <option value="Chennai">Chennai</option>
              <option value="Noida">Noida</option>
              <option value="Gurugram">Gurugram / Gurgaon</option>
            </select>
          </div>

          <div className="flex items-center gap-2 px-2 py-1 bg-ink-50/60 rounded-lg border border-ink-100">
            <input
              type="checkbox"
              id="onlyEligibleInternships"
              checked={onlyEligible}
              onChange={(e) => setOnlyEligible(e.target.checked)}
              className="rounded text-signal-600 focus:ring-signal-500 cursor-pointer"
            />
            <label htmlFor="onlyEligibleInternships" className="text-xs font-semibold text-ink-800 cursor-pointer select-none">
              Only eligible for my profile
            </label>
          </div>
        </div>

        {/* Date Posted & Sort Order Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-3 border-t border-ink-50">
          <div>
            <select
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg border border-ink-100 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              <option value="ALL">Date Posted: Any Time</option>
              <option value="1">Date Posted: Past 24 Hours</option>
              <option value="3">Date Posted: Past 3 Days</option>
              <option value="7">Date Posted: Past Week</option>
              <option value="14">Date Posted: Past 2 Weeks</option>
              <option value="30">Date Posted: Past Month</option>
            </select>
          </div>

          <div>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="w-full px-3 py-1.5 rounded-lg border border-ink-100 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              <option value="recent">Sort by: Most Recent Posting Date (Default)</option>
              <option value="match">Sort by: Highest Match Score</option>
              <option value="stipend">Sort by: Stipend (High to Low)</option>
            </select>
          </div>
        </div>
      </div>

      {isLoading && <SkeletonCard count={4} />}

      {!isLoading && filteredInternships.length === 0 && (
        <EmptyState
          icon={GraduationCap}
          title="No internships matching your criteria"
          description="Try adjusting your target role, date posted, or stipend filters, or tailor your resume for an external internship posting."
          actionText="Reset All Filters"
          onAction={() => {
            setSelectedRole("ALL");
            setMinStipend("ALL");
            setRemoteFilter("ALL");
            setExperienceFilter("ALL");
            setDateFilter("ALL");
            setSortBy("recent");
            setSearchQuery("");
          }}
          secondaryActionText="Tailor for External Internship"
          secondaryActionHref="/resume/tailor-custom"
        />
      )}

      {filteredInternships.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1 text-xs text-ink-500">
            <span>Showing <strong>{filteredInternships.length}</strong> internships</span>
            <span className="text-[11px] font-semibold text-signal-700">
              {sortBy === "recent" ? "Sorted by Most Recent Posting Date ↓" : sortBy === "match" ? "Sorted by Match Score ↓" : "Sorted by Stipend ↓"}
            </span>
          </div>
          {filteredInternships.map((job) => (
            <JobMatchCard key={job.job_id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}
