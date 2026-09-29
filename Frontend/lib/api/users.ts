import { apiClient } from "./client";
import type { InvitedUser, User } from "./types";

/** Id and name of every active user; readable by anyone who can see jobs,
 * for the job form's owner pickers. */
export function listUserOptions() {
  return apiClient.get<{ id: string; full_name: string }[]>("/users/options");
}

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

/** Permanently removes the account. Not the same as deactivating. */
export function deleteUser(userId: string) {
  return apiClient.delete<void>(`/users/${userId}`);
}
