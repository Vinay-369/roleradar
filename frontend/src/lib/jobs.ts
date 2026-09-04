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
};

export type JobQueryFilters = {
  jobType?: "full_time" | "internship";
  liveOnly?: boolean;
  opportunityType?: string;
  experienceTier?: string;
  locationPreset?: string;
  workplaceType?: string;
  region?: string;
};

export async function getRecommendedMatches(
  jobType?: "full_time" | "internship",
  liveOnly?: boolean,
  filters?: Partial<JobQueryFilters>
): Promise<JobMatch[]> {
  const params: Record<string, any> = {};
  if (jobType) params.job_type = jobType;
  if (liveOnly !== undefined) params.live_only = liveOnly;
  if (filters?.opportunityType) params.opportunity_type = filters.opportunityType;
  if (filters?.experienceTier) params.experience_tier = filters.experienceTier;
  if (filters?.locationPreset) params.location_preset = filters.locationPreset;
  if (filters?.workplaceType) params.workplace_type = filters.workplaceType;
  if (filters?.region) params.region = filters.region;

  const res = await apiClient.get<JobMatch[]>("/matches/recommended", { params });
  return res.data;
}
