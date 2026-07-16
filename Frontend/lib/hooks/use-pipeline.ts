import { useQuery } from "@tanstack/react-query";
import { getDefaultStages } from "@/lib/api/pipeline";

export function useStages() {
  return useQuery({
    queryKey: ["pipeline", "stages"],
    queryFn: getDefaultStages,
  });
}
