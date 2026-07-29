import { apiClient } from "./client";

/** Slug of the organization whose careers page is public-facing. */
export const CAREERS_ORG_SLUG =
  process.env.NEXT_PUBLIC_CAREERS_ORG_SLUG ?? "peer-consulting";

export interface PublicJob {
  id: string;
  slug: string;
  title: string;
  department: string | null;
  location: string | null;
  workplace: string;
  employment_type: string;
  summary: string | null;
  description: string | null;
  responsibilities: string[];
  required_skills: string[];
  nice_to_have: string[];
  experience: string | null;
  education: string | null;
  screening_questions: string[];
  posted_at: string | null;
}

export interface PublicOrganization {
  name: string;
  slug: string;
}

export interface PublicApplyResponse {
  application_id: string;
  candidate_id: string;
  status: string;
}

export function getPublicOrganization(slug: string = CAREERS_ORG_SLUG) {
  return apiClient.get<PublicOrganization>(`/careers/${slug}`);
}

export function listPublicJobs(slug: string = CAREERS_ORG_SLUG) {
  return apiClient.get<PublicJob[]>(`/careers/${slug}/jobs`);
}

export function applyToJob(
  jobId: string,
  input: { full_name: string; email: string; phone?: string; resume?: File | null },
  slug: string = CAREERS_ORG_SLUG,
) {
  const form = new FormData();
  form.set("full_name", input.full_name);
  form.set("email", input.email);
  if (input.phone) form.set("phone", input.phone);
  if (input.resume) form.set("resume", input.resume);
  return apiClient.postForm<PublicApplyResponse>(`/careers/${slug}/jobs/${jobId}/apply`, form);
}
