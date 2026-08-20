import { apiClient } from "./apiClient";

export type MatchGuidance = {
  status: "ideal" | "over_optimized" | "good" | "needs_work";
  label: string;
  message: string;
  target_range: string;
};

export type PlatformWarning = {
  severity: "high" | "medium" | "info";
  title: string;
  message: string;
};

export type PlatformCompliance = {
  platform: string;
  platform_name: string;
  compliance_score: number;
  is_compliant: boolean;
  warnings: PlatformWarning[];
  tips: string[];
};

export type ATSScore = {
  overall: number;
  keyword_coverage: number;
  required_skills: number;
  role_alignment: number;
  structure: number;
  formatting: number;
  readability: number;
  job_title: string;
  company: string;
  keyword_density?: number;
  over_optimization_warning?: boolean;
  match_guidance?: MatchGuidance;
  platform_compliance?: PlatformCompliance;
};

export async function getATSScore(jobId: string, platform?: string): Promise<ATSScore> {
  const params: Record<string, string> = {};
  if (platform) params.platform = platform;
  const res = await apiClient.get<ATSScore>(`/intelligence/ats/${jobId}`, { params });
  return res.data;
}
