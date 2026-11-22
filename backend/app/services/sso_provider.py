import base64
import hashlib
import json
import secrets
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
import jwt
from jwt.algorithms import RSAAlgorithm
import httpx
from app.core.config import settings

class SSOValidationError(Exception):
    def __init__(self, message: str, internal_code: str = "SSO_ERROR"):
        super().__init__(message)
        self.message = message
        self.internal_code = internal_code


class SSOProvider(ABC):
    @abstractmethod
    def generate_authorization_url(self, state: str, nonce: str, code_challenge: str, redirect_uri: str) -> str:
        """Constructs OIDC authorization URL with PKCE."""
        pass

    @abstractmethod
    def exchange_and_validate(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        expected_nonce: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Exchanges authorization code for ID/access tokens, performs full cryptographic
        and claim validation, and returns normalized verified claims (tid, oid, upn, email, name, refresh_token).
        """
        pass


class AzureOIDCProvider(SSOProvider):
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        jwks_override: Optional[Dict[str, Any]] = None
    ):
        self.tenant_id = tenant_id or settings.AZURE_TENANT_ID
        self.client_id = client_id or settings.AZURE_CLIENT_ID
        self.client_secret = client_secret or settings.AZURE_CLIENT_SECRET
        self.jwks_override = jwks_override
        self._cached_jwks: Optional[Dict[str, Any]] = None
        self._jwks_fetched_at: float = 0
        self._jwks_ttl: float = 3600.0 # 1 hour

    @property
    def discovery_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0/.well-known/openid-configuration"

    @property
    def jwks_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"

    @property
    def expected_issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"

    def generate_authorization_url(self, state: str, nonce: str, code_challenge: str, redirect_uri: str) -> str:
        base_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": "openid profile email offline_access",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        encoded = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{encoded}"

    def get_jwks(self, force_refresh: bool = False) -> Dict[str, Any]:
        if self.jwks_override:
            return self.jwks_override

        now = time.time()
        if not force_refresh and self._cached_jwks and (now - self._jwks_fetched_at < self._jwks_ttl):
            return self._cached_jwks

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(self.jwks_url)
                if res.status_code != 200:
                    raise SSOValidationError(
                        "Unable to fetch Microsoft public keys.",
                        internal_code="JWKS_FETCH_FAILED"
                    )
                self._cached_jwks = res.json()
                self._jwks_fetched_at = now
                return self._cached_jwks
        except httpx.RequestError as exc:
            raise SSOValidationError(
                "Unable to connect to Microsoft identity service.",
                internal_code=f"JWKS_NETWORK_ERROR: {str(exc)}"
            )

    def validate_id_token(
        self,
        id_token: str,
        expected_nonce: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cryptographically validates Microsoft ID token against JWKS with strict claim checks."""
        try:
            unverified_header = jwt.get_unverified_header(id_token)
        except Exception:
            raise SSOValidationError("Invalid token structure.", internal_code="MALFORMED_HEADER")

        alg = unverified_header.get("alg")
        if not alg or alg.upper() == "NONE" or alg.upper().startswith("HS"):
            raise SSOValidationError(
                "Unsupported signing algorithm.",
                internal_code=f"INSECURE_ALGORITHM: {alg}"
            )

        kid = unverified_header.get("kid")
        if not kid:
            raise SSOValidationError("Missing key ID in token header.", internal_code="MISSING_KID")

        jwks = self.get_jwks()
        key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key_data:
            # Attempt one forced key refresh for key rotation
            jwks = self.get_jwks(force_refresh=True)
            key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)

        if not key_data:
            raise SSOValidationError("Unknown token signing key.", internal_code="UNKNOWN_KID")

        try:
            public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
        except Exception as exc:
            raise SSOValidationError("Invalid signing key format.", internal_code=f"KEY_CONVERSION_FAILED: {str(exc)}")

        try:
            claims = jwt.decode(
                id_token,
                key=public_key,
                algorithms=["RS256", "RS384", "RS512"],
                audience=self.client_id,
                issuer=self.expected_issuer,
                leeway=60, # 60 seconds clock skew tolerance
                options={"verify_signature": True, "verify_aud": True, "verify_exp": True, "verify_iss": True}
            )
        except jwt.ExpiredSignatureError:
            raise SSOValidationError("ID token has expired.", internal_code="TOKEN_EXPIRED")
        except jwt.ImmatureSignatureError:
            raise SSOValidationError("Token is not yet valid (nbf check failed).", internal_code="TOKEN_NOT_YET_VALID")
        except jwt.InvalidAudienceError:
            raise SSOValidationError("Invalid token audience.", internal_code="AUDIENCE_MISMATCH")
        except jwt.InvalidIssuerError:
            raise SSOValidationError("Invalid token issuer.", internal_code="ISSUER_MISMATCH")
        except jwt.InvalidSignatureError:
            raise SSOValidationError("Tampered or invalid token signature.", internal_code="SIGNATURE_VERIFICATION_FAILED")
        except Exception as exc:
            raise SSOValidationError("Token verification failed.", internal_code=f"DECODE_ERROR: {str(exc)}")

        # Validate tenant ID claim
        token_tid = claims.get("tid")
        if not token_tid or token_tid.lower() != self.tenant_id.lower():
            raise SSOValidationError("Unauthorized tenant.", internal_code=f"TENANT_MISMATCH: {token_tid}")

        # Validate nonce
        if expected_nonce:
            token_nonce = claims.get("nonce")
            if not token_nonce or token_nonce != expected_nonce:
                raise SSOValidationError("Replay attack detected: invalid nonce.", internal_code="NONCE_REPLAY")

        return claims

    def exchange_and_validate(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        expected_nonce: str,
        **kwargs
    ) -> Dict[str, Any]:
        # If raw id_token passed in kwargs (for tests or mocked exchange)
        id_token = kwargs.get("id_token")
        refresh_token = kwargs.get("refresh_token")

        if not id_token:
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier
            }
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(token_url, data=data)
                    if resp.status_code != 200:
                        raise SSOValidationError(
                            "Failed to exchange authorization code with Microsoft.",
                            internal_code=f"TOKEN_EXCHANGE_HTTP_{resp.status_code}: {resp.text}"
                        )
                    token_data = resp.json()
                    id_token = token_data.get("id_token")
                    refresh_token = token_data.get("refresh_token")
            except httpx.RequestError as exc:
                raise SSOValidationError(
                    "Network failure communicating with Microsoft OAuth endpoint.",
                    internal_code=f"EXCHANGE_NETWORK_ERROR: {str(exc)}"
                )

        if not id_token:
            raise SSOValidationError("No ID token returned by identity provider.", internal_code="NO_ID_TOKEN")

        claims = self.validate_id_token(id_token, expected_nonce=expected_nonce)

        # Normalize claims
        tid = claims.get("tid")
        oid = claims.get("oid")
        email = (claims.get("preferred_username") or claims.get("email") or claims.get("upn") or "").strip().lower()
        name = claims.get("name") or email.split("@")[0]

        if not email or "@" not in email:
            raise SSOValidationError("No verified email or UPN present in token.", internal_code="MISSING_VERIFIED_EMAIL")

        return {
            "tid": tid,
            "oid": oid,
            "email": email,
            "name": name,
            "upn": email,
            "refresh_token": refresh_token,
            "claims": claims
        }


