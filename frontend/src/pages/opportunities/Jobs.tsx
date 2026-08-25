import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Briefcase, ArrowRight, Sparkles, Search } from "lucide-react";
import { getRecommendedMatches } from "../../lib/jobs";
import { getProfile } from "../../lib/profile";
import { JobMatchCard } from "../../components/jobs/JobMatchCard";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";
import { RoleDropdownSelector } from "../../components/ui/RoleDropdownSelector";
import { ALL_JOB_ROLES } from "../../lib/roleConstants";

export function Jobs() {
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const { data: matches, isLoading } = useQuery({
    queryKey: ["matches", "full_time"],
    queryFn: () => getRecommendedMatches("full_time"),
  });

  const [selectedRole, setSelectedRole] = useState<string>("ALL");
  const [minLpa, setMinLpa] = useState<string>("ALL");
  const [remoteFilter, setRemoteFilter] = useState<string>("ALL");
  const [experienceFilter, setExperienceFilter] = useState<string>("ALL");
  const [dateFilter, setDateFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<"recent" | "match" | "salary">("recent");
  const [searchQuery, setSearchQuery] = useState<string>("");

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

      // 5. Date Posted Recency Filter
      if (dateFilter !== "ALL") {
        const maxDays = Number(dateFilter);
        if (job.posted_days_ago !== undefined && job.posted_days_ago > maxDays) {
          return false;
        }
      }

      // 6. Keyword search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = job.job_title.toLowerCase().includes(q);
        const matchCompany = job.company.toLowerCase().includes(q);
        const matchSkills = job.matched_skills.some((s) => s.toLowerCase().includes(q));
        if (!matchTitle && !matchCompany && !matchSkills) {
          return false;
        }
      }

      return true;
    });

    // Default: Sort by most recent posting date first
    if (sortBy === "recent") {
      return list.sort((a, b) => (a.posted_days_ago ?? 0) - (b.posted_days_ago ?? 0));
    } else if (sortBy === "match") {
      return list.sort((a, b) => b.overall_score - a.overall_score);
    } else if (sortBy === "salary") {
      return list.sort((a, b) => (b.salary_min ?? 0) - (a.salary_min ?? 0));
    }

    return list;
  }, [matches, selectedRole, minLpa, remoteFilter, experienceFilter, dateFilter, sortBy, searchQuery]);

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Briefcase size={24} className="text-signal-600" />
          <h1 className="font-display text-2xl text-ink-900">Jobs For You</h1>
        </div>
        <Link
          to="/resume/tailor-custom"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-signal-600 hover:text-signal-700 bg-signal-500/10 hover:bg-signal-500/15 px-3 py-1.5 rounded-md transition-colors"
        >
          <Sparkles size={13} /> Tailor for external JD <ArrowRight size={13} />
        </Link>
      </div>

      <p className="text-ink-500 mb-5 text-sm">
        Real-time job openings sorted by most recent posting date.
      </p>

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
