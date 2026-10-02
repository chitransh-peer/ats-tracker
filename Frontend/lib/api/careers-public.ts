import { apiClient } from "./client";

/** Slug of the organization whose careers page is public-facing. */
export const CAREERS_ORG_SLUG = process.env.NEXT_PUBLIC_CAREERS_ORG_SLUG ?? "peer-consulting";

export interface ApplicationQuestion {
  key: string;
  label: string;
  type: "text" | "textarea" | "number" | "yesno";
  required: boolean;
  placeholder: string | null;
}

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
  /** The JD-dependent section of the application form. */
  role_questions: ApplicationQuestion[];
  ask_portfolio_links: boolean;
  ask_sponsorship: boolean;
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

/** Every field on the careers-page form; optional ones may be left blank. */
export interface ApplyInput {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  current_title: string;
  current_company: string;
  total_experience_years: string;
  relevant_experience_years: string;
  linkedin_url: string;
  portfolio_url: string;
  github_url: string;
  highest_qualification: string;
  college: string;
  graduation_year: string;
  notice_period: string;
  earliest_joining_date: string;
  current_ctc: string;
  expected_ctc: string;
  work_arrangement_ok: string;
  heard_from: string;
  work_authorized: string;
  needs_sponsorship: string;
}

export function applyToJob(
  jobId: string,
  input: ApplyInput,
  roleAnswers: Record<string, string>,
  resume: File,
  slug: string = CAREERS_ORG_SLUG,
) {
  const form = new FormData();
  for (const [key, value] of Object.entries(input)) {
    if (value.trim()) form.set(key, value.trim());
  }
  form.set("role_answers", JSON.stringify(roleAnswers));
  form.set("resume", resume);
  return apiClient.postForm<PublicApplyResponse>(`/careers/${slug}/jobs/${jobId}/apply`, form);
}
