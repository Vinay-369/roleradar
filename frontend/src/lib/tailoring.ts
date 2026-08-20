import { apiClient } from "./apiClient";

export type ChangeStatus = "PENDING" | "APPROVED" | "REJECTED" | "NEEDS_USER_INPUT";

export type Change = {
  change_id: string;
  original: string;
  proposed: string;
  reason: string;
  source_evidence: string;
  confidence: number;
  status: ChangeStatus;
};

export type TailoredResume = {
  id: string;
  job_id: string;
  job_title: string;
  company: string;
  changes: Change[];
  is_finalized: boolean;
  final_text: string | null;
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

export async function listTailoredVersions(): Promise<TailoredResume[]> {
  const res = await apiClient.get<TailoredResume[]>("/tailoring");
  return res.data;
}

export async function updateChangeStatus(versionId: string, changeId: string, status: "APPROVED" | "REJECTED"): Promise<TailoredResume> {
  const res = await apiClient.put<TailoredResume>(`/tailoring/${versionId}/changes/${changeId}`, { status });
  return res.data;
}

export async function finalizeTailoring(versionId: string): Promise<TailoredResume> {
  const res = await apiClient.post<TailoredResume>(`/tailoring/${versionId}/finalize`);
  return res.data;
}
