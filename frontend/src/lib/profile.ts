import { apiClient } from "./apiClient";

export type Profile = {
  category: "FRESHER" | "EXPERIENCED" | "CAREER_SWITCHER" | "INTERNSHIP_SEEKER";
  experience_years: number;
  current_role: string | null;
  current_company: string | null;
  target_roles: string[];
  industries: string[];
  min_lpa: number | null;
  preferred_locations: string[];
  remote_preference: "remote" | "hybrid" | "onsite" | "any";
  internship_interested: boolean;
  min_stipend: number | null;
  internship_duration_months: number | null;
  cgpa: number | null;
  tier_college: boolean;
  career_brief: string | null;
  github: string | null;
  linkedin: string | null;
  portfolio: string | null;
  consent_text: string;
  auto_apply_settings: { tier: string; min_match_score: number; max_per_day: number };
};

export async function getProfile(): Promise<Profile | null> {
  const res = await apiClient.get<Profile | null>("/profile/me");
  return res.data;
}

export async function updateProfile(data: Partial<Profile>): Promise<Profile> {
  const res = await apiClient.post<Profile>("/profile/onboarding/complete", data);
  return res.data;
}
