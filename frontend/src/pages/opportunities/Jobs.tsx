import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Briefcase, ArrowRight, Sparkles, Search, Target } from "lucide-react";
import { getRecommendedMatches } from "../../lib/jobs";
import { getProfile } from "../../lib/profile";
import { JobMatchCard } from "../../components/jobs/JobMatchCard";

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
  const [searchQuery, setSearchQuery] = useState<string>("");

  const targetRolesList = useMemo(() => {
    const roles = new Set<string>();
    if (profile?.target_roles) {
      profile.target_roles.forEach((r) => roles.add(r));
    }
    roles.add("Full Stack Developer");
    roles.add("Backend Developer");
    roles.add("Frontend Developer");
    roles.add("Data Scientist");
    roles.add("DevOps Engineer");
    roles.add("Software Engineer");
    return Array.from(roles);
  }, [profile]);

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
        // Evaluate experience score or title indicators
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

      // 5. Keyword search query
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

    // Rank by highest ATS match score descending
    return list.sort((a, b) => b.overall_score - a.overall_score);
  }, [matches, selectedRole, minLpa, remoteFilter, experienceFilter, searchQuery]);

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
        Real-time job openings ranked by ATS compatibility match with your master resume.
      </p>

      {/* Target Role & Advanced Filters Card */}
      <div className="bg-white rounded-xl border border-ink-100 p-4 mb-6 shadow-xs space-y-4">
        {/* Target Role Selector Pills */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-bold uppercase tracking-wider text-ink-700 flex items-center gap-1.5">
              <Target size={13} className="text-signal-600" /> Filter by Target Role:
            </label>
            {selectedRole !== "ALL" && (
              <button
                onClick={() => setSelectedRole("ALL")}
                className="text-[11px] text-signal-600 hover:underline font-medium"
              >
                Reset Role
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setSelectedRole("ALL")}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                selectedRole === "ALL"
                  ? "bg-ink-950 text-white shadow-xs"
                  : "bg-ink-50 text-ink-700 hover:bg-ink-100"
              }`}
            >
              All Openings
            </button>
            {targetRolesList.map((role) => (
              <button
                key={role}
                onClick={() => setSelectedRole(role)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                  selectedRole === role
                    ? "bg-ink-950 text-white shadow-xs"
                    : "bg-ink-50 text-ink-700 hover:bg-ink-100"
                }`}
              >
                {role}
              </button>
            ))}
          </div>
        </div>

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
      </div>

      {isLoading && (
        <div className="p-8 text-center bg-white rounded-lg border border-ink-100 shadow-xs">
          <span className="inline-block w-3 h-3 rounded-full bg-signal-500 animate-pulse mb-2" />
          <p className="text-sm text-ink-600 font-medium">Matching real-time job openings with your resume…</p>
        </div>
      )}

      {!isLoading && filteredJobs.length === 0 && (
        <div className="rounded-xl border border-ink-100 bg-white p-8 text-center shadow-xs">
          <Briefcase size={32} className="text-ink-300 mx-auto mb-2" />
          <h3 className="font-display text-base text-ink-900 mb-1">No Jobs Matching Current Filter</h3>
          <p className="text-xs text-ink-500 max-w-sm mx-auto mb-4">
            Try adjusting your target role or salary filters, or tailor your resume for any external posting.
          </p>
          <div className="flex justify-center gap-2">
            <button
              onClick={() => {
                setSelectedRole("ALL");
                setMinLpa("ALL");
                setRemoteFilter("ALL");
                setExperienceFilter("ALL");
                setSearchQuery("");
              }}
              className="rounded-lg bg-ink-100 hover:bg-ink-200 text-ink-800 px-4 py-2 text-xs font-semibold"
            >
              Reset All Filters
            </button>
            <Link
              to="/resume/tailor-custom"
              className="rounded-lg bg-ink-950 hover:bg-ink-900 text-white px-4 py-2 text-xs font-semibold shadow-xs"
            >
              Tailor External JD
            </Link>
          </div>
        </div>
      )}

      {filteredJobs.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1 text-xs text-ink-500">
            <span>Showing <strong>{filteredJobs.length}</strong> real-time openings</span>
            <span className="text-[11px] font-semibold text-signal-700">Ranked by Highest ATS Match ↓</span>
          </div>
          {filteredJobs.map((job) => (
            <JobMatchCard key={job.job_id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}
