import { apiClient } from "./client";
import type { Permission, Role } from "./types";

export function listRoles() {
  return apiClient.get<Role[]>("/roles");
}

export function listPermissions() {
  return apiClient.get<Permission[]>("/permissions");
}
