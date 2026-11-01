import axios from "axios";

type ApiErrorPayload = {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
};

export function getApiErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as ApiErrorPayload | null)?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
          return item.msg;
        }
        return "";
      })
      .filter(Boolean);
    if (messages.length > 0) return messages.join("; ");
  }
  return fallback;
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 30_000,
  headers: {
    Accept: "application/json",
  },
});

// Auth token attaches automatically once Phase 1 (auth) is built.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("roleradar_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new Event("roleradar:session-expired"));
    }
    return Promise.reject(error);
  },
);
