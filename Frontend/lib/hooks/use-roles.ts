import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as rolesApi from "@/lib/api/roles";
import type { Permission } from "@/lib/api/types";

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

export function useUpdateRolePermissions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ roleId, permissions }: { roleId: string; permissions: Permission[] }) =>
      rolesApi.updateRolePermissions(roleId, permissions),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["roles"] }),
  });
}
