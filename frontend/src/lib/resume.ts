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

export type ActionVerbOut = {
  score: number;
  total_bullets: number;
  strong_verb_bullets: number;
  weak_verb_bullets: number;
  power_verb_rate: number;
  strong_verbs_found: string[];
  weak_verbs_found: string[];
  issues: string[];
  recommendations: string[];
};

export type SkillCategoryDomain = {
  id: string;
  name: string;
  items: string[];
};

export type SkillsDepthOut = {
  score: number;
  total_skills: number;
  verified_skills_count: number;
  domain_coverage_count: number;
  categorized_domains: SkillCategoryDomain[];
  missing_domains: string[];
  issues: string[];
  recommendations: string[];
};

export type ATSStatusOut = {
  status: "passed" | "review" | "at_risk";
  label: string;
  color: string;
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
  action_verbs?: ActionVerbOut;
  skills_depth?: SkillsDepthOut;
  strict_ats_score?: number;
  ats_status?: ATSStatusOut;
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
