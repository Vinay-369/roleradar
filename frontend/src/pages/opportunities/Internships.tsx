import { useState, useMemo, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { GraduationCap, Sparkles, Search, FileText, RotateCcw } from "lucide-react";
import { getRecommendedMatches, type JobMatch } from "../../lib/jobs";
import { JobMatchCard } from "../../components/jobs/JobMatchCard";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";
import { RoleDropdownSelector } from "../../components/ui/RoleDropdownSelector";
import { ALL_INTERNSHIP_ROLES } from "../../lib/roleConstants";
import { CANONICAL_CAREER_STAGES, getProfile } from "../../lib/profile";
import {
  saveListState,
  loadListState,
  clearListState,
  markNavigatedToDetail,
  consumeNavigatedToDetail,
} from "../../lib/listState";

const PAGE_SIZE = 20;

export function Internships() {
  const restoredState = useMemo(() => {
    if (consumeNavigatedToDetail("internships")) {
      return loadListState("internships");
    }
    return null;
  }, []);

  const [regionScope, setRegionScope] = useState<"india" | "global">(restoredState?.regionScope ?? "india");
  const [includeBenchmarks, setIncludeBenchmarks] = useState<boolean>(restoredState?.includeBenchmarks ?? false);

  // Core Discovery Controls
  const [searchQuery, setSearchQuery] = useState<string>(restoredState?.searchQuery ?? "");
  const [selectedRole, setSelectedRole] = useState<string>(restoredState?.selectedRole ?? "ALL");
  const [locationPreset, setLocationPreset] = useState<string>(restoredState?.locationPreset ?? "ALL");
  const [stageFilter, setStageFilter] = useState<string>(restoredState?.stageFilter ?? "ALL");
  const [workplaceFilter, setWorkplaceFilter] = useState<string>(restoredState?.workplaceFilter ?? "ALL");
  const [onlyEligible, setOnlyEligible] = useState<boolean>(restoredState?.onlyEligible ?? false);
  const [sortBy, setSortBy] = useState<"recent" | "match" | "stipend">(
    (restoredState?.sortBy as any) ?? "recent"
  );

  // Progressive Loading State
  const [page, setPage] = useState<number>(restoredState?.page ?? 1);
  const [loadedInternships, setLoadedInternships] = useState<JobMatch[]>(restoredState?.loadedItems ?? []);
  const [totalCount, setTotalCount] = useState<number>(restoredState?.totalCount ?? 0);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);

  const isRestoringRef = useRef<boolean>(!!restoredState);
  const targetScrollYRef = useRef<number | null>(restoredState?.scrollY ?? null);

  // User Profile for Registration Stage Alignment
  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: getProfile,
  });

  // Initial Page 1 Query
  const { data, isLoading } = useQuery({
    queryKey: [
      "matches",
      "internship",
      regionScope,
      includeBenchmarks,
      selectedRole,
      locationPreset,
      stageFilter,
      workplaceFilter,
      searchQuery,
      sortBy,
    ],
    queryFn: () =>
      getRecommendedMatches("internship", false, {
        region: regionScope,
        includeBenchmarks,
        role: selectedRole !== "ALL" ? selectedRole : undefined,
        locationPreset: locationPreset !== "ALL" ? locationPreset : undefined,
        stage: stageFilter !== "ALL" ? stageFilter : undefined,
        workplaceType: workplaceFilter !== "ALL" ? workplaceFilter : undefined,
        search: searchQuery.trim() || undefined,
        sortBy,
        page: 1,
        pageSize: PAGE_SIZE,
      }),
  });

  // Synchronize initial page results
  useEffect(() => {
    if (isRestoringRef.current) {
      isRestoringRef.current = false;
      return;
    }
    if (data) {
      setLoadedInternships(data.items);
      setTotalCount(data.total);
      setPage(1);
    }
  }, [data]);

  // Restore scroll position after loaded items are rendered
  useEffect(() => {
    if (targetScrollYRef.current !== null && loadedInternships.length > 0) {
      const scrollY = targetScrollYRef.current;
      targetScrollYRef.current = null;
      const timer = setTimeout(() => {
        window.scrollTo({ top: scrollY, behavior: "instant" });
      }, 60);
      return () => clearTimeout(timer);
    }
  }, [loadedInternships]);

  const handleSaveListState = () => {
    saveListState("internships", {
      regionScope,
      includeBenchmarks,
      searchQuery,
      selectedRole,
      locationPreset,
      stageFilter,
      workplaceFilter,
      onlyEligible,
      sortBy,
      page,
      loadedItems: loadedInternships,
      totalCount,
      scrollY: window.scrollY,
    });
    markNavigatedToDetail("internships");
  };

  const hasResume = useMemo(() => {
    return loadedInternships.some((m) => m.has_match) ?? false;
  }, [loadedInternships]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (searchQuery.trim()) count++;
    if (selectedRole !== "ALL") count++;
    if (locationPreset !== "ALL") count++;
    if (stageFilter !== "ALL") count++;
    if (workplaceFilter !== "ALL") count++;
    if (onlyEligible) count++;
    return count;
  }, [searchQuery, selectedRole, locationPreset, stageFilter, workplaceFilter, onlyEligible]);

  const resetAllFilters = () => {
    clearListState("internships");
    setSearchQuery("");
    setSelectedRole("ALL");
    setLocationPreset("ALL");
    setStageFilter("ALL");
    setWorkplaceFilter("ALL");
    setOnlyEligible(false);
    setSortBy("recent");
    setPage(1);
  };

  // Progressive "Show More" Handler
  const handleShowMore = async () => {
    if (isLoadingMore || loadedInternships.length >= totalCount) return;
    setIsLoadingMore(true);
    const nextPage = page + 1;
    try {
      const res = await getRecommendedMatches("internship", false, {
        region: regionScope,
        includeBenchmarks,
        role: selectedRole !== "ALL" ? selectedRole : undefined,
        locationPreset: locationPreset !== "ALL" ? locationPreset : undefined,
        stage: stageFilter !== "ALL" ? stageFilter : undefined,
        workplaceType: workplaceFilter !== "ALL" ? workplaceFilter : undefined,
        search: searchQuery.trim() || undefined,
        sortBy,
        page: nextPage,
        pageSize: PAGE_SIZE,
      });
      setLoadedInternships((prev) => {
        const existing = new Set(prev.map((j) => j.job_id));
        const newItems = res.items.filter((j) => !existing.has(j.job_id));
        return [...prev, ...newItems];
      });
      setTotalCount(res.total);
      setPage(nextPage);
    } catch (err) {
      console.error("Failed to load more internships:", err);
    } finally {
      setIsLoadingMore(false);
    }
  };

  // Secondary client filter for "Eligible for my profile only"
  const visibleInternships = useMemo(() => {
    if (!onlyEligible) return loadedInternships;
    return loadedInternships.filter((job) => {
      if (hasResume) {
        return job.eligibility?.status === "ELIGIBLE" || job.eligibility?.status === "LIKELY_ELIGIBLE";
      }
      return job.student_eligible || job.fresher_eligible;
    });
  }, [loadedInternships, onlyEligible, hasResume]);

  return (
    <div className="max-w-5xl mx-auto pt-4 pb-12 px-4 sm:px-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <GraduationCap size={20} className="text-signal-600" />
            <h1 className="text-xl sm:text-2xl font-bold font-display text-ink-950">Internships & Co-ops</h1>
          </div>
          <p className="text-xs text-ink-500">
            Student and fresher friendly opportunities verified directly on employer portals.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Link
            to="/resume/tailor-custom"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-ink-200 bg-white hover:bg-ink-50 text-ink-800 text-xs font-semibold transition-colors shadow-2xs"
          >
            <FileText size={13} className="text-signal-600" />
            <span>Paste External JD</span>
          </Link>

          {/* India vs Global Scope Explorer */}
          <div className="inline-flex rounded-lg border border-ink-200 bg-ink-50 p-1 text-xs font-semibold shrink-0">
            <button
              type="button"
              onClick={() => setRegionScope("india")}
              className={`px-3 py-1 rounded-md transition-all ${
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
              className={`px-3 py-1 rounded-md transition-all ${
                regionScope === "global"
                  ? "bg-white text-signal-700 shadow-xs font-bold border border-ink-100"
                  : "text-ink-600 hover:text-ink-950"
              }`}
            >
              🌐 Global
            </button>
          </div>
        </div>
      </div>

      {/* Pre-Resume Discovery Banner */}
      {!hasResume && !isLoading && visibleInternships.length > 0 && (
        <div className="bg-signal-500/10 border border-signal-500/20 rounded-xl p-3 mb-3 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2.5">
            <Sparkles size={16} className="text-signal-700 shrink-0" />
            <p className="text-xs text-signal-800">
              <span className="font-semibold text-signal-950">Student Discovery Mode:</span> Upload your resume to calculate your match score, missing skills, and instant tailoring.
            </p>
          </div>
          <Link
            to="/resume/master"
            className="shrink-0 text-xs font-semibold text-white bg-signal-600 hover:bg-signal-700 px-3 py-1.5 rounded-lg transition-colors shadow-2xs ml-auto"
          >
            Upload Resume
          </Link>
        </div>
      )}

      {/* Streamlined Filter Panel */}
      <div className="bg-white rounded-xl border border-ink-100 p-3.5 mb-3 shadow-xs space-y-3">
        {/* Row 1: Search + Role */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-2.5">
          <div className="sm:col-span-6 relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search internship title, company, skill…"
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-ink-200 text-xs outline-none focus:border-signal-500 shadow-2xs"
            />
          </div>

          <div className="sm:col-span-6">
            <RoleDropdownSelector
              label="Role:"
              selectedRole={selectedRole}
              onRoleChange={setSelectedRole}
              roles={ALL_INTERNSHIP_ROLES}
              includeAllOption={true}
              allOptionLabel="All Internship Roles"
            />
          </div>
        </div>

        {/* Row 2: Location + Your Stage + Workplace */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-2 border-t border-ink-50">
          <div>
            <label className="block text-[10px] font-semibold text-ink-500 uppercase tracking-wider mb-1">Location</label>
            <select
              value={locationPreset}
              onChange={(e) => setLocationPreset(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded-lg border border-ink-200 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              <option value="ALL">All Locations</option>
              <option value="Bengaluru">Bengaluru</option>
              <option value="Delhi NCR">Delhi NCR</option>
              <option value="Hyderabad">Hyderabad</option>
              <option value="Pune">Pune</option>
              <option value="Mumbai">Mumbai</option>
              <option value="Chennai">Chennai</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-semibold text-ink-500 uppercase tracking-wider mb-1">
              Your Stage
            </label>
            <select
              value={stageFilter}
              onChange={(e) => setStageFilter(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded-lg border border-ink-200 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              {CANONICAL_CAREER_STAGES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                  {profile?.category === s.value ? " (Your Stage)" : ""}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-semibold text-ink-500 uppercase tracking-wider mb-1">Workplace</label>
            <select
              value={workplaceFilter}
              onChange={(e) => setWorkplaceFilter(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded-lg border border-ink-200 bg-white text-xs outline-none focus:border-signal-500 font-medium text-ink-800 shadow-2xs"
            >
              <option value="ALL">Any Workplace</option>
              <option value="remote">Remote Only</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">On-site / Office</option>
            </select>
          </div>
        </div>

        {/* Row 3: Auxiliary Toggles + Sort + Reset */}
        <div className="flex items-center justify-between gap-3 pt-2 border-t border-ink-50 flex-wrap text-xs">
          <div className="flex items-center gap-4 flex-wrap">
            <label className="flex items-center gap-2 cursor-pointer select-none text-ink-700 hover:text-ink-950 font-medium">
              <input
                type="checkbox"
                checked={includeBenchmarks}
                onChange={(e) => setIncludeBenchmarks(e.target.checked)}
                className="rounded border-ink-300 text-signal-600 focus:ring-signal-500 cursor-pointer"
              />
              <span>Include Market Benchmark Profiles</span>
            </label>

            {hasResume && (
              <label className="flex items-center gap-2 cursor-pointer select-none text-ink-700 hover:text-ink-950 font-medium">
                <input
                  type="checkbox"
                  checked={onlyEligible}
                  onChange={(e) => setOnlyEligible(e.target.checked)}
                  className="rounded border-ink-300 text-signal-600 focus:ring-signal-500 cursor-pointer"
                />
                <span>Eligible for my profile only</span>
              </label>
            )}
          </div>

          <div className="flex items-center gap-3 ml-auto">
            <div className="flex items-center gap-1.5 text-xs text-ink-500">
              <span>Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="px-2 py-1 rounded-md border border-ink-200 bg-white text-xs font-semibold text-ink-800"
              >
                <option value="recent">Most Recent</option>
                <option value="match">Highest Match</option>
                <option value="stipend">Stipend</option>
              </select>
            </div>

            {activeFilterCount > 0 && (
              <button
                type="button"
                onClick={resetAllFilters}
                className="inline-flex items-center gap-1 text-xs font-semibold text-rose-600 hover:text-rose-700 hover:underline transition-colors cursor-pointer"
              >
                <RotateCcw size={11} />
                <span>Reset ({activeFilterCount})</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {isLoading && <SkeletonCard count={4} />}

      {/* Transparent Low Inventory Notice */}
      {!isLoading && totalCount > 0 && totalCount <= 5 && !includeBenchmarks && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 mb-3 text-xs text-amber-900 flex items-center justify-between gap-2 flex-wrap">
          <p>
            <span className="font-bold">Live Inventory Note:</span> Only {totalCount} live internship{totalCount === 1 ? "" : "s"} currently open directly on employer ATS portals matching these filters.
          </p>
          <button
            type="button"
            onClick={() => setIncludeBenchmarks(true)}
            className="text-amber-800 hover:text-amber-950 font-bold underline cursor-pointer"
          >
            Toggle Market Benchmark Profiles →
          </button>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && visibleInternships.length === 0 && (
        <EmptyState
          icon={GraduationCap}
          title={
            activeFilterCount > 0
              ? "No internships match your selected filters"
              : "No live internships currently published on connected employer ATS boards"
          }
          description={
            activeFilterCount > 0
              ? "Try clearing filters or selecting another role. You can also toggle 'Include Market Benchmark Profiles' to explore reference career paths."
              : "Connected employer ATS portals currently have no matching live internship postings. You can enable 'Include Market Benchmark Profiles' to explore student competencies."
          }
          actionText={activeFilterCount > 0 ? "Reset Filters" : (!includeBenchmarks ? "Show Career Benchmark Roles" : undefined)}
          onAction={activeFilterCount > 0 ? resetAllFilters : (!includeBenchmarks ? () => setIncludeBenchmarks(true) : undefined)}
          secondaryActionText="Paste External Job Description"
          secondaryActionHref="/resume/tailor-custom"
        />
      )}

      {/* Results List */}
      {visibleInternships.length > 0 && (
        <div className="space-y-3">
          {/* Single Authoritative Count & Status Row */}
          <div className="flex items-center justify-between px-1 py-1 text-xs text-ink-600 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-ink-900">
                Showing {visibleInternships.length} of {totalCount} active internship{totalCount === 1 ? "" : "s"}
              </span>
              {!includeBenchmarks && (
                <span className="text-ink-400 hidden sm:inline">
                  • Verified live from connected employer ATS boards
                </span>
              )}
            </div>
            {!includeBenchmarks && (
              <button
                type="button"
                onClick={() => setIncludeBenchmarks(true)}
                className="text-signal-700 hover:text-signal-800 font-medium underline underline-offset-2 text-[11px] cursor-pointer ml-auto"
              >
                Explore Market Benchmark Profiles →
              </button>
            )}
          </div>

          {visibleInternships.map((job) => (
            <JobMatchCard key={job.job_id} job={job} onViewDetail={handleSaveListState} />
          ))}

          {/* Progressive "Show More" Action */}
          {visibleInternships.length < totalCount ? (
            <div className="mt-6 flex flex-col items-center justify-center gap-2 pt-2 pb-4">
              <button
                type="button"
                onClick={handleShowMore}
                disabled={isLoadingMore}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-ink-900 hover:bg-ink-950 text-white text-xs font-semibold shadow-xs hover:shadow transition-all disabled:opacity-50 cursor-pointer active:scale-98"
              >
                {isLoadingMore ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Loading more internships…</span>
                  </>
                ) : (
                  <>
                    <span>Show More Internships</span>
                    <span className="text-ink-400 font-mono text-[11px]">
                      ({visibleInternships.length} loaded of {totalCount})
                    </span>
                  </>
                )}
              </button>
              <p className="text-[11px] text-ink-400">
                Showing {visibleInternships.length} of {totalCount} total internships matching your criteria
              </p>
            </div>
          ) : totalCount > 0 ? (
            <div className="mt-6 text-center py-4 border-t border-ink-100">
              <p className="text-xs text-ink-500 font-medium">
                All {totalCount} verified active internships matching your filters are loaded.
              </p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
