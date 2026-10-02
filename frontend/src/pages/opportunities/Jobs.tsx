import { useState, useMemo, useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Briefcase, Sparkles, Search, FileText, RotateCcw, X, RefreshCw, SlidersHorizontal } from "lucide-react";
import {
  getRecommendedMatches,
  isWithinPostingAge,
  MAX_ACTIVE_POSTING_AGE_DAYS,
  syncLiveJobs,
  type JobMatch,
} from "../../lib/jobs";
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
  const [loadedJobs, setLoadedJobs] = useState<JobMatch[]>(
    restoredState?.loadedItems?.filter((job) => isWithinPostingAge(job, MAX_ACTIVE_POSTING_AGE_DAYS)) ?? [],
  );
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
        maxPostedDays: MAX_ACTIVE_POSTING_AGE_DAYS,
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
      setLoadedJobs(data.items.filter((job) => isWithinPostingAge(job, MAX_ACTIVE_POSTING_AGE_DAYS)));
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
        maxPostedDays: MAX_ACTIVE_POSTING_AGE_DAYS,
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
    <div className="mx-auto w-full max-w-7xl px-4 pt-5 pb-12 sm:px-6">
      {/* Header Bar */}
      <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-2">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-signal-500/20 bg-signal-500/10 text-signal-700"><Briefcase size={18} /></span>
            <h1 className="font-display text-xl font-bold text-ink-950 sm:text-2xl">Active Full-Time Openings</h1>
          </div>
          <p className="pl-11 text-xs text-ink-500">
            Verified direct opportunities sourced straight from official employer applicant tracking systems.
          </p>
        </div>

        <div className="flex shrink-0 flex-wrap items-center justify-start gap-2 sm:justify-end">
          <div role="group" aria-label="Job listing region" className="inline-flex h-10 items-center rounded-lg border border-slate-200 bg-slate-100 p-1 dark:border-slate-700 dark:bg-slate-800">
            <button type="button" onClick={() => setRegionScope("india")} aria-pressed={regionScope === "india"} className={`h-8 rounded-md px-3 text-xs font-semibold transition-colors ${regionScope === "india" ? "bg-white text-signal-700 shadow-xs dark:bg-slate-700 dark:text-white" : "text-slate-600 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white"}`}>🇮🇳 India</button>
            <button type="button" onClick={() => setRegionScope("global")} aria-pressed={regionScope === "global"} className={`h-8 rounded-md px-3 text-xs font-semibold transition-colors ${regionScope === "global" ? "bg-white text-signal-700 shadow-xs dark:bg-slate-700 dark:text-white" : "text-slate-600 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white"}`}>🌐 Global</button>
          </div>
          <button
            type="button"
            onClick={() => liveSync.mutate()}
            disabled={liveSync.isPending}
            className="inline-flex h-10 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border border-signal-200 bg-signal-50 px-3 text-xs font-semibold text-signal-800 transition-colors hover:bg-signal-100 disabled:opacity-60 dark:border-signal-900 dark:bg-signal-950/40 dark:text-signal-300 dark:hover:bg-signal-950/70"
            title={liveSync.error ? "Live listing refresh failed" : "Fetch the latest job listings"}
          >
            <RefreshCw size={13} className={liveSync.isPending ? "animate-spin" : ""} />
            <span>{liveSync.isPending ? "Refreshing…" : "Refresh live listings"}</span>
          </button>
          <Link
            to="/resume/tailor-custom"
            className="inline-flex h-10 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <FileText size={13} className="text-signal-600" />
            <span>Paste External JD</span>
          </Link>
          {liveSync.data && <span className="text-[11px] text-ink-500">Synced {liveSync.data.added_count}</span>}
          {liveSync.error && <span className="text-[11px] text-rose-700">Refresh failed</span>}

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

      <div className="mb-4 space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <SlidersHorizontal size={16} className="text-signal-600" />
            <h2 className="text-sm font-bold text-ink-900 dark:text-slate-100">Find the right opening</h2>
            <span className="hidden sm:inline text-xs text-ink-400">Search and narrow results</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-xs font-medium text-ink-700 cursor-pointer">
              <span>Sort by</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as "recent" | "salary" | "match")}
                className="h-10 rounded-lg border border-slate-200 bg-slate-50 px-3 text-xs font-semibold text-slate-800 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
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

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="relative">
            <label htmlFor="job-search-input" className="mb-1.5 block text-[11px] font-semibold text-ink-600">Keywords</label>
            <div className="relative">
              <Search size={15} className="absolute left-3 top-[calc(50%+1px)] -translate-y-1/2 text-ink-400" />
              <input
                id="job-search-input"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Job title, company, skill or location"
                aria-label="Search jobs by title, company, skill, or location"
                className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-9 text-sm text-slate-900 shadow-2xs outline-none transition-all placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500"
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
          <div>
            <RoleDropdownSelector
              label="Role"
              selectedRole={selectedRole}
              onRoleChange={setSelectedRole}
              roles={roleOptions}
              includeAllOption={true}
              allOptionLabel="All roles"
              className="[&_label]:mb-1.5 [&_label]:text-[11px] [&_label]:font-semibold [&_label]:normal-case [&_label]:tracking-normal [&_input[role=combobox]]:h-10 [&_input[role=combobox]]:bg-slate-50 [&_input[role=combobox]]:dark:bg-slate-800 [&_input[role=combobox]]:focus:ring-indigo-500/15 [&>div:last-child]:gap-0"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 border-t border-slate-200 pt-3 sm:grid-cols-2 lg:grid-cols-3 dark:border-slate-800">
          <label className="block text-[11px] font-semibold text-ink-600">
            Location
            <select
              value={locationPreset}
              onChange={(e) => setLocationPreset(e.target.value)}
              className="mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-800 shadow-2xs outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
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
              className="mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-800 shadow-2xs outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
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
              className="mt-1.5 h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-800 shadow-2xs outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="ALL">Any arrangement</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="on_site">On-site</option>
            </select>
          </label>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-3 dark:border-slate-800">
          {hasResume && (
            <label className="inline-flex cursor-pointer items-center gap-2.5 text-xs font-semibold text-slate-700 dark:text-slate-200">
              <input
                type="checkbox"
                checked={onlyEligible}
                onChange={(e) => setOnlyEligible(e.target.checked)}
                className="peer sr-only"
              />
              <span aria-hidden="true" className={`relative h-5 w-9 rounded-full transition-colors ${onlyEligible ? "bg-emerald-500 dark:bg-emerald-600" : "bg-slate-300 dark:bg-slate-600"}`}><span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${onlyEligible ? "translate-x-4" : "translate-x-0.5"}`} /></span>
              Eligible for my profile
            </label>
          )}
          <span className="text-[11px] text-slate-500 dark:text-slate-400">Sort and filters update listings automatically.</span>
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
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
            <div>
              <span className="text-sm font-semibold text-ink-900 dark:text-slate-100">
                {onlyEligible
                  ? `Showing ${visibleJobs.length} eligible opening${visibleJobs.length === 1 ? "" : "s"}`
                  : `Showing ${visibleJobs.length} of ${totalCount} active opening${totalCount === 1 ? "" : "s"}`}
              </span>
              <span className="ml-2 hidden text-xs text-slate-500 sm:inline dark:text-slate-400">
                Verified live from connected employer ATS boards
              </span>
            </div>
            <div className="w-full sm:w-40">
              <div className="mb-1 flex justify-between text-[10px] font-medium text-slate-500 dark:text-slate-400">
                <span>Loaded</span><span>{visibleJobs.length}/{totalCount}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                <div className="h-full rounded-full bg-indigo-600 transition-all" style={{ width: `${totalCount ? Math.min(100, (visibleJobs.length / totalCount) * 100) : 0}%` }} />
              </div>
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
                className="inline-flex h-11 min-w-52 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 text-sm font-semibold text-slate-800 shadow-sm transition-all hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-800 hover:shadow disabled:cursor-not-allowed disabled:opacity-50 active:scale-[0.99] dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:border-indigo-700 dark:hover:bg-indigo-950/40 dark:hover:text-indigo-200"
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
