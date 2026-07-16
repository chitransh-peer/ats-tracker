export interface CurrentUserProfile {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: string[];
  created_at: string;
  updated_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Job {
  id: string;
  organization_id: string;
  req_id: string;
  slug: string;
  title: string;
  department: string | null;
  client_id: string | null;
  hiring_manager_id: string | null;
  recruiter_id: string | null;
  stage_template_id: string | null;
  location: string | null;
  workplace: string;
  employment_type: string;
  openings: number;
  pay_min: number | null;
  pay_max: number | null;
  priority: string;
  status: string;
  summary: string | null;
  description: string | null;
  responsibilities: string[];
  required_skills: string[];
  nice_to_have: string[];
  screening_questions: string[];
  experience: string | null;
  education: string | null;
  posted_at: string | null;
  created_at: string;
  updated_at: string;
  applications_count: number;
  shortlisted_count: number;
  interviews_count: number;
  offers_count: number;
  hires_count: number;
}

export interface JobCreateInput {
  title: string;
  department?: string | null;
  client_id?: string | null;
  hiring_manager_id?: string | null;
  recruiter_id?: string | null;
  location?: string | null;
  workplace: string;
  employment_type: string;
  openings?: number;
  pay_min?: number | null;
  pay_max?: number | null;
  priority?: string;
  summary?: string | null;
  description?: string | null;
  responsibilities?: string[];
  required_skills?: string[];
  nice_to_have?: string[];
  screening_questions?: string[];
  experience?: string | null;
  education?: string | null;
}

export interface EducationItem {
  degree: string;
  school: string;
  year: string | null;
}

export interface DuplicateWarning {
  candidate_id: string;
  full_name: string;
  email: string;
  match_reason: string;
}

export interface Candidate {
  id: string;
  organization_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  location: string | null;
  current_company: string | null;
  current_title: string | null;
  total_experience_years: number | null;
  relevant_experience_years: number | null;
  notice_period: string | null;
  current_ctc: number | null;
  expected_ctc: number | null;
  skills: string[];
  source: string | null;
  rating: number | null;
  linkedin_url: string | null;
  work_auth: string | null;
  relocation_ok: boolean;
  status: string;
  education: EducationItem[];
  tags: string[];
  created_at: string;
  updated_at: string;
  duplicate_warnings: DuplicateWarning[];
}

export interface CandidateCreateInput {
  full_name: string;
  email: string;
  phone?: string | null;
  location?: string | null;
  current_company?: string | null;
  current_title?: string | null;
  total_experience_years?: number | null;
  relevant_experience_years?: number | null;
  notice_period?: string | null;
  current_ctc?: number | null;
  expected_ctc?: number | null;
  skills?: string[];
  source?: string | null;
  linkedin_url?: string | null;
  work_auth?: string | null;
  relocation_ok?: boolean;
  education?: EducationItem[];
  tags?: string[];
}

export interface CandidateNote {
  id: string;
  author_id: string | null;
  body: string;
  created_at: string;
}

export interface Application {
  id: string;
  organization_id: string;
  candidate_id: string;
  job_id: string;
  current_stage_id: string | null;
  source: string | null;
  status: string;
  applied_at: string;
}

export interface ApplicationStageHistoryEntry {
  id: string;
  from_stage_id: string | null;
  to_stage_id: string | null;
  changed_by: string | null;
  note: string | null;
  created_at: string;
}

export interface Stage {
  id: string;
  name: string;
  sort_order: number;
  terminal_outcome: string;
}

export interface StageTemplate {
  id: string;
  name: string;
  is_default: boolean;
  stages: Stage[];
}

export interface InterviewFeedbackEntry {
  id: string;
  submitted_by: string | null;
  rating: number;
  recommendation: string;
  notes: string | null;
  created_at: string;
}

export interface InterviewPanelMember {
  user_id: string;
  is_primary: boolean;
}

export interface Interview {
  id: string;
  organization_id: string;
  application_id: string;
  round_name: string;
  mode: string;
  scheduled_at: string;
  status: string;
  panel_members: InterviewPanelMember[];
  feedback_entries: InterviewFeedbackEntry[];
  created_at: string;
  updated_at: string;
}

export interface OfferVersion {
  id: string;
  version_number: number;
  base_salary: number;
  bonus: number | null;
  equity: string | null;
  joining_date: string | null;
  created_at: string;
}

export interface OfferApproval {
  id: string;
  requested_by: string | null;
  approver_id: string | null;
  status: string;
  note: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface Offer {
  id: string;
  organization_id: string;
  application_id: string;
  status: string;
  base_salary: number;
  bonus: number | null;
  equity: string | null;
  joining_date: string | null;
  versions: OfferVersion[];
  approvals: OfferApproval[];
  created_at: string;
  updated_at: string;
}

export interface FunnelStage {
  stage: string;
  value: number;
}

export interface SourceEffectivenessRow {
  source: string;
  value: number;
}

export interface AgingJobRow {
  job_id: string;
  title: string;
  status: string;
  posted_at: string | null;
  age_days: number | null;
}

export interface AuditLogEntry {
  id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  metadata_json: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}
