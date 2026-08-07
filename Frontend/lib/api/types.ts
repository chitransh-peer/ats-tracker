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

export interface JobBusinessInfo {
  title: string;
  department: string | null;
  client_id: string | null;
  hiring_manager_id: string | null;
  recruiter_id: string | null;
  location: string | null;
  workplace: string;
  employment_type: string;
  openings: number;
  pay_min: number | null;
  pay_max: number | null;
  priority: string;
  summary: string | null;
  description: string | null;
  responsibilities: string[];
  required_skills: string[];
  nice_to_have: string[];
  screening_questions: string[];
  experience: string | null;
  education: string | null;

  business_unit: string | null;
  facility: string | null;
  end_client: string | null;
  job_status_detail: string | null;
  duration: string | null;
  required_hours_per_week: number | null;
  interview_mode: string | null;
  clearance_required: boolean;
  additional_details: string | null;
  employment_test_template: string | null;
  employment_level: string | null;
  required_documents: string[];
  work_authorizations: string[];

  respond_by: string | null;
  respond_by_date: string | null;
  turnaround_time_value: number | null;
  turnaround_time_unit: string | null;

  pay_rate_currency: string;
  pay_rate_unit: string;
  pay_rate_type: string | null;
  client_bill_rate_min: string | null;
  client_bill_rate_max: string | null;
  client_bill_rate_currency: string;
  client_bill_rate_unit: string;
  client_bill_rate_type: string | null;

  address: string | null;
  city: string | null;
  states: string[];
  country: string | null;
  postal_code: string | null;

  experience_min_years: number | null;
  experience_max_years: number | null;

  max_allowed_submissions: number | null;
  tax_terms: string[];
  sales_manager_id: string | null;
  recruitment_manager_id: string | null;
  account_manager_id: string | null;
  primary_recruiter_id: string | null;
  assigned_to_ids: string[];
  comments: string | null;
}

export interface JobCustomField {
  id: string;
  field_name: string;
  field_value: string | null;
}

export interface JobSearchCriteria {
  id: string;
  job_id: string;
  boolean_string: string | null;
  job_title: string | null;
  recent_job_title_only: boolean;
  search_mode: string;
  country: string | null;
  state: string | null;
  city: string | null;
  postal_code: string | null;
  radius_miles: number | null;
  search_radius_within_state: boolean;
  include_applicants_without_country: boolean;
  experience_min_years: number | null;
  experience_max_years: number | null;
  education: string[];
  work_authorizations: string[];
  employer: string | null;
  most_recent_employer_only: boolean;
  willing_to_relocate: boolean | null;
  clearance: boolean | null;
}

export type JobSearchCriteriaInput = Omit<JobSearchCriteria, "id" | "job_id">;

export interface JobNote {
  id: string;
  body: string;
  note_type: string;
  action: string | null;
  author_id: string | null;
  author_name: string | null;
  created_at: string;
}

export interface JobDocument {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: string | null;
  created_at: string;
}

export interface JobSubmission {
  application_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string | null;
  candidate_phone: string | null;
  candidate_location: string | null;
  work_auth: string | null;
  pay_expectation: number | null;
  source: string | null;
  status: string;
  current_stage_id: string | null;
  current_stage_name: string | null;
  stage_index: number;
  applied_at: string;
  submitted_by: string | null;
  submitted_by_name: string | null;
  submitted_at: string | null;
}

export interface JobSubmissionsSummary {
  stages: string[];
  submissions: JobSubmission[];
  counts: Record<string, number>;
}

export interface Job extends JobBusinessInfo {
  id: string;
  organization_id: string;
  req_id: string;
  slug: string;
  stage_template_id: string | null;
  status: string;
  posted_at: string | null;
  created_at: string;
  updated_at: string;

  client_name: string | null;
  sales_manager_name: string | null;
  recruitment_manager_name: string | null;
  account_manager_name: string | null;
  primary_recruiter_name: string | null;
  assigned_to_names: string[];

  created_by: string | null;
  created_by_name: string | null;
  updated_by: string | null;
  updated_by_name: string | null;

  job_age_days: number;
  custom_fields: JobCustomField[];
  search_criteria: JobSearchCriteria | null;

  applications_count: number;
  shortlisted_count: number;
  interviews_count: number;
  offers_count: number;
  hires_count: number;
}

export interface JobNoteInput {
  body: string;
  note_type?: string;
  action?: string | null;
}

export interface JobCustomFieldInput {
  field_name: string;
  field_value?: string | null;
}

export type JobCreateInput = Partial<JobBusinessInfo> & {
  title: string;
  notes?: JobNoteInput[];
  custom_fields?: JobCustomFieldInput[];
  search_criteria?: JobSearchCriteriaInput | null;
};

