import { apiClient } from "./client";
import type { InvitedUser, User } from "./types";

export function listUsers() {
  return apiClient.get<User[]>("/users");
}

export function inviteUser(email: string, fullName: string, roleName: string) {
  return apiClient.post<InvitedUser>("/users", {
    email,
    full_name: fullName,
    role_name: roleName,
  });
}

export function updateUser(userId: string, input: { full_name?: string; is_active?: boolean }) {
  return apiClient.patch<User>(`/users/${userId}`, input);
}

export function assignRoles(userId: string, roleNames: string[]) {
  return apiClient.post<User>(`/users/${userId}/roles`, { role_names: roleNames });
}
