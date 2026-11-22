# L&K Skill Hub — Microsoft Integration & Azure IT Setup Guide

> **IMPORTANT NOTICE FOR IT ADMINISTRATORS**:
> The SSO, Teams meetings, attendance report import, and Teams notification bot integrations in L&K Skill Hub have been built and tested using high-fidelity cryptographic mock providers and test suites. **They have NOT yet been executed against a live corporate Microsoft Entra ID (Azure AD) tenant or live Microsoft Graph environment.**
>
> Please follow the setup steps below to provision and configure the necessary Azure resources and grant required permissions. Items requiring organization-specific policies or tenant verification are explicitly tagged with **`VERIFY WITH IT/MICROSOFT DOCS`**.

---

## 1. Information IT Must Provide

Before activating Microsoft integration in production, the IT team must supply the following parameters to populate the environment configuration (`.env`):

| Parameter | Description | Security Notes |
|:---|:---|:---|
| `AZURE_TENANT_ID` | Corporate Microsoft Entra ID Tenant ID (Directory ID) | Stored only in `.env`; validates all user JWT tokens |
| `AZURE_CLIENT_ID` | Application (Client) ID of the registered App | Exposed to browser during SSO initialization |
| `AZURE_CLIENT_SECRET` | Client Secret created under App Registrations | **CONFIDENTIAL**. Store only in `.env`, record expiry date |
| `AZURE_REDIRECT_URI` | Exact callback URL (e.g. `https://skillhub.yourcompany.com/auth/sso/callback`) | Must match Azure portal registration character-for-character |
| `AZURE_BOT_APP_ID` | Microsoft App ID for Azure Bot Service (for Teams notifications) | Required for Teams reminder delivery |
| `AZURE_BOT_APP_PASSWORD` | App secret for Azure Bot Service | **CONFIDENTIAL** |

---

## 2. Microsoft Entra ID (Azure AD) App Registration

