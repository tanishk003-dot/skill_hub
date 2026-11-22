# L&K Skill Hub — Production Operations Runbook

This operational runbook provides sysadmins, DevOps, and SRE teams with standard operating procedures (SOPs) for running, securing, backing up, and troubleshooting the L&K Skill Hub enterprise platform.

---

## 1. Production Startup Checklist

Before deploying or starting the backend in `APP_ENV=production`:

1. **Database Backend**:
   - Ensure `DATABASE_URL` points to a live MySQL 8.0+ instance (e.g. `mysql+pymysql://user:pass@host:3306/skillhub_db?charset=utf8mb4`).
   - In production, **SQLite is strictly prohibited**. If `DATABASE_URL` starts with `sqlite` or if MySQL is unreachable, the backend will refuse to start with a fatal error.
2. **Secrets & Cryptographic Keys**:
   - `SECRET_KEY`: Must be at least 32 characters long. The backend will refuse to start if set to the default placeholder (`skillhub-super-secret-jwt-key-replace-in-production`).
   - `TOKEN_ENCRYPTION_KEY`: A Fernet encryption key used to encrypt Microsoft SSO refresh tokens at rest.
     > [!CAUTION]
     > **CRITICAL KEY RETENTION WARNING**:
     > Losing `TOKEN_ENCRYPTION_KEY` renders all stored SSO refresh tokens permanently unreadable. Any user whose token cannot be decrypted will be immediately de-authenticated and forced to complete interactive login again. Store this key securely in a secret vault (AWS Secrets Manager, Azure Key Vault, or HashiCorp Vault). Never commit it to git or lose it during key rotation.
3. **Session Expiration**:
   - `ACCESS_TOKEN_EXPIRE_MINUTES`: Enforced to $\le 60$ minutes in production. The backend refuses to start if higher.
4. **CORS Restrictions**:
   - `CORS_ORIGINS`: Wildcard `*` is strictly forbidden in production. Must list exact corporate domain origins.
5. **Provider Safety**:
   - `MockSSOProvider`, `MockAttendanceProvider`, and `MockTeamsBotProvider` are strictly banned in production.
6. **Security Headers**:
   - All responses include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security` (on HTTPS), and strict `Content-Security-Policy`.

---

## 2. Database Backup and Restoration SOP

### 2.1 Online Production Backup (`mysqldump`)

Perform online backups using `--single-transaction` to ensure transactional consistency without locking tables.

```bash
# Set UTC timestamp for the backup filename
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")

# Execute consistent online dump
mysqldump -h 127.0.0.1 -P 3306 -u root -p \
  --single-transaction \
  --quick \
  --routines \
  --triggers \
  --default-character-set=utf8mb4 \
  --databases skillhub_db > "/var/backups/skillhub/backup_skillhub_${TIMESTAMP}.sql"
```

Verify that the backup file is non-empty and contains valid SQL definitions.

### 2.2 Point-in-Time Restore SOP

To restore a backup into a target database:

```bash
# 1. Create target database if it does not exist
mysql -h 127.0.0.1 -P 3306 -u root -p -e "CREATE DATABASE IF NOT EXISTS skillhub_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. Restore schema and data
mysql -h 127.0.0.1 -P 3306 -u root -p skillhub_db < "/var/backups/skillhub/backup_skillhub_20261120_120000Z.sql"

