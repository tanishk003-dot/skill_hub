import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "L&K Skill Hub API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "skillhub-super-secret-jwt-key-replace-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DATABASE_URL: str = "sqlite:///./skillhub.db"
    CORS_ORIGINS: str = "http://localhost:4200,http://127.0.0.1:4200"
    PROCTORING_DEBUG: bool = False
    ALLOWED_EMAIL_DOMAINS: str = "csm.tech"
    ALLOWED_MEETING_DOMAINS: str = "teams.microsoft.com,teams.live.com,zoom.us,meet.google.com"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@csm.tech"
    UPLOAD_DIR: str = "uploads/trainings"
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "mock-gpt-4"
    LLM_BASE_URL: str = ""
    ALLOW_MOCK_LLM: bool = True
    CHAT_RATE_LIMIT_PER_HOUR: int = 20
    CHAT_MAX_MESSAGE_CHARS: int = 1000
    LLM_MAX_TOKENS: int = 800
    LLM_TIMEOUT_SECONDS: int = 30
    APP_ENV: str = "development"
    JUDGE0_URL: str = "http://judge0-server:2358"
    JUDGE0_CPU_TIME_LIMIT: float = 2.0
    JUDGE0_WALL_TIME_LIMIT: float = 5.0
    JUDGE0_MEMORY_LIMIT: int = 256000
    JUDGE0_MAX_PROCESSES: int = 30
    JUDGE0_MAX_OUTPUT_SIZE: int = 100000
    JUDGE0_ENABLE_NETWORK: bool = False
    CODING_RUN_RATE_LIMIT_PER_ATTEMPT: int = 20
    TRANSCRIPT_RETENTION_DAYS: int = 30
    MAX_TRANSCRIPT_FILE_SIZE_MB: int = 5
    MAX_GENERATE_CALLS_PER_MENTOR_PER_DAY: int = 20
    MAX_QUESTIONS_PER_CALL: int = 50
    MAX_TRANSCRIPT_TOKENS: int = 4000

    # Phase 11 Settings
    NOTE_ENCRYPTION_KEY: str = ""
    REPORTING_TOKEN_DEFAULT_EXPIRY_DAYS: int = 90
    REPORTING_TOKEN_RATE_LIMIT_PER_MINUTE: int = 60
    DEFAULT_READY_NOW_THRESHOLD_PCT: float = 90.0
    ONE_ON_ONE_AI_RATE_LIMIT_PER_HOUR: int = 5

    # Phase 13 Microsoft Integration Settings
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_REDIRECT_URI: str = "http://localhost:4300/auth/sso/callback"
    AZURE_BOT_APP_ID: str = ""
    AZURE_BOT_APP_PASSWORD: str = ""
    AZURE_BOT_ENDPOINT: str = ""
    SSO_AUTO_PROVISION_ASE: bool = False
    ALLOW_LOCAL_LOGIN: bool = True
    TOKEN_ENCRYPTION_KEY: str = ""
    TOKEN_ROTATION_KEYS: str = ""
    SSO_PROVIDER_TYPE: str = "auto"
    ATTENDANCE_PROVIDER_TYPE: str = "auto"
    TEAMS_BOT_PROVIDER_TYPE: str = "auto"

    # Polish Phase: Retention Policies (configurable in days; must be confirmed by HR/Legal)
    CHAT_TRANSCRIPT_RETENTION_DAYS: int = 90
    PROCTORING_SNAPSHOT_RETENTION_DAYS: int = 30
    ATTENDANCE_STAGING_RETENTION_DAYS: int = 30
    ADMIN_AUDIT_LOG_RETENTION_DAYS: int = 365
    SSO_AUDIT_LOG_RETENTION_DAYS: int = 180
    FORUM_AUDIT_LOG_RETENTION_DAYS: int = 180
    MENTOR_NOTES_RETENTION_DAYS: int = 365

    # Polish Phase: Security Hardening & Lockout Policies
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_BASE_SECONDS: int = 60
    LOGIN_LOCKOUT_MAX_SECONDS: int = 1800
    BREAK_GLASS_RATE_LIMIT_PER_MINUTE: int = 3
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True

    @property
    def allowed_meeting_domains_list(self) -> List[str]:
        return [d.strip().lower() for d in self.ALLOWED_MEETING_DOMAINS.split(",") if d.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()
