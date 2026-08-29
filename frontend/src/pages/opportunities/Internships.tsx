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
  const { data: matches, isLoading } = useQuery({
    queryKey: ["matches", "internship"],
    queryFn: () => getRecommendedMatches("internship"),
  });

  const [selectedRole, setSelectedRole] = useState<string>("ALL");
  const [minStipend, setMinStipend] = useState<string>("ALL");
  const [remoteFilter, setRemoteFilter] = useState<string>("ALL");
  const [experienceFilter, setExperienceFilter] = useState<string>("ALL");
  const [dateFilter, setDateFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<"recent" | "match" | "stipend">("recent");
  const [searchQuery, setSearchQuery] = useState<string>("");

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
        if (job.stipend_min !== undefined && job.stipend_min !== null && job.stipend_min < minVal) {
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

      // 5. Date Posted Recency Filter
      if (dateFilter !== "ALL") {
        const maxDays = Number(dateFilter);
        if (job.posted_days_ago !== undefined && job.posted_days_ago > maxDays) {
          return false;
        }
      }

      // 6. Keyword query
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
    } else if (sortBy === "stipend") {
      return list.sort((a, b) => (b.stipend_min ?? 0) - (a.stipend_min ?? 0));
    }

    return list;
  }, [matches, selectedRole, minStipend, remoteFilter, experienceFilter, dateFilter, sortBy, searchQuery]);

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <GraduationCap size={24} className="text-signal-600" />
          <h1 className="font-display text-2xl text-ink-900">Internships</h1>
        </div>
        <Link
          to="/resume/tailor-custom"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-signal-600 hover:text-signal-700 bg-signal-500/10 hover:bg-signal-500/15 px-3 py-1.5 rounded-md transition-colors"
        >
          <Sparkles size={13} /> Tailor for external internship <ArrowRight size={13} />
        </Link>
      </div>

      <p className="text-ink-500 mb-5 text-sm">
        Real-time verified internship openings sorted by most recent posting date.
      </p>

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
