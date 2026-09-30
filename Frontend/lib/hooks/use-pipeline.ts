import { useQuery } from "@tanstack/react-query";
import { getDefaultStages, getPipelineBoard } from "@/lib/api/pipeline";

export function useStages() {
  return useQuery({
    queryKey: ["pipeline", "stages"],
    queryFn: getDefaultStages,
  });
}

/** Keyed under "applications" so moving a card refreshes the board. */
export function usePipelineBoard(jobId: string | null) {
  return useQuery({
    queryKey: ["applications", "board", jobId],
    queryFn: () => getPipelineBoard(jobId),
    placeholderData: (previous) => previous,
  });
}
