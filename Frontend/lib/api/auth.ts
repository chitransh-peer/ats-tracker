import { apiClient } from "./client";
import type { CurrentUserProfile, TokenPair } from "./types";

export function login(email: string, password: string) {
  return apiClient.post<TokenPair>("/auth/login", { email, password });
}

export function logout(refreshToken: string) {
  return apiClient.post<void>("/auth/logout", { refresh_token: refreshToken });
}

export function me() {
  return apiClient.get<CurrentUserProfile>("/auth/me");
}