### Step 2.1: Register the Application
1. Sign in to the [Microsoft Entra admin center](https://entra.microsoft.com/) as a **Global Administrator** or **Application Administrator**.
2. Navigate to **Identity** > **Applications** > **App registrations** > **New registration**.
3. **Name**: `LK-SkillHub-Enterprise`
4. **Supported account types**: Select **Accounts in this organizational directory only (Single tenant)**. Multi-tenant access is explicitly rejected by the L&K Skill Hub application.
5. **Redirect URI (Web)**:
   - Type: `Web`
   - Production URI: `https://skillhub.yourcompany.com/auth/sso/callback`
   - Staging/Local Testing URI: `http://localhost:4300/auth/sso/callback` *(VERIFY WITH IT/MICROSOFT DOCS: Do not keep localhost URIs in production apps)*
6. Click **Register**. Copy the **Application (client) ID** and **Directory (tenant) ID**.

### Step 2.2: Generate Client Secret
1. In the app registration, select **Certificates & secrets** > **Client secrets** > **New client secret**.
2. Description: `SkillHub Backend API Secret`
3. Expiration: Select 180 or 365 days according to corporate policy.
4. Click **Add** and immediately copy the secret **Value**. *(It will never be displayed again).*
5. Record the expiration date in your IT secret rotation calendar.

---

## 3. Microsoft Graph API Permissions & Endpoints

L&K Skill Hub adheres to the principle of least privilege. Permissions are split into **Delegated** (SSO sign-in on behalf of the user) and **Application** (daemon background tasks for meeting scheduling and attendance reports).

### Summary of Graph Permissions

| Scope / Permission Name | Type | Admin Consent | Microsoft Graph Endpoint Used | Purpose |
|:---|:---|:---|:---|:---|
| `User.Read` | Delegated | Not required | `/v1.0/me` | Read user profile during SSO login |
| `openid`, `profile`, `email`, `offline_access` | Delegated | Not required | OIDC authorize & token endpoints | OIDC identity token, email claim, refresh token |
| `OnlineMeetings.ReadWrite.All` | Application | **REQUIRED** | `POST /v1.0/users/{organizerUserId}/onlineMeetings` | Daemon creation of Teams meetings for classes |
| `OnlineMeetingAttendanceReport.Read.All` | Application | **REQUIRED** | `GET /v1.0/users/{userId}/onlineMeetings/{meetingId}/attendanceReports` | Importing post-class attendance |

> **CRITICAL VERIFICATION NOTE (`VERIFY WITH IT/MICROSOFT DOCS`)**:
> - **Delegated vs Application Endpoints**:
>   - In delegated flow, Microsoft Graph provides `POST /v1.0/me/onlineMeetings`.
>   - In application (daemon) flow, **`/me` DOES NOT EXIST**. The backend must explicitly call `POST /v1.0/users/{organizerUserId}/onlineMeetings` where `{organizerUserId}` is the Azure User Object ID or UPN of the class creator.
> - **Admin Consent**: A Microsoft 365 Global Administrator must click **"Grant admin consent for [Company Name]"** in Azure Portal under **API permissions**.

---

## 4. Teams Application Access Policy (PowerShell)

When using **Application permissions** (`OnlineMeetings.ReadWrite.All`), Microsoft Teams requires an **Application Access Policy** (`CsApplicationAccessPolicy`) to restrict which user mailboxes the application is allowed to act upon. Without this policy, Graph API calls to `/v1.0/users/{userId}/onlineMeetings` will fail with `HTTP 403 Forbidden: GeneralAccessDenied`.

### Step 4.1: Grant Application Access Policy via Teams PowerShell
*Must be executed by a **Teams Administrator** or **Global Administrator**.*

```powershell
# 1. Install and connect to Microsoft Teams PowerShell Module
Install-Module -Name MicrosoftTeams -Force -AllowClobber
Connect-MicrosoftTeams

# 2. Create the Application Access Policy linking your Azure Client ID
New-CsApplicationAccessPolicy -Identity "SkillHub-TeamsMeetingPolicy" `
    -AppIds "<AZURE_CLIENT_ID>" `
    -Description "Permits L&K Skill Hub to create online meetings on behalf of authorized mentors"

# 3. Option A: Grant policy to specific mentor/organizer mailboxes (Recommended Least Privilege)
Grant-CsApplicationAccessPolicy -PolicyName "SkillHub-TeamsMeetingPolicy" `
    -Identity "mentor.lead@yourcompany.com"

# 3. Option B: Grant policy tenant-wide (VERIFY WITH IT/MICROSOFT DOCS before applying globally)
# Grant-CsApplicationAccessPolicy -PolicyName "SkillHub-TeamsMeetingPolicy" -Global
```

*(Note: Policy propagation across Microsoft 365 can take 15 to 60 minutes).*

---

## 5. Teams Notification Bot Registration

L&K Skill Hub uses the modern **Azure Bot Service** / Bot Framework connector to dispatch class reminders, assessment notifications, and training deadlines directly to users in Microsoft Teams.
*(Notice: Legacy Office 365 connector webhooks have been deprecated by Microsoft and are NOT used).*

1. In Azure Portal, navigate to **Create a resource** > **Azure Bot**.
2. **Bot handle**: `LK-SkillHub-Bot`
3. **Pricing tier**: Standard or Free (F0).
4. **Microsoft App ID**: Select "Use existing app registration" (or create a dedicated bot registration).
5. Under **Channels**, add **Microsoft Teams** and accept the Terms of Service.
6. Populate `AZURE_BOT_APP_ID` and `AZURE_BOT_APP_PASSWORD` in `backend/.env`.

---

## 6. Pre-Flight Verification Checklist for IT

- [ ] Azure App Registration created as **Single tenant**.
- [ ] Redirect URI matches `AZURE_REDIRECT_URI` character-for-character with HTTPS in production.
- [ ] Client Secret generated and expiration tracked.
- [ ] Microsoft Graph API permissions added (`OnlineMeetings.ReadWrite.All`, `OnlineMeetingAttendanceReport.Read.All`).
- [ ] Global Admin clicked **"Grant admin consent for [Tenant]"**.
- [ ] Teams PowerShell executed: `New-CsApplicationAccessPolicy` and `Grant-CsApplicationAccessPolicy`.
- [ ] `APP_ENV="production"` set in `.env` (ensures mock providers are strictly barred from startup).
- [ ] Break-glass local administrator password verified and kept securely in corporate password vault.
