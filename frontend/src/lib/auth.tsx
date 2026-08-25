import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "./nav";
import { api, clearTokens, getAccessToken, setTokens } from "./api";
import type { TokenResponse, User } from "./types";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  adminLogin: (email: string, password: string) => Promise<void>;
  completeSession: (data: TokenResponse) => void;
  logout: () => Promise<void>;
  hasPermission: (code: string) => boolean;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get<User>("/api/v1/users/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        clearTokens();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      hasPermission: (code: string) => Boolean(user?.permissions?.includes(code)),
      login: async (email: string, password: string) => {
        const { data } = await api.post<TokenResponse>("/api/v1/auth/login", { email, password });
        setTokens(data.access_token, data.refresh_token);
        setUser(data.user);
        navigate(data.user.permissions?.includes("admin.portal.access") ? "/admin/dashboard" : "/dashboard");
      },
      adminLogin: async (email: string, password: string) => {
        const { data } = await api.post<TokenResponse>("/api/v1/auth/admin/login", { email, password });
        setTokens(data.access_token, data.refresh_token);
        setUser(data.user);
        navigate("/admin/dashboard");
      },
      completeSession: (data: TokenResponse) => {
        setTokens(data.access_token, data.refresh_token);
        setUser(data.user);
        navigate("/dashboard");
      },
      logout: async () => {
        try {
          const refresh = sessionStorage.getItem("its.refresh_token");
          if (refresh) {
            await api.post("/api/v1/auth/logout", { refresh_token: refresh });
          }
        } catch {
          /* still clear locally */
        }
        clearTokens();
        setUser(null);
        navigate("/login");
      },
      refreshMe: async () => {
        const { data } = await api.get<User>("/api/v1/users/me");
        setUser(data);
      },
    }),
    [user, loading, navigate],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
