import { apiClient } from "./apiClient";

export type ChangeStatus = "PENDING" | "APPROVED" | "REJECTED" | "NEEDS_USER_INPUT";

export type Change = {
  change_id: string;
  section?: string;
  change_type?: "TEXT_REWRITE" | "SKILL_REORDER" | "KEYWORD_INJECTION" | "SECTION_REORDER";
  original: string;
  proposed: string;
  reason: string;
  source_evidence: string;
  confidence: number;
  status: ChangeStatus;
  target_bullet_index?: number | null;
  fabrication_warning?: string | null;
  before_order?: string[] | null;
  after_order?: string[] | null;
};

export type TailoredScores = {
  overall: number;
  keyword_coverage: number;
  required_skills: number;
  role_alignment: number;
  structure: number;
  formatting: number;
  readability: number;
  keyword_density: number;
  parseability: number;
  recruiter_impact: number;
  master_overall?: number | null;
  score_delta?: number;
  score_warning?: string | null;
};

export type ValidationSummary = {
  protected_sections_intact: boolean;
  anti_fabrication_passed: boolean;
  one_page_fit: boolean;
  page_count: number;
  score_improvement: boolean;
  all_checks_passed: boolean;
  errors?: string[];
};

export type CandidateClassification = {
  classification: string;
  career_profile?: string | null;
  experience_level: string;
  experience_depth: string;
  project_depth: string;
  internship_presence: string;
  leadership_evidence: string;
  professional_role_count: number;
  career_continuity: string;
  years_of_experience: number;
  is_student: boolean;
  has_leadership_evidence: boolean;
  confidence: number;
};

export type ResumeStrategy = {
  candidate_type: string;
  template_variant: string;
  highlight_education_top: boolean;
  section_priority: string[];
  max_bullets_per_entry: number;
  emphasize_projects: boolean;
  recommended_length_pages: number;
  focus_areas: string[];
};

export type RequirementEvidenceMapping = {
  requirement_id: string;
  requirement_text: string;
  category: string;
  status: "EXACT_MATCH" | "SUPPORTED" | "RELATED" | "PARTIAL" | "MISSING" | "CONFLICTING";
  matched_skills: string[];
  matched_entity_ids: string[];
  relevance_score: number;
  notes: string;
};

export type ATSReadabilityFindings = {
  factual_validation?: {
    is_valid: boolean;
    verified_claims_count: number;
    unverified_claims: string[];
    boundary_violations: string[];
    protected_sections_intact: boolean;
  };
  ats_format_validation?: {
    overall_ats_score: number;
    standard_headings_score: number;
    section_order_score: number;
    bullet_consistency_score: number;
    date_consistency_score: number;
    readability_score: number;
    keyword_stuffing_risk: boolean;
    length_status: string;
    unusual_symbols_detected: string[];
    parsing_risks: string[];
    layout_risks: string[];
    missing_critical_sections: string[];
    actionable_recommendations: string[];
  };
};

export type TailoredResume = {
  id: string;
  job_id: string;
  job_title: string;
  company: string;
  changes: Change[];
  is_finalized: boolean;
  final_text: string | null;
  parsed?: Record<string, any> | null;
  audit?: Record<string, any> | null;
  tailored_scores?: TailoredScores | null;
  sections_evaluated?: string[];
  sections_changed?: string[];
  unmatched_gaps?: string[];
  validation_summary?: ValidationSummary | null;
  one_page_fit?: boolean | null;
  candidate_classification?: CandidateClassification | null;
  resume_strategy?: ResumeStrategy | null;
  evidence_mapping?: RequirementEvidenceMapping[] | null;
  matched_skills?: string[] | null;
  missing_skills?: string[] | null;
  partial_skills?: string[] | null;
  ats_readability_findings?: ATSReadabilityFindings | null;
  created_at: string;
};

export async function generateTailoring(jobId: string): Promise<TailoredResume> {
  const res = await apiClient.post<TailoredResume>("/tailoring/generate", { job_id: jobId });
  return res.data;
}

export async function generateCustomTailoring(company: string, roleTitle: string, jdText: string): Promise<TailoredResume> {
  const res = await apiClient.post<TailoredResume>("/tailoring/generate", {
    custom_company: company,
    custom_role_title: roleTitle,
    custom_jd_text: jdText,
  });
  return res.data;
}

export async function getTailoredVersion(versionId: string): Promise<TailoredResume> {
  const res = await apiClient.get<TailoredResume>(`/tailoring/${versionId}`);
  return res.data;
}

export async function getTailoredVersionForJob(jobId: string): Promise<TailoredResume | null> {
  try {
    const res = await apiClient.get<TailoredResume>(`/tailoring/job/${jobId}`);
    return res.data;
  } catch (err: any) {
    if (err.response?.status === 404) return null;
    throw err;
  }
}

export async function listTailoredVersions(): Promise<TailoredResume[]> {
  const res = await apiClient.get<TailoredResume[]>("/tailoring");
  return res.data;
}

export async function updateChangeStatus(versionId: string, changeId: string, status: "APPROVED" | "REJECTED"): Promise<TailoredResume> {
  const res = await apiClient.put<TailoredResume>(`/tailoring/${versionId}/changes/${changeId}`, { status });
  return res.data;
}

export async function updateParsedResume(versionId: string, parsed: Record<string, any>): Promise<TailoredResume> {
  const res = await apiClient.put<TailoredResume>(`/tailoring/${versionId}/resume`, { parsed });
  return res.data;
}

export async function finalizeTailoring(versionId: string): Promise<TailoredResume> {
  const res = await apiClient.post<TailoredResume>(`/tailoring/${versionId}/finalize`);
  return res.data;
}

export async function deleteTailoredVersion(versionId: string): Promise<void> {
  await apiClient.delete(`/tailoring/${versionId}`);
}

