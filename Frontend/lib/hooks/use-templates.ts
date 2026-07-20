import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as templatesApi from "@/lib/api/templates";

export function useTemplates() {
  return useQuery({
    queryKey: ["templates"],
    queryFn: templatesApi.listTemplates,
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: templatesApi.createTemplate,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["templates"] }),
  });
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      templateId,
      input,
    }: {
      templateId: string;
      input: { name?: string; subject?: string; body?: string };
    }) => templatesApi.updateTemplate(templateId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["templates"] }),
  });
}
