import { apiClient } from "./apiClient";

export type CompetencyStatus = "DEMONSTRATED" | "PARTIALLY_DEMONSTRATED" | "NO_RESUME_EVIDENCE";

export type CompetencyTier =
  | "FOUNDATION"
  | "CORE"
  | "DOMAIN_PROCESSING"
  | "TOOLS"
  | "CLOUD_SPECIALIZATION"
  | "ADVANCED";

export type CompetencyImportance = "CORE" | "COMMON" | "OPTIONAL";

export type CompetencyEvidence = {
  section: string;
  entity_name?: string | null;
  text: string;
  evidence_type: string;
  source_reference?: string | null;
};

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
  // Phase 16D Career Skill Intelligence fields
  tier?: CompetencyTier;
  status?: CompetencyStatus;
  importance?: CompetencyImportance;
  evidence?: CompetencyEvidence[];
  explanation?: string;
  evidence_type?: string;
};

export type CareerAlignmentSummary = {
  total: number;
  demonstrated: number;
  partially_demonstrated: number;
  no_resume_evidence: number;
};

export type CareerAlignment = {
  role: string;
  domain?: string | null;
  subdomain?: string | null;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  provenance: string;
  has_resume: boolean;
  message?: string | null;
  summary: CareerAlignmentSummary;
  competencies: SkillGap[];
};

export type CanonicalRole = {
  role: string;
  domain: string;
  subdomain: string;
  aliases: string[];
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

export async function getCareerAlignment(params?: string | { jobId?: string; role?: string }): Promise<CareerAlignment> {
  if (typeof params === "string") {
    const res = await apiClient.get<CareerAlignment>(`/learning/gaps/${params}`);
    return res.data;
  }
  const query = new URLSearchParams();
  if (params?.role) query.set("role", params.role);
  if (params?.jobId) query.set("job_id", params.jobId);
  const qs = query.toString();
  const res = await apiClient.get<CareerAlignment>(`/learning/gaps${qs ? `?${qs}` : ""}`);
  return res.data;
}

export async function getSkillGaps(params?: string | { jobId?: string; role?: string }): Promise<SkillGap[]> {
  const alignment = await getCareerAlignment(params);
  if (alignment && Array.isArray(alignment.competencies)) {
    return alignment.competencies;
  }
  if (Array.isArray(alignment)) {
    return alignment;
  }
  return [];
}

export async function getCanonicalRoles(): Promise<CanonicalRole[]> {
  const res = await apiClient.get<CanonicalRole[]>("/learning/roles");
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
