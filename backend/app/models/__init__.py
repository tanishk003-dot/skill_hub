from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt, AssessmentResponse, AttemptStatus, ExamViolation

from app.models.cohort import Cohort, CohortMember
from app.models.training import Training, TrainingAssignment
from app.models.live_class import LiveClass, LiveClassAttendee
from app.models.notification import Notification, ReminderSent
from app.models.chat import ChatSession, ChatMessage, LLMUsageLog, AIInsightsCache
from app.models.quote import MotivationalQuote
from app.models.coding import CodingSubmission, CodingRunLog, CodingPlagiarismFlag
from app.models.ai_class_summary import (
    ClassTranscript, ClassSummary, AIGeneratedAssessment,
    AIGeneratedQuestion, ClassEffectivenessReport, AIGenerateRateLog
)
from app.models.phase9_models import (
    ReadinessConfig, ReadinessAuditLog, AseReadinessHistory,
    AseGamification, OnboardingMilestone, AILearningRoadmap,
    AseRiskSignal, MentorNudgeLog, ReassessmentSchedule,
    IssuedCertificate, MockInterviewSession, MockInterviewRateLog,
    PublicVerifyRateLog
)
from app.models.phase10_models import (
    WebcamConsent, CameraHandshake, CameraHeartbeat, CameraOverrideLog,
    WebcamProctoringSnapshot, WebcamAuditLog, AccommodationRequest, AccommodationAuditLog
)
from app.models.phase11_models import (
    QuestionItemAnalytics, OneOnOneMeeting, OneOnOneGoal,
    OneOnOneActionItem, OneOnOneComment, ReportingApiToken,
    ReportingTokenAuditLog, StaffingProject, StaffingProjectSkill,
    MeetingStatus, GoalStatus
)
from app.models.phase12_models import (
    BuddyPairing, BuddyPairingStatus, BuddyMilestone, BuddyMilestoneStatus, BuddyRating,
    ForumPost, ForumPostStatus, ForumAnswer, ForumVote, ForumReport,
    ForumReportReason, ForumReportStatus, ForumIdentityAuditLog,
    ForumFilterAuditLog, ForumRateLimit
)
from app.models.phase13_models import (
    UserSSOAccount, SSOAuditLog, SSOConfiguration, SSOOAuthState,
    UserNotificationPreference, ClassAttendanceImport
)
from app.models.admin_audit_log import AdminAuditLog
from app.models.login_lockout import LoginAttempt

__all__ = [
    "User", "UserRole", "MentorAseAssignment",
    "QuestionBank", "AssessmentType", "QuestionDifficulty", "QuestionType",
    "Assessment", "AssessmentSection", "AssessmentSectionQuestion",
    "AssessmentAssignment",
    "AssessmentAttempt", "AssessmentResponse", "AttemptStatus", "ExamViolation",
    "Cohort", "CohortMember",
    "Training", "TrainingAssignment",
    "LiveClass", "LiveClassAttendee",
    "Notification", "ReminderSent",
    "ChatSession", "ChatMessage", "LLMUsageLog", "AIInsightsCache",
    "MotivationalQuote", "CodingSubmission", "CodingRunLog", "CodingPlagiarismFlag",
    "ClassTranscript", "ClassSummary", "AIGeneratedAssessment",
    "AIGeneratedQuestion", "ClassEffectivenessReport", "AIGenerateRateLog",
    "ReadinessConfig", "ReadinessAuditLog", "AseReadinessHistory",
    "AseGamification", "OnboardingMilestone", "AILearningRoadmap",
    "AseRiskSignal", "MentorNudgeLog", "ReassessmentSchedule",
    "IssuedCertificate", "MockInterviewSession", "MockInterviewRateLog",
    "PublicVerifyRateLog",
    "WebcamConsent", "CameraHandshake", "CameraHeartbeat", "CameraOverrideLog",
    "WebcamProctoringSnapshot", "WebcamAuditLog", "AccommodationRequest", "AccommodationAuditLog",
    "QuestionItemAnalytics", "OneOnOneMeeting", "OneOnOneGoal",
    "OneOnOneActionItem", "OneOnOneComment", "ReportingApiToken",
    "ReportingTokenAuditLog", "StaffingProject", "StaffingProjectSkill",
    "MeetingStatus", "GoalStatus",
    "BuddyPairing", "BuddyPairingStatus", "BuddyMilestone", "BuddyMilestoneStatus", "BuddyRating",
    "ForumPost", "ForumPostStatus", "ForumAnswer", "ForumVote", "ForumReport",
    "ForumReportReason", "ForumReportStatus", "ForumIdentityAuditLog",
    "ForumFilterAuditLog", "ForumRateLimit",
    "UserSSOAccount", "SSOAuditLog", "SSOConfiguration", "SSOOAuthState",
    "UserNotificationPreference", "ClassAttendanceImport"
]
