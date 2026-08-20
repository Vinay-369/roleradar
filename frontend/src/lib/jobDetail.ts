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
  internship_duration_months: number | null;
  fresher_friendly: boolean;
  posted_days_ago: number;
  apply_url: string;
  responsibilities: string[];
};

export async function getJobDetail(jobId: string): Promise<JobDetail> {
  const res = await apiClient.get<JobDetail>(`/jobs/${jobId}`);
  return res.data;
}
