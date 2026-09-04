import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Briefcase, Sparkles, Search } from "lucide-react";
import { getRecommendedMatches } from "../../lib/jobs";
import { JobMatchCard } from "../../components/jobs/JobMatchCard";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";
import { RoleDropdownSelector } from "../../components/ui/RoleDropdownSelector";
import { ALL_JOB_ROLES } from "../../lib/roleConstants";

export function Jobs() {
  const [regionScope, setRegionScope] = useState<"india" | "global">("india");

  const { data: matches, isLoading } = useQuery({
    queryKey: ["matches", "full_time", regionScope],
    queryFn: () => getRecommendedMatches("full_time", false, { region: regionScope }),
  });

  const [selectedRole, setSelectedRole] = useState<string>("ALL");
  const [minLpa, setMinLpa] = useState<string>("ALL");
  const [remoteFilter, setRemoteFilter] = useState<string>("ALL");
  const [experienceFilter, setExperienceFilter] = useState<string>("ALL");
  const [locationPreset, setLocationPreset] = useState<string>("ALL");
  const [opportunityTypeFilter, setOpportunityTypeFilter] = useState<string>("ALL");
  const [onlyEligible, setOnlyEligible] = useState<boolean>(false);
  const [dateFilter, setDateFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<"recent" | "match" | "salary">("recent");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const hasResume = useMemo(() => {
    return matches?.some((m) => m.has_match) ?? false;
  }, [matches]);

  const filteredJobs = useMemo(() => {
    if (!matches) return [];

    let list = matches.filter((job) => {
      // 1. Role Filter
      if (selectedRole !== "ALL") {
        const titleLower = job.job_title.toLowerCase();
        const selectedLower = selectedRole.toLowerCase();
        if (!titleLower.includes(selectedLower) && !selectedLower.includes(titleLower)) {
          return false;
        }
      }

      // 2. Minimum LPA Filter
      if (minLpa !== "ALL") {
        const minVal = Number(minLpa);
        if (job.salary_min !== undefined && job.salary_min !== null && job.salary_min < minVal) {
          return false;
        }
      }

      // 3. Workplace / Remote Filter
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

      // 4. Experience Filter
      if (experienceFilter !== "ALL") {
        const titleLower = job.job_title.toLowerCase();
        if (experienceFilter === "fresher") {
          if (titleLower.includes("senior") || titleLower.includes("lead") || titleLower.includes("staff") || titleLower.includes("principal")) {
            return false;
          }
        } else if (experienceFilter === "mid") {
          if (titleLower.includes("intern") || titleLower.includes("principal")) {
            return false;
          }
        } else if (experienceFilter === "senior") {
          if (!titleLower.includes("senior") && !titleLower.includes("lead") && !titleLower.includes("staff")) {
            return false;
          }
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

      // 6. Opportunity Type Filter
      if (opportunityTypeFilter !== "ALL") {
        if (job.opportunity_type && job.opportunity_type !== opportunityTypeFilter) {
          return false;
        }
      }

      // 7. Explicit "Only Eligible" Filter
      if (onlyEligible) {
        if (hasResume) {
          const isEligible = job.eligibility?.status === "ELIGIBLE" || job.eligibility?.status === "LIKELY_ELIGIBLE";
          if (!isEligible) return false;
        } else {
          if (!job.fresher_eligible && !job.student_eligible) return false;
        }
      }

      // 8. Date Posted Recency Filter
      if (dateFilter !== "ALL") {
        const maxDays = Number(dateFilter);
        if (job.posted_days_ago !== undefined && job.posted_days_ago > maxDays) {
          return false;
        }
      }

      // 9. Keyword search query
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
    } else if (sortBy === "salary") {
      return list.sort((a, b) => {
        const aInd = isIndia(a) ? 0 : 1;
        const bInd = isIndia(b) ? 0 : 1;
        if (aInd !== bInd) return aInd - bInd;
        return (b.salary_min ?? 0) - (a.salary_min ?? 0);
      });
    }

    return list;
  }, [matches, selectedRole, minLpa, remoteFilter, experienceFilter, locationPreset, opportunityTypeFilter, onlyEligible, dateFilter, sortBy, searchQuery, hasResume]);

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Briefcase size={20} className="text-signal-600" />
            <h1 className="text-2xl font-bold font-display text-ink-950">Active Full-Time Openings</h1>
          </div>
          <p className="text-sm text-ink-600">
            Discover verified direct-apply career opportunities across India and remote.
          </p>
        </div>

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
            🇮🇳 India Opportunities
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
      </div>

      {/* Pre-Resume Discovery Banner */}
      {!hasResume && !isLoading && matches && matches.length > 0 && (
        <div className="bg-signal-500/10 border border-signal-500/20 rounded-xl p-4 mb-6 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-signal-500/20 flex items-center justify-center shrink-0 mt-0.5">
              <Sparkles size={16} className="text-signal-700" />
            </div>
            <div>
              <p className="text-sm font-semibold text-signal-900">Browsing Public Verified Openings</p>
              <p className="text-xs text-signal-700 mt-0.5">
                Upload your resume to see your personalized match score, skill gap breakdown, and instant tailoring.
              </p>
            </div>
          </div>
          <Link
            to="/resume/master"
            className="shrink-0 text-sm font-semibold text-white bg-signal-600 hover:bg-signal-700 px-4 py-2 rounded-lg transition-colors shadow-sm"
          >
            Upload Resume
          </Link>
        </div>
      )}

      {/* Target Role & Advanced Filters Card */}
      <div className="bg-white rounded-xl border border-ink-100 p-4 mb-6 shadow-xs space-y-4">
        {/* Target Role Dropdown Selector */}
        <RoleDropdownSelector
          label="Filter by Target Role:"
          selectedRole={selectedRole}
          onRoleChange={setSelectedRole}
          roles={ALL_JOB_ROLES}
          includeAllOption={true}
          allOptionLabel="All Openings"
        />

        {/* Multi-Filter Controls: Search, Min LPA, Workplace, Experience */}
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
              value={minLpa}
              onChange={(e) => setMinLpa(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg border border-ink-100 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              <option value="ALL">Min Compensation: Any</option>
              <option value="4">Min ₹4 LPA</option>
              <option value="6">Min ₹6 LPA</option>
              <option value="8">Min ₹8 LPA</option>
              <option value="12">Min ₹12 LPA</option>
              <option value="15">Min ₹15 LPA</option>
              <option value="20">Min ₹20+ LPA</option>
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
              <option value="ALL">Experience: Any</option>
              <option value="fresher">Fresher / Entry Level (0–1 yr)</option>
              <option value="mid">Mid-Level (1–3 yrs)</option>
              <option value="senior">Senior / Lead (3+ yrs)</option>
            </select>
          </div>
        </div>

        {/* India Metros & Opportunity Type Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-3 border-t border-ink-50">
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

          <div>
            <select
              value={opportunityTypeFilter}
              onChange={(e) => setOpportunityTypeFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg border border-ink-100 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              <option value="ALL">Type: All Openings</option>
              <option value="FULL_TIME">Full-Time Career</option>
              <option value="GRADUATE_PROGRAM">Graduate Engineer Trainee (GET)</option>
              <option value="INTERNSHIP">Internship</option>
              <option value="APPRENTICESHIP">Apprenticeship</option>
            </select>
          </div>

          <div className="flex items-center gap-2 px-2 py-1 bg-ink-50/60 rounded-lg border border-ink-100">
            <input
              type="checkbox"
              id="onlyEligibleCheck"
              checked={onlyEligible}
              onChange={(e) => setOnlyEligible(e.target.checked)}
              className="rounded text-signal-600 focus:ring-signal-500 cursor-pointer"
            />
            <label htmlFor="onlyEligibleCheck" className="text-xs font-semibold text-ink-800 cursor-pointer select-none">
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
              <option value="salary">Sort by: Compensation (High to Low)</option>
            </select>
          </div>
        </div>
      </div>

      {isLoading && <SkeletonCard count={4} />}

      {!isLoading && filteredJobs.length === 0 && (
        <EmptyState
          icon={Briefcase}
          title="No jobs matching your filter criteria"
          description="Try adjusting your target role, date posted, or compensation filters, or tailor your resume for an external job posting."
          actionText="Reset All Filters"
          onAction={() => {
            setSelectedRole("ALL");
            setMinLpa("ALL");
            setRemoteFilter("ALL");
            setExperienceFilter("ALL");
            setDateFilter("ALL");
            setSortBy("recent");
            setSearchQuery("");
          }}
          secondaryActionText="Tailor for External JD"
          secondaryActionHref="/resume/tailor-custom"
        />
      )}

      {filteredJobs.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1 text-xs text-ink-500">
            <span>Showing <strong>{filteredJobs.length}</strong> openings</span>
            <span className="text-[11px] font-semibold text-signal-700">
              {sortBy === "recent" ? "Sorted by Most Recent Posting Date ↓" : sortBy === "match" ? "Sorted by Match Score ↓" : "Sorted by Compensation ↓"}
            </span>
          </div>
          {filteredJobs.map((job) => (
            <JobMatchCard key={job.job_id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}
