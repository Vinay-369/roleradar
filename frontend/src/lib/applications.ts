import { apiClient } from "./apiClient";

export type ApplicationStatus =
  | "SAVED" | "TAILORED" | "QUEUED" | "APPLIED" | "SHORTLISTED" | "VIEWED" | "INTERVIEW" | "OFFER" | "REJECTED" | "WITHDRAWN";

export type Application = {
  id: string;
  job_id: string;
  job_title: string;
  company: string;
  apply_url: string;
  tailored_resume_id: string | null;
  status: ApplicationStatus;
  match_score_at_save: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type ApplicationPackage = {
  job_title: string;
  company: string;
  apply_url: string;
  resume_text: string | null;
  resume_source: "tailored" | "master" | "none";
  cover_letter: string | null;
  checklist: string[];
  tailored_version_id?: string | null;
};

export async function saveApplication(jobId: string, tailoredResumeId?: string): Promise<Application> {
  const res = await apiClient.post<Application>("/applications", {
    job_id: jobId,
    tailored_resume_id: tailoredResumeId ?? null,
  });
  return res.data;
}

export async function listApplications(): Promise<Application[]> {
  const res = await apiClient.get<Application[]>("/applications");
  return res.data;
}

export async function updateApplicationStatus(id: string, status: ApplicationStatus): Promise<Application> {
  const res = await apiClient.put<Application>(`/applications/${id}`, { status });
  return res.data;
}

export async function updateApplication(
  id: string,
  updates: { status?: ApplicationStatus; notes?: string }
): Promise<Application> {
  const res = await apiClient.put<Application>(`/applications/${id}`, updates);
  return res.data;
}

export async function getApplicationPackage(id: string): Promise<ApplicationPackage> {
  const res = await apiClient.get<ApplicationPackage>(`/applications/${id}/package`);
  return res.data;
}

export async function deleteApplication(id: string): Promise<void> {
  await apiClient.delete(`/applications/${id}`);
}

export async function recordApplicationSubmission(jobId: string, tailoredResumeId?: string): Promise<Application> {
  const apps = await listApplications();
  const existing = apps.find((a) => a.job_id === jobId);
  if (existing) {
    return await updateApplication(existing.id, {
      status: "APPLIED",
    });
  }
  const created = await saveApplication(jobId, tailoredResumeId);
  return await updateApplication(created.id, { status: "APPLIED" });
}
