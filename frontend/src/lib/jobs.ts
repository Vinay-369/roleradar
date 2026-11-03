import { apiClient } from "./apiClient";

export const MAX_ACTIVE_POSTING_AGE_DAYS = 60;

export type EligibilityStatus =
  | "ELIGIBLE"
  | "LIKELY_ELIGIBLE"
  | "EXPERIENCE_MISMATCH"
  | "DEGREE_MISMATCH"
  | "GRADUATION_MISMATCH"
  | "LOCATION_MISMATCH"
  | "OPPORTUNITY_NOT_SUFFICIENTLY_SPECIFIED"
  | "UNKNOWN";

export type RealisticFitSignal =
  | "GOOD_FIT"
  | "POSSIBLE_FIT"
  | "SKILL_GAP"
  | "EXPERIENCE_GAP"
  | "UNKNOWN";

export type EligibilityResult = {
  status: EligibilityStatus;
  reasons: string[];
  checks: Record<string, string>;
  realistic_fit: RealisticFitSignal;
  fit_explanation?: string;
  candidate_experience_years?: number | null;
  required_experience_min?: number | null;
  required_experience_max?: number | null;
};

export type JobMatch = {
  job_id: string;
  job_title: string;
  company: string;
  overall_score: number | null;
  skill_score?: number | null;
  role_score?: number | null;
  experience_score?: number | null;
  location_score?: number | null;
  salary_score?: number | null;
  industry_score?: number | null;
  matched_skills: string[];
  partial_skills: string[];
  missing_skills: string[];
  skills_required?: string[];
  inferred_skills?: string[];
  apply_readiness?: "ready" | "fix_gaps" | "learn_first" | null;
  job_type: string;
  source: string;
  apply_url: string;
  location?: string;
  is_remote?: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_disclosed?: boolean;
  salary_currency?: string | null;
  salary_period?: string | null;
  salary_unit?: string | null;
  stipend_min?: number | null;
  stipend_max?: number | null;
  stipend_unit?: string | null;
  posted_days_ago?: number;
  experience_min?: number | null;
  experience_max?: number | null;
  experience_text?: string | null;
  industry?: string | null;
  created_at?: string;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  has_match?: boolean;
  verification_status?: string;
  verified_at?: string | null;
  last_verified_at?: string | null;
  verification_reason?: string | null;
  url_type?: string;
  is_direct_apply?: boolean;
  posted_at?: string | null;
  // Phase 12 India-First Opportunity Intelligence fields
  country?: string | null;
  opportunity_type?: string | null;
  candidate_suitability?: string | null;
  student_eligible?: boolean | null;
  fresher_eligible?: boolean | null;
  stipend?: number | null;
  stipend_currency?: string | null;
  stipend_period?: string | null;
  compensation_type?: string | null;
  compensation_text?: string | null;
  eligibility_text?: string | null;
  degree_requirements?: string[];
  graduation_year_requirements?: number[];
  workplace_type?: string | null;
  normalized_location?: string | null;
  eligibility?: EligibilityResult | null;
  realistic_fit?: RealisticFitSignal | null;
  fit_explanation?: string | null;
  factor_weights?: Record<string, number> | null;
  score_explanation?: string | null;
  canonical_role?: string | null;
  canonical_role_key?: string | null;
  role_domain?: string | null;
  contextual_requirements?: string[];
  quality_tier?: "PRIMARY" | "SECONDARY" | string | null;
  completeness_status?: string | null;
  missing_required_information?: string[];
  available_information?: string[];
  role_confidence?: string | null;
  recommendation_quality?: string | null;
  seniority?: string | null;
  fresher_friendly?: boolean;
  registration_closing_date?: string | null;
  application_deadline?: string | null;
  end_date?: string | null;
};

/**
 * Orders matches by the score the user sees on the card. Missing scores are
 * kept at the end, with newer postings breaking otherwise equal scores.
 */
export function sortMatchesByScore(matches: JobMatch[]): JobMatch[] {
  return [...matches].sort((a, b) => {
    const aScore = a.overall_score ?? Number.NEGATIVE_INFINITY;
    const bScore = b.overall_score ?? Number.NEGATIVE_INFINITY;
    return bScore - aScore
      || (a.posted_days_ago ?? Infinity) - (b.posted_days_ago ?? Infinity)
      || a.job_id.localeCompare(b.job_id);
  });
}

