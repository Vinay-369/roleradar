import { apiClient } from "./apiClient";

export type UserPublic = {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  onboarding_completed: boolean;
};

const TOKEN_KEY = "roleradar_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function registerRequest(payload: {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
}) {
  const res = await apiClient.post<{ access_token: string }>("/auth/register", payload);
  return res.data.access_token;
}

export async function loginRequest(payload: { email: string; password: string }) {
  const res = await apiClient.post<{ access_token: string }>("/auth/login", payload);
  return res.data.access_token;
}

export async function requestPasswordReset(email: string): Promise<{ message: string; reset_token?: string }> {
  const res = await apiClient.post<{ message: string; reset_token?: string }>("/auth/forgot-password", { email });
  return res.data;
}

export async function resetPassword(token: string, newPassword: string): Promise<string> {
  const res = await apiClient.post<{ message: string }>("/auth/reset-password", {
    token,
    new_password: newPassword,
  });
  return res.data.message;
}

export async function fetchCurrentUser(): Promise<UserPublic> {
  const res = await apiClient.get<UserPublic>("/auth/me");
  return res.data;
}
