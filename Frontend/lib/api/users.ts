import { apiClient } from "./client";
import type { User } from "./types";

export function listUsers() {
  return apiClient.get<User[]>("/users");
}

export function inviteUser(email: string, roleName: string) {
  return apiClient.post<{ email: string; role_name: string; invitation_token: string }>("/users", {
    email,
    role_name: roleName,
  });
}

export function updateUser(userId: string, input: { full_name?: string; is_active?: boolean }) {
  return apiClient.patch<User>(`/users/${userId}`, input);
}

export function assignRoles(userId: string, roleNames: string[]) {
  return apiClient.post<User>(`/users/${userId}/roles`, { role_names: roleNames });
}
