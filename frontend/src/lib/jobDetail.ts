import { apiClient } from "./apiClient";
import type { JobMatch } from "./jobs";

export type JobDetail = {
  id: string;
  source: string;
  title: string;
  company: string;
  company_description?: string | null;
  industry: string;
  description: string;
  jd_evidence_status?: "COMPLETE" | "INCOMPLETE" | string;
  jd_evidence_source?: string | null;
  skills_required: string[];
  skills_nice_to_have: string[];
  inferred_skills?: string[];
  experience_min: number | null;
  experience_max: number | null;
  experience_text?: string | null;
  job_type: string;
  location: string;
  is_remote: boolean;
  salary_min: number | null;
  salary_max: number | null;
  salary_disclosed: boolean;
  stipend_min: number | null;
  stipend_max?: number | null;
  stipend?: number | null;
  stipend_currency?: string | null;
  stipend_period?: string | null;
  stipend_unit?: string | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  salary_unit?: string | null;
  compensation_type?: string | null;
  compensation_text?: string | null;
  internship_duration_months: number | null;
  fresher_friendly: boolean;
  posted_days_ago: number;
  apply_url: string;
  source_url?: string | null;
  responsibilities: string[];
  qualifications?: string[];
  eligibility_text?: string | null;
  degree_requirements?: string[];
  graduation_year_requirements?: number[];
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
    skill_score?: number | null;
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
  missing_required_information?: string[];
  available_information?: string[];
  seniority?: string | null;
  registration_closing_date?: string | null;
  application_deadline?: string | null;
  end_date?: string | null;
};

export type JobMatchLookup = {
  status: "READY" | "RESUME_REQUIRED" | "RESUME_UNREADABLE" | "UNAVAILABLE";
  match: JobMatch | null;
  resume_version: number | null;
  message: string | null;
};

export async function getJobDetail(jobId: string): Promise<JobDetail> {
  const res = await apiClient.get<JobDetail>(`/jobs/${jobId}`);
  return res.data;
}

export async function getJobMatch(jobId: string): Promise<JobMatchLookup> {
  const res = await apiClient.get<JobMatchLookup>(`/matches/job/${jobId}`);
  return res.data;
}