# 3. Verify table counts and integrity
mysql -h 127.0.0.1 -P 3306 -u root -p -e "SELECT count(*) FROM information_schema.tables WHERE table_schema='skillhub_db';"
```

---

## 3. Data Retention Policy & Automated Cleanup

The automated retention service (`app/services/retention_service.py`) purges stale operational data to prevent unbounded storage growth and comply with privacy standards.

> [!IMPORTANT]
> **LEGAL NOTICE**:
> The retention periods documented below are engineering defaults. **These periods must be formally confirmed with HR and corporate legal counsel** prior to production enforcement to ensure compliance with local labor and data protection laws.

| Data Category | Target Table | Default Retention Period | Policy Rationale |
| :--- | :--- | :--- | :--- |
| **Webcam Proctoring Snapshots** | `webcam_proctoring_snapshots` | 90 days | Discarded after assessment review window closes |
| **Raw Meeting Transcripts** | `class_transcripts` | 180 days | Raw speech audio/text purged; AI summaries retained |
| **Attendance Raw Imports** | `class_attendance_imports` | 180 days | Staging records removed once synced with student attendance |
| **Expired OAuth State Tokens** | `sso_oauth_states` | 1 day (or on expiry) | PKCE and nonce state parameters have a 10-minute TTL |
| **Login Attempt Records** | `login_attempts` | 90 days | Forensic security logs kept for 90 days |
| **Admin Audit Trail** | `admin_audit_logs` | Indefinite (Append-only) | Immutable audit log for security compliance |

### Manual Retention Execution
To run retention cleanup on demand:
```bash
python -m app.services.retention_service
```

---

## 4. Break-Glass Emergency Procedures

### 4.1 Break-Glass Admin Local Login
If corporate SSO (Microsoft Entra ID / Azure AD) is experiencing an outage or misconfiguration, administrators can use the dedicated Break-Glass endpoint:
- **Endpoint**: `POST /api/v1/auth/break-glass`
- **Request**:
  ```json
  {
    "email": "breakglass.admin@csmtech.com",
    "password": "EmergencyStrongPassword123!"
  }
  ```
- **Guards**:
  - Only accounts with role `ADMIN` can authenticate via this endpoint.
  - Generates an immutable `ADMIN_BREAK_GLASS_LOGIN` audit event.
  - Rate limited to prevent brute-force attacks.

### 4.2 Account Lockout Unlock
If an admin or user is locked out due to repeated failed login attempts (exponential backoff locks accounts after 5 consecutive failures):
```bash
# View locked accounts via CLI
python -m app.cli.admin_manage --list-locked

# Unlock a specific user account
python -m app.cli.admin_manage --unlock user@csmtech.com
```
Alternatively, another admin can unlock the account via `POST /api/v1/auth/unlock-account` with `{ "email": "user@csmtech.com" }`.

### 4.3 Emergency Admin Creation
If all admin accounts are inaccessible:
```bash
python -m app.cli.create_admin --email emergency.admin@csmtech.com --name "Emergency Admin" --password "EmergencyPassword123!"
```

### 4.4 Demo Data Purging
Before putting a seeded environment into production:
```bash
python -m app.cli.purge_demo_data --confirm
```
This safely removes all records with `is_demo = TRUE` and demo seeded accounts without breaking foreign key cascades.

---

## 5. Health Checks & Monitoring

### 5.1 Service Health Endpoint
- **URL**: `GET /api/v1/health`
- **Response Format**:
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-11-20T11:27:00Z",
    "version": "1.0.0",
    "environment": "production",
    "services": {
      "database": {
        "status": "connected",
        "engine": "mysql",
        "latency_ms": 1.45
      },
      "judge0": {
        "status": "connected",
        "latency_ms": 12.3
      }
    }
  }
  ```
- **Alert Conditions**:
  - HTTP status $\ne 200 \implies$ Critical Alert (PagerDuty / Slack).
  - `database.status != "connected"` $\implies$ Service Unavailable (Backend cannot process requests).
  - `judge0.status != "connected"` $\implies$ Advisory Alert (Coding assessments temporarily degraded).

---

## 6. Log Rotation & Monitoring Best Practices

1. **Application Logs**:
   - Configure Docker log driver with `max-size: "50m"` and `max-file: "10"`:
     ```yaml
     logging:
       driver: "json-file"
       options:
         max-size: "50m"
         max-file: "10"
     ```
2. **Reverse Proxy Logs (Nginx)**:
   - Configure `/etc/logrotate.d/nginx` with daily rotation and 14-day retention.
   - Mask sensitive query strings (e.g., `code`, `state`) from access logs.
3. **Database Audit Logs**:
   - Enable MySQL general log only during debugging sessions.
   - Enable slow query log (`long_query_time = 2`).
