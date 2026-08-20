import { apiClient } from "./apiClient";

export type ParseabilityIssue = { code: string; severity: string; message: string };

export type ParseabilityOut = {
  score: number;
  issues: ParseabilityIssue[];
  detected_sections: string[];
  missing_standard_sections: string[];
  contact_info_found: Record<string, boolean>;
  likely_multi_column: boolean;
  word_count: number;
};

export type MasterResumeOut = {
  id: string;
  version: number;
  file_name: string;
  file_type: string;
  parsed: {
    personal: { name: string | null; email: string | null; phone: string | null; github: string | null; linkedin: string | null; portfolio: string | null };
    summary: string | null;
    skills: string[];
    experience_raw: string[];
    projects_raw: string[];
    internships_raw: string[];
    education_raw: string[];
    certifications: string[];
    achievements: string[];
    links: string[];
  };
  parseability: ParseabilityOut;
  recruiter_impact: {
    score: number;
    bullets_analyzed: number;
    quantified_bullets: number;
    weak_verb_bullets: number;
    quantification_rate: number;
    issues: string[];
  };
  created_at: string;
};

export async function uploadResume(file: File): Promise<MasterResumeOut> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiClient.post<MasterResumeOut>("/resumes/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function getMasterResume(): Promise<MasterResumeOut | null> {
  const res = await apiClient.get<MasterResumeOut | null>("/resumes/master");
  return res.data;
}

export type Achievement = {
  id: string;
  title: string;
  description: string;
  metrics: string | null;
  skills_tags: string[];
  created_at: string;
};

export async function getAchievements(): Promise<Achievement[]> {
  const res = await apiClient.get<Achievement[]>("/resumes/achievements");
  return res.data;
}

export async function createAchievement(data: {
  title: string;
  description: string;
  metrics?: string;
  skills_tags: string[];
}): Promise<Achievement> {
  const res = await apiClient.post<Achievement>("/resumes/achievements", data);
  return res.data;
}

export async function deleteAchievement(id: string): Promise<void> {
  await apiClient.delete(`/resumes/achievements/${id}`);
}
