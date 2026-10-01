import { useState, useMemo, useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Briefcase, Sparkles, Search, FileText, RotateCcw, X, RefreshCw, SlidersHorizontal } from "lucide-react";
import { getRecommendedMatches, syncLiveJobs, type JobMatch } from "../../lib/jobs";
import { JobMatchCard } from "../../components/jobs/JobMatchCard";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/SkeletonLoaders";
import { RoleDropdownSelector } from "../../components/ui/RoleDropdownSelector";
import { ALL_JOB_ROLES } from "../../lib/roleConstants";
import { CANONICAL_CAREER_STAGES, getProfile } from "../../lib/profile";
import { getCanonicalRoles } from "../../lib/learning";
import {
  saveListState,
  loadListState,
  clearListState,
  markNavigatedToDetail,
  consumeNavigatedToDetail,
} from "../../lib/listState";

const PAGE_SIZE = 20;

export function Jobs() {
  const queryClient = useQueryClient();
  const liveSync = useMutation({
    mutationFn: syncLiveJobs,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["matches"] }),
  });
  // Check if returning from detail navigation
  const restoredState = useMemo(() => {
    if (consumeNavigatedToDetail("jobs")) {
      const state = loadListState("jobs");
      if (state?.includeBenchmarks) {
        clearListState("jobs");
        return null;
      }
      return state;
    }
    return null;
  }, []);

  const [regionScope, setRegionScope] = useState<"india" | "global">(restoredState?.regionScope ?? "india");

  // Core Discovery Controls
  const [searchQuery, setSearchQuery] = useState<string>(restoredState?.searchQuery ?? "");
  const [selectedRole, setSelectedRole] = useState<string>(restoredState?.selectedRole ?? "ALL");
  const [locationPreset, setLocationPreset] = useState<string>(restoredState?.locationPreset ?? "ALL");
  const [stageFilter, setStageFilter] = useState<string>(restoredState?.stageFilter ?? "ALL");
  const [workplaceFilter, setWorkplaceFilter] = useState<string>(restoredState?.workplaceFilter ?? "ALL");
  const [onlyEligible, setOnlyEligible] = useState<boolean>(restoredState?.onlyEligible ?? false);
  const [sortBy, setSortBy] = useState<"recent" | "salary" | "match">(
    restoredState?.sortBy === "salary"
      ? "salary"
      : restoredState?.sortBy === "match"
        ? "match"
        : "recent"
  );
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState(searchQuery);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearchQuery(searchQuery), 300);
    return () => window.clearTimeout(timer);
  }, [searchQuery]);

  // Progressive Loading State
  const [page, setPage] = useState<number>(restoredState?.page ?? 1);
  const [loadedJobs, setLoadedJobs] = useState<JobMatch[]>(restoredState?.loadedItems ?? []);
  const [totalCount, setTotalCount] = useState<number>(restoredState?.totalCount ?? 0);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);

  const isRestoringRef = useRef<boolean>(!!restoredState);
  const targetScrollYRef = useRef<number | null>(restoredState?.scrollY ?? null);

  // User Profile for Registration Stage Alignment
  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: getProfile,
  });
  const { data: canonicalRoles } = useQuery({
    queryKey: ["canonical-roles"],
    queryFn: getCanonicalRoles,
  });
  const roleOptions = canonicalRoles?.length ? canonicalRoles : ALL_JOB_ROLES;

  // Initial Page 1 Query (automatically refetches when discovery filters change)
  const { data, isFetching: isLoading } = useQuery({
    queryKey: [
      "matches",
      "full_time",
      regionScope,
      selectedRole,
      locationPreset,
      stageFilter,
      workplaceFilter,
      debouncedSearchQuery,
      sortBy,
    ],
    queryFn: () =>
      getRecommendedMatches("full_time", false, {
        region: regionScope,
        role: selectedRole !== "ALL" ? selectedRole : undefined,
        locationPreset: locationPreset !== "ALL" ? locationPreset : undefined,
        stage: stageFilter !== "ALL" ? stageFilter : undefined,
        workplaceType: workplaceFilter !== "ALL" ? workplaceFilter : undefined,
        search: debouncedSearchQuery.trim() || undefined,
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
      setLoadedJobs(data.items);
      setTotalCount(data.total);
      setPage(1);
    }
  }, [data]);

  // Restore scroll position after loaded items are rendered
  useEffect(() => {
    if (targetScrollYRef.current !== null && loadedJobs.length > 0) {
      const scrollY = targetScrollYRef.current;
      targetScrollYRef.current = null;
      const timer = setTimeout(() => {
        window.scrollTo({ top: scrollY, behavior: "instant" });
      }, 60);
      return () => clearTimeout(timer);
    }
  }, [loadedJobs]);

  const handleSaveListState = () => {
    saveListState("jobs", {
      regionScope,
      searchQuery,
      selectedRole,
      locationPreset,
      stageFilter,
      workplaceFilter,
      onlyEligible,
      sortBy,
      page,
      loadedItems: loadedJobs,
      totalCount,
      scrollY: window.scrollY,
    });
    markNavigatedToDetail("jobs");
  };

  const hasResume = useMemo(() => {
    return loadedJobs.some((m) => m.has_match) ?? false;
  }, [loadedJobs]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (searchQuery.trim()) count++;
    if (selectedRole !== "ALL") count++;
    if (locationPreset !== "ALL") count++;
    if (stageFilter !== "ALL") count++;
    if (workplaceFilter !== "ALL") count++;
    if (onlyEligible) count++;
    if (regionScope !== "india") count++;
    return count;
  }, [searchQuery, selectedRole, locationPreset, stageFilter, workplaceFilter, onlyEligible, regionScope]);

  const resetAllFilters = () => {
    clearListState("jobs");
    setSearchQuery("");
    setSelectedRole("ALL");
    setLocationPreset("ALL");
    setStageFilter("ALL");
    setWorkplaceFilter("ALL");
    setOnlyEligible(false);
    setRegionScope("india");
    setSortBy("recent");
    setPage(1);
  };

  // Progressive "Show More" Handler
  const handleShowMore = async () => {
    if (isLoadingMore || loadedJobs.length >= totalCount) return;
    setIsLoadingMore(true);
    const nextPage = page + 1;
    try {
      const res = await getRecommendedMatches("full_time", false, {
        region: regionScope,
        role: selectedRole !== "ALL" ? selectedRole : undefined,
        locationPreset: locationPreset !== "ALL" ? locationPreset : undefined,
        stage: stageFilter !== "ALL" ? stageFilter : undefined,
        workplaceType: workplaceFilter !== "ALL" ? workplaceFilter : undefined,
        search: debouncedSearchQuery.trim() || undefined,
        sortBy,
        page: nextPage,
        pageSize: PAGE_SIZE,
      });
      setLoadedJobs((prev) => {
        const existing = new Set(prev.map((j) => j.job_id));
        const newItems = res.items.filter((j) => !existing.has(j.job_id));
        return [...prev, ...newItems];
      });
      setTotalCount(res.total);
      setPage(nextPage);
    } catch (err) {
      console.error("Failed to load more opportunities:", err);
    } finally {
      setIsLoadingMore(false);
    }
  };

  // Secondary client filter for "Eligible for my profile only"
  const visibleJobs = useMemo(() => {
    const eligibleJobs = onlyEligible
      ? loadedJobs.filter((job) => {
          if (hasResume) {
            return job.eligibility?.status === "ELIGIBLE" || job.eligibility?.status === "LIKELY_ELIGIBLE";
          }
          return job.fresher_eligible || job.student_eligible;
        })
      : loadedJobs;

    if (sortBy !== "match") return eligibleJobs;
    return [...eligibleJobs].sort((a, b) => {
      const aScore = a.overall_score ?? Number.NEGATIVE_INFINITY;
      const bScore = b.overall_score ?? Number.NEGATIVE_INFINITY;
      return bScore - aScore || (a.posted_days_ago ?? Infinity) - (b.posted_days_ago ?? Infinity);
    });
  }, [loadedJobs, onlyEligible, hasResume, sortBy]);

  return (
    <div className="max-w-5xl mx-auto pt-4 pb-12 px-4 sm:px-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <Briefcase size={18} className="text-signal-600" />
            <h1 className="text-xl sm:text-2xl font-bold font-display text-ink-950">Active Full-Time Openings</h1>
          </div>
          <p className="text-xs text-ink-500">
            Verified direct opportunities sourced straight from official employer applicant tracking systems.
          </p>
        </div>

        <div className="flex items-center justify-end gap-2 flex-wrap shrink-0">
          <button
            type="button"
            onClick={() => liveSync.mutate()}
            disabled={liveSync.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-signal-200 bg-signal-50 hover:bg-signal-100 text-signal-800 text-xs font-semibold transition-colors disabled:opacity-60"
            title={liveSync.error ? "Live listing refresh failed" : "Fetch the latest job listings"}
          >
            <RefreshCw size={13} className={liveSync.isPending ? "animate-spin" : ""} />
            <span>{liveSync.isPending ? "Refreshing…" : "Refresh live listings"}</span>
          </button>
          <Link
            to="/resume/tailor-custom"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-ink-200 bg-white hover:bg-ink-50 text-ink-800 text-xs font-semibold transition-colors shadow-2xs"
          >
            <FileText size={13} className="text-signal-600" />
            <span>Paste External JD</span>
          </Link>
          {liveSync.data && <span className="text-[11px] text-ink-500">Synced {liveSync.data.added_count}</span>}
          {liveSync.error && <span className="text-[11px] text-rose-700">Refresh failed</span>}

          {/* India-First vs Global Scope Explorer */}
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
      {!hasResume && !isLoading && visibleJobs.length > 0 && (
        <div className="bg-signal-500/10 border border-signal-500/20 rounded-xl p-3 mb-3 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2.5">
            <Sparkles size={16} className="text-signal-700 shrink-0" />
            <p className="text-xs text-signal-800">
              <span className="font-semibold text-signal-950">Browsing Verified Direct Openings:</span> Upload your resume to calculate your match score, missing skills, and instant tailoring.
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

      <div className="bg-white rounded-xl border border-ink-100 p-4 sm:p-5 mb-4 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <SlidersHorizontal size={16} className="text-signal-600" />
            <h2 className="text-sm font-bold text-ink-900">Find the right opening</h2>
            <span className="hidden sm:inline text-xs text-ink-400">Search and narrow results</span>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-xs font-medium text-ink-700 cursor-pointer">
              <span>Sort by</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as "recent" | "salary" | "match")}
                className="rounded-lg border border-ink-200 bg-white px-2.5 py-2 text-xs font-semibold text-ink-800"
                aria-label="Sort jobs"
              >
                <option value="recent">Most recent</option>
                <option value="salary">Highest compensation</option>
                <option value="match" disabled={!hasResume}>
                  Highest matching score{hasResume ? "" : " (resume required)"}
                </option>
              </select>
            </label>
            {activeFilterCount > 0 && (
              <button
                type="button"
                onClick={resetAllFilters}
                className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-xs font-semibold text-signal-700 hover:bg-signal-500/10 transition-colors"
              >
                <RotateCcw size={13} />
                Clear filters <span className="text-ink-500">({activeFilterCount})</span>
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-12">
          <div className="relative md:col-span-6">
            <label htmlFor="job-search-input" className="mb-1.5 block text-[11px] font-semibold text-ink-600">Keywords</label>
            <div className="relative">
              <Search size={15} className="absolute left-3 top-[calc(50%+1px)] -translate-y-1/2 text-ink-400" />
              <input
                id="job-search-input"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Job title, company, skill or location"
                aria-label="Search jobs by title, company, skill, or location"
                className="w-full rounded-lg border border-ink-200 bg-white py-2.5 pl-9 pr-9 text-sm text-ink-900 shadow-2xs outline-none transition-all placeholder:text-ink-400 focus:border-signal-500 focus:ring-2 focus:ring-signal-500/15"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-[calc(50%+1px)] -translate-y-1/2 rounded-full p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-700"
                  title="Clear search"
                  aria-label="Clear search input"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>
          <div className="md:col-span-6">
            <RoleDropdownSelector
              label="Role"
              selectedRole={selectedRole}
              onRoleChange={setSelectedRole}
              roles={roleOptions}
              includeAllOption={true}
              allOptionLabel="All roles"
              className="[&_label]:mb-1.5 [&_label]:text-[11px] [&_label]:font-semibold [&_label]:normal-case [&_label]:tracking-normal [&>div:last-child]:gap-0"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 border-t border-ink-100 pt-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="block text-[11px] font-semibold text-ink-600">
            Location
            <select
              value={locationPreset}
              onChange={(e) => setLocationPreset(e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-ink-200 bg-white px-3 py-2.5 text-sm font-medium text-ink-800 shadow-2xs outline-none focus:border-signal-500"
            >
              <option value="ALL">All locations</option>
              <option value="Bengaluru">Bengaluru</option>
              <option value="Delhi NCR">Delhi NCR</option>
              <option value="Hyderabad">Hyderabad</option>
              <option value="Pune">Pune</option>
              <option value="Mumbai">Mumbai</option>
              <option value="Chennai">Chennai</option>
            </select>
          </label>
          <label className="block text-[11px] font-semibold text-ink-600">
            Career stage
            <select
              value={stageFilter}
              onChange={(e) => setStageFilter(e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-ink-200 bg-white px-3 py-2.5 text-sm font-medium text-ink-800 shadow-2xs outline-none focus:border-signal-500"
            >
              {CANONICAL_CAREER_STAGES.map((stage) => (
                <option key={stage.value} value={stage.value}>
                  {stage.label}{profile?.category === stage.value ? " (Your stage)" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-[11px] font-semibold text-ink-600">
            Work arrangement
            <select
              value={workplaceFilter}
              onChange={(e) => setWorkplaceFilter(e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-ink-200 bg-white px-3 py-2.5 text-sm font-medium text-ink-800 shadow-2xs outline-none focus:border-signal-500"
            >
              <option value="ALL">Any arrangement</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="on_site">On-site</option>
            </select>
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-x-5 gap-y-3 border-t border-ink-100 pt-3">
          {hasResume && (
            <label className="flex items-center gap-2 text-xs font-medium text-ink-700 cursor-pointer">
              <input
                type="checkbox"
                checked={onlyEligible}
                onChange={(e) => setOnlyEligible(e.target.checked)}
                className="rounded border-ink-300 text-signal-600 focus:ring-signal-500 cursor-pointer"
              />
              Eligible for my profile
            </label>
          )}
        </div>
      </div>

      {isLoading && <SkeletonCard count={4} />}

      {/* Low Inventory Note */}
      {!isLoading && totalCount > 0 && totalCount <= 3 && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 mb-3 text-xs text-amber-900 flex items-center justify-between gap-2 flex-wrap">
          <p>
            <span className="font-bold">Live Inventory Note:</span> Only {totalCount} live opening{totalCount === 1 ? "" : "s"} currently match this exact filter combination directly on employer ATS portals.
          </p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && visibleJobs.length === 0 && (
        <EmptyState
          icon={Briefcase}
          title={
            activeFilterCount > 0
              ? "No opportunities match your selected filters"
              : "No live postings currently available from connected employers"
          }
          description={
            activeFilterCount > 0
              ? "Try clearing filters or selecting another role."
              : "Connected employer ATS boards currently have no matching live openings. Check back later or broaden your search filters."
          }
          actionText={activeFilterCount > 0 ? "Reset Filters" : undefined}
          onAction={activeFilterCount > 0 ? resetAllFilters : undefined}
          secondaryActionText="Paste External Job Description"
          secondaryActionHref="/resume/tailor-custom"
        />
      )}

      {/* Results List */}
      {visibleJobs.length > 0 && (
        <div className="space-y-3">
          {/* Single Authoritative Count & Status Row */}
          <div className="flex items-center justify-between px-1 py-1 text-xs text-ink-600 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-ink-900">
                {onlyEligible
                  ? `Showing ${visibleJobs.length} eligible opening${visibleJobs.length === 1 ? "" : "s"}`
                  : `Showing ${visibleJobs.length} of ${totalCount} active opening${totalCount === 1 ? "" : "s"}`}
              </span>
              <span className="text-ink-400 hidden sm:inline">
                • Verified live from connected employer ATS boards
              </span>
            </div>
          </div>

          {visibleJobs.map((job) => (
            <JobMatchCard key={job.job_id} job={job} onViewDetail={handleSaveListState} />
          ))}

          {/* Progressive "Show More" Action */}
          {loadedJobs.length < totalCount ? (
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
                    <span>Loading more openings…</span>
                  </>
                ) : (
                  <span>Show More Openings</span>
                )}
              </button>
              <p className="text-[11px] text-ink-400">
                Showing {visibleJobs.length} of {totalCount} total openings matching your criteria
              </p>
            </div>
          ) : totalCount > 0 ? (
            <div className="mt-6 text-center py-4 border-t border-ink-100">
              <p className="text-xs text-ink-500 font-medium">
                All {totalCount} verified active opportunities matching your filters are loaded.
              </p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
