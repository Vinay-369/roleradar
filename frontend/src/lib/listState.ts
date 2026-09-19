import type { JobMatch } from "./jobs";

export interface OpportunityListState {
  regionScope: "india" | "global";
  includeBenchmarks: boolean;
  searchQuery: string;
  selectedRole: string;
  locationPreset: string;
  stageFilter: string;
  workplaceFilter: string;
  onlyEligible: boolean;
  sortBy: string;
  page: number;
  loadedItems: JobMatch[];
  totalCount: number;
  scrollY: number;
  timestamp: number;
}

const JOBS_STORAGE_KEY = "roleradar_jobs_list_state";
const INTERNSHIPS_STORAGE_KEY = "roleradar_internships_list_state";
const DETAIL_NAV_FLAG_KEY = "roleradar_detail_nav_source";

export function saveListState(
  type: "jobs" | "internships",
  state: Omit<OpportunityListState, "timestamp">
): void {
  try {
    const payload: OpportunityListState = {
      ...state,
      timestamp: Date.now(),
    };
    const key = type === "jobs" ? JOBS_STORAGE_KEY : INTERNSHIPS_STORAGE_KEY;
    sessionStorage.setItem(key, JSON.stringify(payload));
  } catch (err) {
    console.warn("Could not save list state to sessionStorage", err);
  }
}

export function loadListState(type: "jobs" | "internships"): OpportunityListState | null {
  try {
    const key = type === "jobs" ? JOBS_STORAGE_KEY : INTERNSHIPS_STORAGE_KEY;
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as OpportunityListState;
    // Expire state after 30 minutes
    if (Date.now() - parsed.timestamp > 30 * 60 * 1000) {
      sessionStorage.removeItem(key);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function clearListState(type: "jobs" | "internships"): void {
  try {
    const key = type === "jobs" ? JOBS_STORAGE_KEY : INTERNSHIPS_STORAGE_KEY;
    sessionStorage.removeItem(key);
  } catch {
    // Ignore storage errors
  }
}

export function markNavigatedToDetail(source: "jobs" | "internships"): void {
  try {
    sessionStorage.setItem(DETAIL_NAV_FLAG_KEY, source);
  } catch {
    // Ignore storage errors
  }
}

export function consumeNavigatedToDetail(expected: "jobs" | "internships"): boolean {
  try {
    const current = sessionStorage.getItem(DETAIL_NAV_FLAG_KEY);
    if (current === expected) {
      sessionStorage.removeItem(DETAIL_NAV_FLAG_KEY);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}
