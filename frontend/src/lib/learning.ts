import { apiClient } from "./apiClient";

export type SkillGap = {
  skill: string;
  priority: "CORE" | "SECONDARY" | "BONUS";
  reason: string;
  target_job_title: string;
  current_evidence: string;
  resources: string[];
  project_suggestion: string;
  estimated_days: number;
  candidate_status?: "MATCHED" | "PARTIAL" | "RELATED" | "MISSING" | null;
  source?: string;
  confidence?: "HIGH" | "MEDIUM" | "LOW";
  domain?: string;
  subdomain?: string;
};

export type Roadmap = {
  immediate: string[];
  week_1: string[];
  week_2: string[];
  month_1: string[];
  is_personalized?: boolean;
  roadmap_type?: "MARKET" | "CANDIDATE" | "JOB";
  personalization_status?: "NONE" | "LIMITED_EVIDENCE" | "PERSONALIZED";
  role_context?: string;
  role_confidence?: "HIGH" | "MEDIUM" | "LOW";
  provenance_source?: string;
  message?: string;
};

export async function getSkillGaps(params?: string | { jobId?: string; role?: string }): Promise<SkillGap[]> {
  if (typeof params === "string") {
    const res = await apiClient.get<SkillGap[]>(`/learning/gaps/${params}`);
    return res.data;
  }
  const query = new URLSearchParams();
  if (params?.role) query.set("role", params.role);
  if (params?.jobId) query.set("job_id", params.jobId);
  const qs = query.toString();
  const res = await apiClient.get<SkillGap[]>(`/learning/gaps${qs ? `?${qs}` : ""}`);
  return res.data;
}

export async function getRoadmap(params?: string | { jobId?: string; role?: string }): Promise<Roadmap> {
  if (typeof params === "string") {
    const res = await apiClient.get<Roadmap>(`/learning/roadmap/${params}`);
    return res.data;
  }
  const query = new URLSearchParams();
  if (params?.role) query.set("role", params.role);
  if (params?.jobId) query.set("job_id", params.jobId);
  const qs = query.toString();
  const res = await apiClient.get<Roadmap>(`/learning/roadmap${qs ? `?${qs}` : ""}`);
  return res.data;
}