export function isWithinPostingAge(job: JobMatch, maxAgeDays: number): boolean {
  if (job.posted_at) {
    const postedAt = Date.parse(job.posted_at);
    if (!Number.isNaN(postedAt)) {
      const ageDays = Math.max(0, (Date.now() - postedAt) / 86_400_000);
      return ageDays <= maxAgeDays;
    }
  }

  if (typeof job.posted_days_ago === "number") {
    return job.posted_days_ago >= 0 && job.posted_days_ago <= maxAgeDays;
  }

  const lastSeenAt = job.last_seen_at || job.first_seen_at;
  if (!lastSeenAt) return false;
  const seenAt = Date.parse(lastSeenAt);
  if (Number.isNaN(seenAt)) return false;
  const ageDays = Math.max(0, (Date.now() - seenAt) / 86_400_000);
  return ageDays <= maxAgeDays;
}

export type JobQueryFilters = {
  jobType?: "full_time" | "internship";
  liveOnly?: boolean;
  opportunityType?: string;
  experienceTier?: string;
  locationPreset?: string;
  workplaceType?: string;
  region?: string;
  role?: string;
  domain?: string;
  stage?: string;
  search?: string;
  sortBy?: "recent" | "salary" | "stipend" | "match";
  maxPostedDays?: number;
  page?: number;
  pageSize?: number;
};

export type RecommendedMatchesResult = {
  items: JobMatch[];
  total: number;
};

export type LiveProviderSync = {
  provider: string;
  status: "success" | "partial" | "failed" | "timed_out" | "not_configured" | string;
  total_boards: number;
  fetched: number;
  verified_active: number;
  unique_requisitions: number;
  errors: string[];
  results?: Array<{ board: string; status: string; errors?: string[] }>;
};

export type LiveSyncReport = {
  status: "success" | "partial" | "failed" | "not_configured" | string;
  added_count: number;
  unique_requisitions: number;
  errors: string[];
  detail_enriched: number;
  detail_enrichment_failed: number;
  detail_enrichment_skipped: number;
  providers: LiveProviderSync[];
};

export async function syncLiveJobs(): Promise<LiveSyncReport> {
  const res = await apiClient.post<LiveSyncReport>("/jobs/sync", undefined, { timeout: 85_000 });
  return res.data;
}

export async function getRecommendedMatches(
  jobType?: "full_time" | "internship",
  liveOnly?: boolean,
  filters?: Partial<JobQueryFilters>
): Promise<RecommendedMatchesResult> {
  const params: Record<string, any> = {};
  if (jobType) params.job_type = jobType;
  if (liveOnly !== undefined) params.live_only = liveOnly;
  if (filters?.opportunityType) params.opportunity_type = filters.opportunityType;
  if (filters?.experienceTier) params.experience_tier = filters.experienceTier;
  if (filters?.locationPreset) params.location_preset = filters.locationPreset;
  if (filters?.workplaceType) params.workplace_type = filters.workplaceType;
  if (filters?.region) params.region = filters.region;
  if (filters?.role) params.role = filters.role;
  if (filters?.domain) params.domain = filters.domain;
  if (filters?.stage) params.stage = filters.stage;
  if (filters?.search) params.search = filters.search;
  if (filters?.sortBy) params.sort_by = filters.sortBy;
  if (filters?.maxPostedDays) params.max_posted_days = filters.maxPostedDays;
  if (filters?.page) params.page = filters.page;
  if (filters?.pageSize) params.page_size = filters.pageSize;

  const res = await apiClient.get<JobMatch[]>("/matches/recommended", { params });
  const rawTotal = res.headers["x-total-count"];
  const parsedTotal = rawTotal ? parseInt(rawTotal, 10) : Number.NaN;
  const page = filters?.page ?? 1;
  const pageSize = filters?.pageSize ?? 50;
  const total = Number.isFinite(parsedTotal)
    ? parsedTotal
    : res.data.length === pageSize
      ? page * pageSize + 1
      : (page - 1) * pageSize + res.data.length;
  return { items: res.data, total };
}

export type CreateCustomJobPayload = {
  company?: string;
  title?: string;
  jd_text: string;
};

export async function createCustomJob(payload: CreateCustomJobPayload): Promise<any> {
  const res = await apiClient.post("/jobs/custom", payload);
  return res.data;
}
