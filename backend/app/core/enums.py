import enum


class RoleName(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    EXECUTIVE = "executive"
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"


class PermissionAction(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"


class PermissionResource(str, enum.Enum):
    ORGANIZATION = "organization"
    USER = "user"
    ROLE = "role"
    JOB = "job"
    CANDIDATE = "candidate"
    APPLICATION = "application"
    PIPELINE = "pipeline"
    AI_EVALUATION = "ai_evaluation"
    INTERVIEW = "interview"
    OFFER = "offer"
    ONBOARDING = "onboarding"
    REPORT = "report"
    TEMPLATE = "template"
    SETTINGS = "settings"
    AUDIT_LOG = "audit_log"
    CLIENT = "client"
    VENDOR = "vendor"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    USER_INVITED = "user_invited"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    PERMISSION_CHANGED = "permission_changed"
    SETTINGS_CHANGED = "settings_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    JOB_CREATED = "job_created"
    JOB_UPDATED = "job_updated"
    JOB_PUBLISHED = "job_published"
    JOB_UNPUBLISHED = "job_unpublished"
    JOB_CLOSED = "job_closed"
    JOB_HELD = "job_held"
    JOB_CANCELLED = "job_cancelled"
    CANDIDATE_CREATED = "candidate_created"
    CANDIDATE_UPDATED = "candidate_updated"
    APPLICATION_CREATED = "application_created"
    APPLICATION_STAGE_MOVED = "application_stage_moved"
    APPLICATION_REJECTED = "application_rejected"
    APPLICATION_HELD = "application_held"
    APPLICATION_RESTORED = "application_restored"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_UPDATED = "interview_updated"
    INTERVIEW_FEEDBACK_SUBMITTED = "interview_feedback_submitted"
    OFFER_CREATED = "offer_created"
    OFFER_UPDATED = "offer_updated"
    OFFER_SUBMITTED_FOR_APPROVAL = "offer_submitted_for_approval"
    OFFER_APPROVED = "offer_approved"
    OFFER_REJECTED = "offer_rejected"
    OFFER_SENT = "offer_sent"
    TEMPLATE_CREATED = "template_created"
    TEMPLATE_UPDATED = "template_updated"
    RESUME_PARSED = "resume_parsed"
    AI_EVALUATION_TRIGGERED = "ai_evaluation_triggered"
    AI_EVALUATION_OVERRIDDEN = "ai_evaluation_overridden"
    VIEW_AS_STARTED = "view_as_started"


class JobStatus(str, enum.Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    ON_HOLD = "On Hold"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


class JobWorkplace(str, enum.Enum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ONSITE = "Onsite"


class JobEmploymentType(str, enum.Enum):
    FULL_TIME = "Full-time"
    CONTRACT = "Contract"
    PART_TIME = "Part-time"
    INTERN = "Intern"


class JobPriority(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class CandidateStatus(str, enum.Enum):
    ACTIVE = "Active"
    PASSIVE = "Passive"
    SILVER_MEDALIST = "Silver Medalist"
    DO_NOT_CONTACT = "Do Not Contact"


class ApplicationStatus(str, enum.Enum):
    ACTIVE = "Active"
    ON_HOLD = "On Hold"
    REJECTED = "Rejected"
    HIRED = "Hired"
    WITHDRAWN = "Withdrawn"


class TerminalOutcome(str, enum.Enum):
    NONE = "none"
    HIRED = "hired"
    REJECTED = "rejected"


class ClientStatus(str, enum.Enum):
    ACTIVE = "Active"
    PROSPECT = "Prospect"
    PAUSED = "Paused"


class VendorStatus(str, enum.Enum):
    ACTIVE = "Active"
    ON_HOLD = "On Hold"


class CandidateDocumentType(str, enum.Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    OTHER = "other"


class DuplicateMatchReason(str, enum.Enum):
    EMAIL = "email"
    PHONE = "phone"


class ResumeParseStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AIEvaluationStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AIRecommendationLabel(str, enum.Enum):
    STRONG_FIT = "strong_fit"
    FIT = "fit"
    PARTIAL_FIT = "partial_fit"
    NOT_A_FIT = "not_a_fit"


class InterviewMode(str, enum.Enum):
    VIDEO = "Video"
    ONSITE = "Onsite"
    PHONE = "Phone"


class InterviewStatus(str, enum.Enum):
    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    RESCHEDULED = "Rescheduled"


class InterviewRecommendation(str, enum.Enum):
    STRONG_YES = "Strong Yes"
    YES = "Yes"
    NO = "No"
    STRONG_NO = "Strong No"


class OfferStatus(str, enum.Enum):
    DRAFT = "Draft"
    APPROVAL_PENDING = "Approval Pending"
    SENT = "Sent"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    EXPIRED = "Expired"


class OfferApprovalStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class CommunicationTemplateType(str, enum.Enum):
    INTERVIEW_INVITE = "Interview Invite"
    OFFER = "Offer"
    REJECTION = "Rejection"
    FOLLOW_UP = "Follow-up"
    ACKNOWLEDGMENT = "Acknowledgment"


class OutboundMessageStatus(str, enum.Enum):
    LOGGED = "logged"
    SENT = "sent"
    FAILED = "failed"
