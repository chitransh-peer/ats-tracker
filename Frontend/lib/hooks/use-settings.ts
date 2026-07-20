import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as settingsApi from "@/lib/api/settings";

export function useOrganizationSettings() {
  return useQuery({
    queryKey: ["settings", "organization"],
    queryFn: settingsApi.getOrganizationSettings,
  });
}

export function useUpdateOrganizationSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: settingsApi.updateOrganizationSettings,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings", "organization"] }),
  });
}