export type JobUpdateInput = Partial<JobBusinessInfo>;

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
  ai_score?: number | null;
  ai_recommendation?: string | null;
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

export interface OnboardingTask {
  id: string;
  case_id: string;
  title: string;
  category: string;
  status: string;
  assignee_id: string | null;
  due_date: string | null;
  order_index: number;
  completed_at: string | null;
  created_at: string;
}

export interface OnboardingCase {
  id: string;
  organization_id: string;
  application_id: string;
  status: string;
  start_date: string | null;
  coordinator_id: string | null;
  notes: string | null;
  completed_at: string | null;
  tasks: OnboardingTask[];
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

export interface AIEvaluation {
  id: string;
  application_id: string;
  version: number;
  status: string;
  rule_score: number | null;
  semantic_score: number | null;
  overall_score: number | null;
  recommendation_label: string | null;
  strengths: string[];
  gaps: string[];
  risk_flags: string[];
  matched_skills: string[];
  missing_skills: string[];
  criteria: JDCriterion[];
  suggested_interview_questions: string[];
  confidence: number | null;
  explanation_text: string | null;
  model_name: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface JDCriterion {
  type: string;
  requirement: string;
  weight: number;
  candidate_value: string;
  status: string;
  score: number;
}

export interface JDResumeComparison {
  job_requirements: {
    title: string;
    required_skills: string[];
    nice_to_have: string[];
    experience: string | null;
    education: string | null;
    location: string | null;
  };
  candidate_profile: {
    full_name: string;
    skills: string[];
    total_experience_years: number | null;
    location: string | null;
  };
  criteria: JDCriterion[];
  total_score: number;
}

export interface OrganizationSettings {
  default_locale: string;
  careers_page_enabled: boolean;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  settings: OrganizationSettings;
}

export interface Permission {
  resource: string;
  action: string;
}

export interface Role {
  id: string;
  name: string;
  display_name: string;
  is_system_role: boolean;
  permissions: Permission[];
}

export interface User {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: string[];
  created_at: string;
  updated_at: string;
}

export interface Template {
  id: string;
  organization_id: string;
  name: string;
  type: string;
  subject: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface AuditUserSummary {
  actor_user_id: string | null;
  full_name: string | null;
  email: string | null;
  event_count: number;
  last_activity: string | null;
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

export interface ClientContact {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  title: string | null;
  status: string;
}

export interface ClientAccount {
  id: string;
  contact_person: string;
  email_id: string | null;
  designation: string | null;
  office_number: string | null;
  mobile_number: string | null;
}

export interface ClientAssignment {
  id: string;
  user_id: string;
  assignment_role: string | null;
  user_name: string | null;
}

export interface ClientNote {
  id: string;
  body: string;
  note_type: string;
  priority: string;
  author_id: string | null;
  author_name: string | null;
  created_at: string;
}

export interface ClientDocument {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: string | null;
  created_at: string;
}

/** Every writable business-information field on a client. */
export interface ClientBusinessInfo {
  name: string;
  short_name: string | null;
  vms_client_name: string | null;
  federal_id: string | null;
  contact_number: string | null;
  email_id: string | null;
  fax: string | null;
  website: string | null;
  industry: string | null;
  status: string;
  category: string | null;
  practice: string | null;
  payment_terms: string | null;
  about_company: string | null;

  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;

  primary_business_unit: string | null;
  business_unit: string | null;
  client_visibility: string;
  primary_owner_id: string | null;
  ownership_id: string | null;
  client_lead_id: string | null;
  parent_client_id: string | null;

  display_on_job_posting: boolean;
  send_requirement: boolean;
  send_hotlist: boolean;
  allow_access_to_all_users: boolean;
  notify_near_client_location: boolean;
  stop_contact_email_on_submit: boolean;
  default_address_for_jobs: boolean;

  client_facilities: string[];
  required_documents: string[];
  submission_format_fields: string[];

  guidelines: string | null;
  markup_percentage: string | null;
  overtime_markup_percentage: string | null;
  standard_working_hours: number | null;
  submission_instructions: string | null;
}

export interface Client extends ClientBusinessInfo {
  id: string;
  organization_id: string;
  client_code: string;

  primary_owner_name: string | null;
  ownership_name: string | null;
  client_lead_name: string | null;
  parent_client_name: string | null;

  created_by: string | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
  updated_by: string | null;
  updated_by_name: string | null;

  contacts: ClientContact[];
  accounts: ClientAccount[];
  assignments: ClientAssignment[];
  active_jobs: number;
}

export interface ClientAccountInput {
  contact_person: string;
  email_id?: string | null;
  designation?: string | null;
  office_number?: string | null;
  mobile_number?: string | null;
}

export interface ClientContactInput {
  name: string;
  email?: string | null;
  phone?: string | null;
  title?: string | null;
  status?: string;
}

export interface ClientNoteInput {
  body: string;
  note_type?: string;
  priority?: string;
}

export interface ClientAssignmentInput {
  user_id: string;
  assignment_role?: string | null;
}

export type ClientCreateInput = Partial<ClientBusinessInfo> & {
  name: string;
  accounts?: ClientAccountInput[];
  contacts?: ClientContactInput[];
  notes?: ClientNoteInput[];
  assignments?: ClientAssignmentInput[];
};

export type ClientUpdateInput = Partial<ClientBusinessInfo>;

export interface VendorContact {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  work_phone: string | null;
  designation: string | null;
  status: string;
  vms_status: string;
  owner_id: string | null;
  owner_name: string | null;
}

export interface VendorAccount {
  id: string;
  contact_person: string;
  email_id: string | null;
  designation: string | null;
  office_number: string | null;
  mobile_number: string | null;
}

export interface VendorNote {
  id: string;
  body: string;
  action: string | null;
  author_id: string | null;
  author_name: string | null;
  notified_user_ids: string[];
  notified_people: string[];
  created_at: string;
}

export interface VendorDocument {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: string | null;
  created_at: string;
}

export interface VendorMeeting {
  id: string;
  meeting_for: string;
  description: string | null;
  contact_id: string | null;
  contact_name: string | null;
  attendee_ids: string[];
  attendee_names: string[];
  guest_attendees: string[];
  start_time: string | null;
  duration_minutes: number | null;
  created_by_id: string | null;
  created_by_name: string | null;
}

export interface VendorBankAccount {
  id: string;
  account_holder_name: string;
  bank_name: string;
  account_number: string;
  account_type: string | null;
  routing_number: string | null;
  swift_code: string | null;
  branch_address: string | null;
  effective_from: string | null;
  is_primary: boolean;
}

/** Every writable business-information field on a vendor. */
export interface VendorBusinessInfo {
  name: string;
  specialization: string | null;
  status: string;
  federal_id: string | null;
  website: string | null;
  contact_number: string | null;
  email_id: string | null;
  fax: string | null;
  vendor_type: string | null;
  vendor_classification: string | null;
  payment_terms: string | null;
  about_vendor: string | null;

  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  zip_code: string | null;

  primary_business_unit: string | null;
  business_units: string[];
  vendor_visibility: string;
  primary_owner_id: string | null;
  ownership_id: string | null;
  vendor_lead_id: string | null;

  send_requirement: boolean;
  send_hotlist: boolean;
  primary_vendor: boolean;
  allow_access_to_all_users: boolean;

  technologies: string[];
  submission_format_fields: string[];
  submission_instructions: string | null;
}

export interface Vendor extends VendorBusinessInfo {
  id: string;
  organization_id: string;

  primary_owner_name: string | null;
  ownership_name: string | null;
  vendor_lead_name: string | null;

  created_by: string | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
  updated_by: string | null;
  updated_by_name: string | null;

  contacts: VendorContact[];
  accounts: VendorAccount[];
  bank_accounts: VendorBankAccount[];
  active_submissions: number;
}

export interface VendorAccountInput {
  contact_person: string;
  email_id?: string | null;
  designation?: string | null;
  office_number?: string | null;
  mobile_number?: string | null;
}

export interface VendorContactInput {
  name: string;
  email?: string | null;
  phone?: string | null;
  work_phone?: string | null;
  designation?: string | null;
  status?: string;
  vms_status?: string;
  owner_id?: string | null;
}

export interface VendorNoteInput {
  body: string;
  action?: string | null;
  notified_user_ids?: string[];
}

export interface VendorMeetingInput {
  meeting_for: string;
  description?: string | null;
  contact_id?: string | null;
  attendee_ids?: string[];
  guest_attendees?: string[];
  start_time?: string | null;
  duration_minutes?: number | null;
}

export interface VendorBankAccountInput {
  account_holder_name: string;
  bank_name: string;
  account_number: string;
  account_type?: string | null;
  routing_number?: string | null;
  swift_code?: string | null;
  branch_address?: string | null;
  effective_from?: string | null;
  is_primary?: boolean;
}

export type VendorCreateInput = Partial<VendorBusinessInfo> & {
  name: string;
  accounts?: VendorAccountInput[];
  contacts?: VendorContactInput[];
  notes?: VendorNoteInput[];
  bank_accounts?: VendorBankAccountInput[];
};

export type VendorUpdateInput = Partial<VendorBusinessInfo>;
