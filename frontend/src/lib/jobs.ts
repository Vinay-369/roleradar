import { apiClient } from "./apiClient";

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
  apply_readiness?: "ready" | "fix_gaps" | "learn_first" | null;
  job_type: string;
  source: string;
  apply_url: string;
  location?: string;
  is_remote?: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  stipend_min?: number | null;
  stipend_max?: number | null;
  posted_days_ago?: number;
  experience_min?: number | null;
  experience_max?: number | null;
  industry?: string | null;
  created_at?: string;
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
  salary_currency?: string | null;
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
  completeness_status?: string | null;
  quality_tier?: "PRIMARY" | "SECONDARY" | string | null;
  role_confidence?: string | null;
  recommendation_quality?: string | null;
  seniority?: string | null;
  fresher_friendly?: boolean;
};

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
  sortBy?: "recent" | "match" | "salary" | "stipend";
  maxPostedDays?: number;
  includeBenchmarks?: boolean;
  page?: number;
  pageSize?: number;
};

export type RecommendedMatchesResult = {
  items: JobMatch[];
  total: number;
};

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
  if (filters?.includeBenchmarks !== undefined) params.include_benchmarks = filters.includeBenchmarks;
  if (filters?.page) params.page = filters.page;
  if (filters?.pageSize) params.page_size = filters.pageSize;

  const res = await apiClient.get<JobMatch[]>("/matches/recommended", { params });
  const rawTotal = res.headers["x-total-count"];
  const parsedTotal = rawTotal ? parseInt(rawTotal, 10) : res.data.length;
  const total = isNaN(parsedTotal) ? res.data.length : parsedTotal;
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

