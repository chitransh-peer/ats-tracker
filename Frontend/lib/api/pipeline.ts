import { apiClient } from "./client";
import type { StageTemplate } from "./types";

export function getDefaultStages() {
  return apiClient.get<StageTemplate>("/pipeline/stages");
}
