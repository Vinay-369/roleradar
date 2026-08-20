import { apiClient } from "./apiClient";

export type DashboardData = {
  role_readiness_index: number;
  ats_compatibility: number;
  skill_coverage: number;
  top_matches: {
    job_id: string; job_title: string; company: string;
    overall_score: number; apply_readiness: string; missing_skills: string[];
  }[];
  application_counts: Record<string, number>;
  recommended_next_action: string;
  resume_uploaded: boolean;
  onboarding_completed: boolean;
};

export async function getDashboard(): Promise<DashboardData> {
  const res = await apiClient.get<DashboardData>("/intelligence/dashboard");
  return res.data;
}
