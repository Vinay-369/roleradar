import { apiClient } from "./apiClient";

export type InterviewQuestion = {
  question: string;
  category: string;
  star_hint: string | null;
  strategy?: string | null;
  sample_answer?: string | null;
  pitfalls?: string | null;
};

export type InterviewPrep = {
  job_title: string;
  company: string;
  questions: InterviewQuestion[];
  real_experiences_search_url: string;
};

export async function getInterviewQuestions(params?: string | { jobId?: string; role?: string; company?: string }): Promise<InterviewPrep> {
  if (typeof params === "string") {
    const res = await apiClient.get<InterviewPrep>(`/interview/${params}/questions`);
    return res.data;
  }
  const query = new URLSearchParams();
  if (params?.role) query.set("role", params.role);
  if (params?.company) query.set("company", params.company);
  if (params?.jobId) query.set("job_id", params.jobId);
  const qs = query.toString();
  const res = await apiClient.get<InterviewPrep>(`/interview/questions${qs ? `?${qs}` : ""}`);
  return res.data;
}
