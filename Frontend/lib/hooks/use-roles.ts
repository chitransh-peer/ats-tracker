import { useQuery } from "@tanstack/react-query";
import * as rolesApi from "@/lib/api/roles";

export function useRoles() {
  return useQuery({
    queryKey: ["roles"],
    queryFn: rolesApi.listRoles,
  });
}

export function usePermissions() {
  return useQuery({
    queryKey: ["permissions"],
    queryFn: rolesApi.listPermissions,
  });
}
