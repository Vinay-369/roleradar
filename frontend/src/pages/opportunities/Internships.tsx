import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { GraduationCap, ArrowRight, Sparkles, Search, Target } from "lucide-react";
import { getRecommendedMatches } from "../../lib/jobs";
import { getProfile } from "../../lib/profile";
import { JobMatchCard } from "../../components/jobs/JobMatchCard";

export function Internships() {
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const { data: matches, isLoading } = useQuery({
    queryKey: ["matches", "internship"],
    queryFn: () => getRecommendedMatches("internship"),
  });

  const [selectedRole, setSelectedRole] = useState<string>("ALL");
  const [minStipend, setMinStipend] = useState<string>("ALL");
  const [remoteFilter, setRemoteFilter] = useState<string>("ALL");
  const [experienceFilter, setExperienceFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const targetRolesList = useMemo(() => {
    const roles = new Set<string>();
    if (profile?.target_roles) {
      profile.target_roles.forEach((r) => roles.add(r));
    }
    roles.add("Full Stack Intern");
    roles.add("Frontend Intern");
    roles.add("Backend Intern");
    roles.add("Data Science Intern");
    roles.add("Software Engineering Intern");
    return Array.from(roles);
  }, [profile]);

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

      // 5. Keyword query
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
  }, [matches, selectedRole, minStipend, remoteFilter, experienceFilter, searchQuery]);

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
        Real-time verified internship openings ranked by ATS compatibility match with your master resume.
      </p>

      {/* Target Role & Advanced Filters Card */}
      <div className="bg-white rounded-xl border border-ink-100 p-4 mb-6 shadow-xs space-y-4">
        {/* Target Role Selector Pills */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-bold uppercase tracking-wider text-ink-700 flex items-center gap-1.5">
              <Target size={13} className="text-signal-600" /> Filter by Target Internship Role:
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
              All Internship Roles
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
      </div>

      {isLoading && (
        <div className="p-8 text-center bg-white rounded-lg border border-ink-100 shadow-xs">
          <span className="inline-block w-3 h-3 rounded-full bg-signal-500 animate-pulse mb-2" />
          <p className="text-sm text-ink-600 font-medium">Matching verified internships with your resume…</p>
        </div>
      )}

      {!isLoading && filteredInternships.length === 0 && (
        <div className="rounded-xl border border-ink-100 bg-white p-8 text-center shadow-xs">
          <GraduationCap size={32} className="text-ink-300 mx-auto mb-2" />
          <h3 className="font-display text-base text-ink-900 mb-1">No Internships Matching Current Filter</h3>
          <p className="text-xs text-ink-500 max-w-sm mx-auto mb-4">
            Try adjusting your target role or stipend filters, or tailor your resume for any external posting.
          </p>
          <div className="flex justify-center gap-2">
            <button
              onClick={() => {
                setSelectedRole("ALL");
                setMinStipend("ALL");
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
              Tailor External Internship
            </Link>
          </div>
        </div>
      )}

      {filteredInternships.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1 text-xs text-ink-500">
            <span>Showing <strong>{filteredInternships.length}</strong> real-time internships</span>
            <span className="text-[11px] font-semibold text-signal-700">Ranked by Highest ATS Match ↓</span>
          </div>
          {filteredInternships.map((job) => (
            <JobMatchCard key={job.job_id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}
