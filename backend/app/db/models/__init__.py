from app.db.base import Base
from app.db.models.ai import AIEvaluation, AIEvaluationOverride, ParsedResume, ResumeParseRun
from app.db.models.application import Application, ApplicationStageHistory
from app.db.models.audit_log import AuditLog
from app.db.models.candidate import (
    Candidate,
    CandidateDocument,
    CandidateEducation,
    CandidateNote,
    CandidateTag,
    DuplicateCandidateLink,
)
from app.db.models.client import Client, ClientContact
from app.db.models.communication import CommunicationTemplate, OutboundMessage
from app.db.models.interview import Interview, InterviewFeedback, InterviewPanelMember
from app.db.models.invitation import Invitation
from app.db.models.job import Job
from app.db.models.offer import Offer, OfferApproval, OfferVersion
from app.db.models.onboarding import OnboardingCase, OnboardingTask
from app.db.models.organization import Organization, OrganizationSettings
from app.db.models.password_reset_token import PasswordResetToken
from app.db.models.pipeline_stage import StageTemplate, StageTemplateStage
from app.db.models.refresh_token import RefreshToken
from app.db.models.role import Permission, Role, RolePermission, UserRole
from app.db.models.user import User
from app.db.models.vendor import Vendor, VendorContact

__all__ = [
    "Base",
    "Organization",
    "OrganizationSettings",
    "User",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "Invitation",
    "AuditLog",
    "RefreshToken",
    "PasswordResetToken",
    "StageTemplate",
    "StageTemplateStage",
    "Client",
    "ClientContact",
    "Vendor",
    "VendorContact",
    "Job",
    "Candidate",
    "CandidateEducation",
    "CandidateTag",
    "CandidateNote",
    "CandidateDocument",
    "DuplicateCandidateLink",
    "Application",
    "ApplicationStageHistory",
    "Interview",
    "InterviewPanelMember",
    "InterviewFeedback",
    "Offer",
    "OfferVersion",
    "OfferApproval",
    "OnboardingCase",
    "OnboardingTask",
    "CommunicationTemplate",
    "OutboundMessage",
    "ResumeParseRun",
    "ParsedResume",
    "AIEvaluation",
    "AIEvaluationOverride",
]
