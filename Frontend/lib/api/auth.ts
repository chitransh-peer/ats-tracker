import { apiClient } from "./client";
import type { CurrentUserProfile, TokenPair } from "./types";

export function login(email: string, password: string) {
  return apiClient.post<TokenPair>("/auth/login", { email, password });
}

export function logout(refreshToken: string) {
  return apiClient.post<void>("/auth/logout", { refresh_token: refreshToken });
}

export function forgotPassword(email: string) {
  return apiClient.post<{ detail: string; reset_token: string | null }>("/auth/forgot-password", {
    email,
  });
}

export function resetPassword(token: string, newPassword: string) {
  return apiClient.post<void>("/auth/reset-password", {
    token,
    new_password: newPassword,
  });
}

export function me() {
  return apiClient.get<CurrentUserProfile>("/auth/me");
}

export function viewAsRole(roleName: string) {
  // Must use the real token even when already previewing another role —
  // otherwise switching roles mid-preview would try to authenticate with
  // the (unprivileged) preview token and get rejected.
  return apiClient.postAsRealUser<{ access_token: string; token_type: string }>("/auth/view-as", {
    role_name: roleName,
  });
}
