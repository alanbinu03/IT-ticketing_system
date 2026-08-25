import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const ACCESS_KEY = "its.access_token";
const REFRESH_KEY = "its.refresh_token";

function apiBase(): string {
  const explicit = import.meta.env.VITE_API_URL as string | undefined;
  if (explicit && explicit.trim()) return explicit.replace(/\/$/, "");
  return "";
}

export const api = axios.create({
  baseURL: apiBase(),
  headers: { "Content-Type": "application/json" },
  paramsSerializer: { indexes: null },
});

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  sessionStorage.setItem(ACCESS_KEY, access);
  sessionStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}

api.interceptors.request.use((config) => {
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    config.headers.delete("Content-Type");
  }
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<string> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const status = error.response?.status;
    const url = original?.url ?? "";
    if (status === 401 && !original?._retry && !url.includes("/auth/login") && !url.includes("/auth/admin/login") && !url.includes("/auth/refresh")) {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        clearTokens();
        return Promise.reject(error);
      }
      original._retry = true;
      try {
        if (!refreshPromise) {
          refreshPromise = api
            .post("/api/v1/auth/refresh", { refresh_token: refreshToken })
            .then((res) => {
              setTokens(res.data.access_token, res.data.refresh_token);
              return res.data.access_token as string;
            })
            .finally(() => {
              refreshPromise = null;
            });
        }
        const newAccess = await refreshPromise;
        original.headers.Authorization = `Bearer ${newAccess}`;
        return api(original);
      } catch (refreshError) {
        clearTokens();
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  },
);

export type ApiError = {
  error: { code: string; message: string };
};

export function getErrorMessage(err: unknown, fallback = "Request failed"): string {
  const axiosErr = err as AxiosError<ApiError>;
  return axiosErr.response?.data?.error?.message ?? fallback;
}