class MockSSOProvider(SSOProvider):
    def __init__(self):
        if settings.APP_ENV.lower() == "production":
            raise RuntimeError(
                "CRITICAL SECURITY VIOLATION: MockSSOProvider cannot be initialized in production environment!"
            )

    def generate_authorization_url(self, state: str, nonce: str, code_challenge: str, redirect_uri: str) -> str:
        return f"{redirect_uri}?mock_sso=1&state={state}&nonce={nonce}"

    def exchange_and_validate(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        expected_nonce: str,
        **kwargs
    ) -> Dict[str, Any]:
        if settings.APP_ENV.lower() == "production":
            raise RuntimeError("CRITICAL SECURITY VIOLATION: MockSSOProvider cannot execute in production!")

        # Allow caller to pass mock email / user
        mock_email = kwargs.get("email") or "ase.demo@csm.tech"
        mock_oid = kwargs.get("oid") or "mock-azure-oid-12345"
        mock_tid = kwargs.get("tid") or (settings.AZURE_TENANT_ID or "mock-tenant-id")
        mock_name = kwargs.get("name") or "Mock Azure User"

        return {
            "tid": mock_tid,
            "oid": mock_oid,
            "email": mock_email.strip().lower(),
            "name": mock_name,
            "upn": mock_email.strip().lower(),
            "refresh_token": "mock-refresh-token-xyz",
            "claims": {
                "tid": mock_tid,
                "oid": mock_oid,
                "email": mock_email,
                "name": mock_name,
                "nonce": expected_nonce
            }
        }


def get_sso_provider(override_type: Optional[str] = None) -> SSOProvider:
    provider_type = (override_type or settings.SSO_PROVIDER_TYPE).lower()

    if settings.APP_ENV.lower() == "production":
        if provider_type == "mock":
            raise RuntimeError("CRITICAL SECURITY VIOLATION: Mock SSO cannot be enabled when APP_ENV=production!")
        if not (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID):
            raise RuntimeError("SSO is disabled: Azure credentials (AZURE_TENANT_ID, AZURE_CLIENT_ID) are not configured.")
        return AzureOIDCProvider()

    if provider_type == "mock":
        return MockSSOProvider()
    elif provider_type == "azure":
        return AzureOIDCProvider()

    # "auto" detection
    if settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID:
        return AzureOIDCProvider()
    return MockSSOProvider()
