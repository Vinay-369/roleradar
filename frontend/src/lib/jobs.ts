import { apiClient } from "./apiClient";

export type JobMatch = {
  job_id: string;
  job_title: string;
  company: string;
  overall_score: number;
  skill_score: number;
  role_score: number;
  experience_score: number;
  location_score: number;
  salary_score: number;
  industry_score: number;
  matched_skills: string[];
  partial_skills: string[];
  missing_skills: string[];
  apply_readiness: "ready" | "fix_gaps" | "learn_first";
  job_type: string;
  source: string;
  apply_url: string;
  location?: string;
  is_remote?: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  stipend_min?: number | null;
  stipend_max?: number | null;
};

export async function getRecommendedMatches(jobType?: "full_time" | "internship", liveOnly?: boolean): Promise<JobMatch[]> {
  const params: Record<string, any> = {};
  if (jobType) params.job_type = jobType;
  if (liveOnly !== undefined) params.live_only = liveOnly;
  const res = await apiClient.get<JobMatch[]>("/matches/recommended", { params });
  return res.data;
}
