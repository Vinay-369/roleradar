import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api",
});

// Auth token attaches automatically once Phase 1 (auth) is built.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("roleradar_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
