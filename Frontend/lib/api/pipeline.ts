import { apiClient } from "./client";
import type { PipelineBoard, StageTemplate } from "./types";

export function getDefaultStages() {
  return apiClient.get<StageTemplate>("/pipeline/stages");
}

/** Exact stage counts plus the newest cards, for every job or for one. */
export function getPipelineBoard(jobId?: string | null) {
  return apiClient.get<PipelineBoard>(`/pipeline/board${jobId ? `?job_id=${jobId}` : ""}`);
}
