import asyncio
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import get_db
from app.seed import init_db
from app.services.scheduler import start_scheduler_loop
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.assignments import router as assignments_router
from app.api.dashboard import router as dashboard_router
from app.api.questions import router as questions_router
from app.api.assessments import router as assessments_router
from app.api.assessment_assignments import router as assessment_assignments_router
from app.api.exam import router as exam_router
from app.api.cohorts import router as cohorts_router
from app.api.analytics import router as analytics_router
from app.api.reports import router as reports_router
from app.api.trainings import router as trainings_router
from app.api.live_classes import router as live_classes_router
from app.api.calendar import router as calendar_router
from app.api.notifications import router as notifications_router
from app.api.chat import router as chat_router
from app.api.llm_admin import router as llm_admin_router
from app.api.quotes import router as quotes_router
from app.api.coding import router as coding_router
from app.api.class_summary import router as class_summary_router
from app.api.phase9_router import router as phase9_router
from app.api.proctoring import router as proctoring_router
from app.api.one_on_one import router as one_on_one_router
from app.api.export import router as export_router
from app.api.reporting import router as reporting_router
from app.api.staffing import router as staffing_router
from app.api.buddy import router as buddy_router
from app.api.forum import router as forum_router
from app.api.sso import router as sso_router
from app.api.admin_audit import router as admin_audit_router

logger = logging.getLogger(__name__)

def validate_production_configuration():
    """
    Enforces security hardening rules in APP_ENV=production:
    - Default or weak secrets prohibited
    - Token encryption keys required
    - Short access-token expiration (<= 60 min)
    - Wildcard CORS prohibited
    - Mock SSO, Mock Attendance, Mock Teams Bot and Mock LLM prohibited
    """
    if settings.APP_ENV.lower() == "production":
        # 1. Default Secrets Checks
        if settings.SECRET_KEY == "skillhub-super-secret-jwt-key-replace-in-production" or len(settings.SECRET_KEY) < 32:
            raise RuntimeError(
                "FATAL SECURITY CONFIGURATION: In APP_ENV=production, default or weak SECRET_KEY is strictly prohibited. "
                "Configure a secure 32+ character SECRET_KEY."
            )
        if not settings.TOKEN_ENCRYPTION_KEY or len(settings.TOKEN_ENCRYPTION_KEY) < 32:
            raise RuntimeError(
                "FATAL SECURITY CONFIGURATION: In APP_ENV=production, TOKEN_ENCRYPTION_KEY must be set to a valid 32+ character Fernet key."
            )
        # 2. Access Token Expiry Bounds
        if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 60:
            raise RuntimeError(
                f"FATAL SECURITY CONFIGURATION: In APP_ENV=production, ACCESS_TOKEN_EXPIRE_MINUTES ({settings.ACCESS_TOKEN_EXPIRE_MINUTES}) "
                "must be <= 60 minutes for production session security."
            )
        # 3. CORS Origins Restrictions
        if "*" in settings.cors_origins_list:
            raise RuntimeError(
                "FATAL SECURITY CONFIGURATION: In APP_ENV=production, wildcard '*' in CORS_ORIGINS is strictly prohibited."
            )
        # 4. Mock Providers Prohibition (SSO, Attendance, Teams Bot must never be mocked in production)
        if settings.SSO_PROVIDER_TYPE.lower() == "mock":
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Mock SSO is strictly forbidden in production! "
                "Configure valid AZURE_* credentials or leave empty to disable SSO."
            )
        if settings.ATTENDANCE_PROVIDER_TYPE.lower() == "mock":
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Mock Attendance provider is strictly forbidden in production!"
            )
        if settings.TEAMS_BOT_PROVIDER_TYPE.lower() == "mock":
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Mock Teams Bot provider is strictly forbidden in production!"
            )

        # 5. LLM Configuration: Demo AI Mode vs Required Live Key
        api_key = (settings.LLM_API_KEY or "").strip()
        if not api_key or settings.LLM_PROVIDER.lower() == "mock":
            if not getattr(settings, "ALLOW_MOCK_LLM", True):
                raise RuntimeError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: LLM_API_KEY is empty in production and ALLOW_MOCK_LLM is false. "
                    "A valid LLM_API_KEY is required to start."
                )
            logger.warning(
                "\n====================================================================\n"
                "WARNING: LLM_API_KEY is empty in production. Starting in Demo AI mode (MockProvider).\n"
                "AI features will use mocked responses with a 'Demo AI' indicator. Set LLM_API_KEY to enable live AI.\n"
                "===================================================================="
            )

        # 6. Azure Integration Status
        if not (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID):
            logger.info(
                "Microsoft Azure integration (SSO, Teams meetings, attendance sync, Teams bot) is DISABLED. "
                "Local login is enabled and meeting links will use ManualLinkProvider."
            )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce production security constraints
    validate_production_configuration()
    # Initialize DB and seed default records
    init_db()
    # Start background reminder scheduler (polls every 60s, error-handled)
    scheduler_task = asyncio.create_task(start_scheduler_loop(interval_seconds=60))
    try:
        yield
    finally:
        scheduler_task.cancel()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'wasm-unsafe-eval'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob:",
        "connect-src 'self'",
        "worker-src 'self' blob:",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'"
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
    
    # Set HSTS ONLY when served over HTTPS
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
    return response

# Production Error Masking (No stack traces exposed to clients)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    logger.exception("Unhandled server exception [Error ID: %s]: %s", error_id, exc)
    if settings.APP_ENV.lower() == "production":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred. Please contact system support.",
                "error_id": error_id
            }
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc), "error_id": error_id}
    )

# CORS configuration
origins = settings.cors_origins_list
if "*" not in origins:
    origins.append("http://localhost:4200")
    origins.append("http://127.0.0.1:4200")
    origins.append("http://localhost:4300")
    origins.append("http://127.0.0.1:4300")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(assignments_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(questions_router, prefix=settings.API_V1_STR)
app.include_router(assessments_router, prefix=settings.API_V1_STR)
app.include_router(assessment_assignments_router, prefix=settings.API_V1_STR)
app.include_router(exam_router, prefix=settings.API_V1_STR)
app.include_router(cohorts_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(trainings_router, prefix=settings.API_V1_STR)
app.include_router(live_classes_router, prefix=settings.API_V1_STR)
app.include_router(calendar_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(llm_admin_router, prefix=settings.API_V1_STR)
app.include_router(quotes_router, prefix=settings.API_V1_STR)
app.include_router(coding_router, prefix=settings.API_V1_STR)
app.include_router(class_summary_router, prefix=settings.API_V1_STR)
app.include_router(phase9_router, prefix=settings.API_V1_STR)
app.include_router(proctoring_router, prefix=settings.API_V1_STR)
app.include_router(one_on_one_router, prefix=settings.API_V1_STR)
app.include_router(export_router, prefix=settings.API_V1_STR)
app.include_router(reporting_router, prefix=settings.API_V1_STR)
app.include_router(staffing_router, prefix=settings.API_V1_STR)
app.include_router(buddy_router, prefix=settings.API_V1_STR)
app.include_router(forum_router, prefix=settings.API_V1_STR)
app.include_router(sso_router, prefix=settings.API_V1_STR)
app.include_router(admin_audit_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "message": "Welcome to L&K Skill Hub API",
        "docs": f"{settings.API_V1_STR}/docs"
    }

@app.get(f"{settings.API_V1_STR}/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "app_env": settings.APP_ENV
    }
