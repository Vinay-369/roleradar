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
  status: "EXACT_MATCH" | "STRONG_MATCH" | "SUPPORTED" | "RELATED" | "PARTIAL" | "WEAK" | "MISSING" | "CONFLICTING";
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
  user_modified?: boolean | null;
  created_at: string;
};

export type EvidenceBadgeInfo = {
  label: string;
  style: string;
  iconType: "alert" | "edit" | "check" | "info";
};

export function getEvidenceBadge(version?: {
  changes?: Array<{ status?: string }> | null;
  evidence_mapping?: Array<{ status?: string }> | null;
  user_modified?: boolean | null;
} | null): EvidenceBadgeInfo {
  if (!version) {
    return {
      label: "No Verified JD Evidence",
      style: "bg-ink-100 text-ink-600 border-ink-200",
      iconType: "info",
    };
  }

  const needsConfirmationCount = (version.changes || []).filter(
    (c) => c.status === "NEEDS_USER_INPUT"
  ).length;

  // 1. Any NEEDS_USER_INPUT change takes precedence over all other states (including user_modified)
  if (needsConfirmationCount > 0) {
    return {
      label: `Confirmation Needed (${needsConfirmationCount})`,
      style: "bg-amber-500/10 text-amber-700 border-amber-500/20",
      iconType: "alert",
    };
  }

  // 2. User-modified content with no unresolved confirmation warnings
  if (version.user_modified) {
    return {
      label: "User Modified • Baseline Evidence Preserved",
      style: "bg-purple-500/10 text-purple-700 border-purple-500/20",
      iconType: "edit",
    };
  }

  const mappings = version.evidence_mapping || [];

  // 3. Empty evidence_mapping must NOT fall through to the fully-grounded state
  if (mappings.length === 0) {
    return {
      label: "No Verified JD Evidence",
      style: "bg-ink-100 text-ink-600 border-ink-200",
      iconType: "info",
    };
  }

  const verifiedCount = mappings.filter(
    (m) => m.status === "EXACT_MATCH" || m.status === "SUPPORTED"
  ).length;

  // 4. Evidence mapping exists but has zero EXACT_MATCH/SUPPORTED evidence
  if (verifiedCount === 0) {
    return {
      label: "No Verified JD Evidence",
      style: "bg-ink-100 text-ink-600 border-ink-200",
      iconType: "info",
    };
  }

  // 5. Mixed evidence (some verified/supported, some missing/partial/related)
  if (verifiedCount < mappings.length) {
    return {
      label: "Partially Evidence-Grounded",
      style: "bg-teal-500/10 text-teal-700 border-teal-500/20",
      iconType: "check",
    };
  }

  // 6. Fully supported / high evidence alignment with no unresolved confirmation
  return {
    label: "Evidence Grounded",
    style: "bg-signal-500/10 text-signal-700 border-signal-500/20",
    iconType: "check",
  };
}

export type RequirementStatusInfo = {
  label: string;
  style: string;
};

export function getRequirementStatusInfo(status?: string): RequirementStatusInfo {
  switch (status) {
    case "EXACT_MATCH":
      return {
        label: "Direct Match",
        style: "bg-signal-500/10 text-signal-700 border-signal-500/20",
      };
    case "STRONG_MATCH":
      return {
        label: "Strong Match",
        style: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
      };
    case "SUPPORTED":
      return {
        label: "Supported",
        style: "bg-teal-500/10 text-teal-700 border-teal-500/20",
      };
    case "PARTIAL":
      return {
        label: "Partial",
        style: "bg-amber-500/10 text-amber-700 border-amber-500/20",
      };
    case "RELATED":
      return {
        label: "Related",
        style: "bg-amber-500/10 text-amber-700 border-amber-500/20",
      };
    case "WEAK":
      return {
        label: "Weak Match",
        style: "bg-orange-500/10 text-orange-700 border-orange-500/20",
      };
    case "MISSING":
      return {
        label: "Missing",
        style: "bg-alert-500/10 text-alert-700 border-alert-500/20",
      };
    case "CONFLICTING":
      return {
        label: "Conflict",
        style: "bg-rose-500/10 text-rose-700 border-rose-500/20",
      };
    default:
      return {
        label: status ? status.replace(/_/g, " ") : "Unknown",
        style: "bg-ink-100 text-ink-700 border-ink-200",
      };
  }
}

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

