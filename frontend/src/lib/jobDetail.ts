import { apiClient } from "./apiClient";

export type JobDetail = {
  id: string;
  source: string;
  title: string;
  company: string;
  industry: string;
  description: string;
  skills_required: string[];
  skills_nice_to_have: string[];
  experience_min: number;
  experience_max: number;
  job_type: string;
  location: string;
  is_remote: boolean;
  salary_min: number | null;
  salary_max: number | null;
  salary_disclosed: boolean;
  stipend_min: number | null;
  compensation_type?: string | null;
  compensation_text?: string | null;
  internship_duration_months: number | null;
  fresher_friendly: boolean;
  posted_days_ago: number;
  apply_url: string;
  responsibilities: string[];
  qualifications?: string[];
  verification_status?: string;
  verified_at?: string | null;
  last_verified_at?: string | null;
  verification_reason?: string | null;
  url_type?: string;
  is_direct_apply?: boolean;
  posted_at?: string | null;
  contextual_requirements?: string[];
  canonical_role?: string | null;
  canonical_role_key?: string | null;
  role_domain?: string | null;
  opportunity_type?: string | null;
  workplace_type?: string | null;
  eligibility?: {
    status: string;
    reasons: string[];
    checks?: Record<string, string>;
    realistic_fit?: string;
    fit_explanation?: string;
  } | null;
  match?: {
    overall_score: number;
    skills_score?: number;
    experience_score?: number;
    matched_skills?: string[];
    missing_skills?: string[];
    summary?: string;
  } | null;
  realistic_fit?: string | null;
  student_eligible?: boolean;
  fresher_eligible?: boolean;
  completeness_status?: string | null;
  recommendation_quality?: string | null;
  seniority?: string | null;
};

export async function getJobDetail(jobId: string): Promise<JobDetail> {
  const res = await apiClient.get<JobDetail>(`/jobs/${jobId}`);
  return res.data;
}
