"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { login as apiLogin, logout as apiLogout, me, viewAsRole as apiViewAsRole } from "@/lib/api/auth";
import {
  clearTokens,
  clearViewAsToken,
  getAccessToken,
  getViewAsRole,
  setTokens,
  setViewAsToken,
} from "@/lib/api/client";
import type { CurrentUserProfile } from "@/lib/api/types";

interface AuthContextValue {
  user: CurrentUserProfile | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  viewAsRole: string | null;
  startViewAs: (roleName: string) => Promise<void>;
  exitViewAs: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [viewAsRole, setViewAsRoleState] = useState<string | null>(null);

  useEffect(() => {
    setViewAsRoleState(getViewAsRole());
  }, []);

  const loadUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const profile = await me();
      setUser(profile);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiLogin(email, password);
    setTokens(tokens.access_token, tokens.refresh_token);
    const profile = await me();
    setUser(profile);
  }, []);

  const logout = useCallback(() => {
    const refreshToken = localStorage.getItem("ats_refresh_token");
    if (refreshToken) {
      apiLogout(refreshToken).catch(() => {
        // best-effort server-side revocation; local logout proceeds regardless
      });
    }
    clearTokens();
    setUser(null);
    window.location.href = "/auth/login";
  }, []);

  const startViewAs = useCallback(async (roleName: string) => {
    try {
      const { access_token } = await apiViewAsRole(roleName);
      setViewAsToken(access_token, roleName);
      setViewAsRoleState(roleName);
      window.location.reload();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not start role preview";
      window.alert(message);
    }
  }, []);

  const exitViewAs = useCallback(() => {
    clearViewAsToken();
    setViewAsRoleState(null);
    window.location.reload();
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, viewAsRole, startViewAs, exitViewAs }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
