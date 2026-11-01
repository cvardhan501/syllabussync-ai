import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import jwt
from jwt import PyJWK
from fastapi import Header, HTTPException, status
from app.core.config import settings

logger = logging.getLogger("syllabus_sync.auth")


# ==============================================================================
# Base64URL Helpers
# ==============================================================================

def b64url_decode(segment: str) -> bytes:
    """Decodes standard base64url-encoded string with appropriate padding."""
    rem = len(segment) % 4
    if rem > 0:
        segment += "=" * (4 - rem)
    return base64.urlsafe_b64decode(segment)


def b64url_encode(data: bytes) -> str:
    """Encodes bytes into a base64url ASCII string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def ec_public_key_to_jwk(pub_key: Any, kid: str = "test-ec-kid-1") -> Dict[str, Any]:
    """Converts a cryptography ECPublicKey into a standard JWK dictionary."""
    numbers = pub_key.public_numbers()

    def _to_b64(val: int) -> str:
        return base64.urlsafe_b64encode(val.to_bytes(32, "big")).rstrip(b"=").decode("ascii")

    return {
        "kty": "EC",
        "crv": "P-256",
        "alg": "ES256",
        "use": "sig",
        "kid": kid,
        "x": _to_b64(numbers.x),
        "y": _to_b64(numbers.y),
    }


# ==============================================================================
# Supabase JWKS Public Key Cache (ES256 Verification)
# ==============================================================================

class SupabaseJWKSCache:
    """
    Thread-safe in-memory cache for Supabase public signing keys retrieved from JWKS.

    Security & Resilience Controls:
    1. Caches public keys with a configurable TTL (default 24 hours).
    2. When a token contains an unknown 'kid', triggers a dynamic refresh from the JWKS endpoint.
    3. Cooldown protection (minimum 5s between external network fetches) prevents DoS from malicious kids.
    4. Supports manual injection of mock keys for offline / unit testing.
    """

    def __init__(self, ttl_seconds: float = 86400.0, cooldown_seconds: float = 5.0):
        self._cache: Dict[str, PyJWK] = {}
        self._last_refresh: float = 0.0
        self._ttl_seconds: float = ttl_seconds
        self._cooldown_seconds: float = cooldown_seconds
        self._lock = threading.Lock()

    def get_key(self, kid: str) -> PyJWK:
        """
        Retrieves the public key for the requested key ID.
        Refreshes from the JWKS endpoint if the key is missing or the cache has expired.
        """
        now = time.time()
        # Fast-path cache lookup
        if kid in self._cache and (now - self._last_refresh) < self._ttl_seconds:
            return self._cache[kid]

        with self._lock:
            now = time.time()
            if kid in self._cache and (now - self._last_refresh) < self._ttl_seconds:
                return self._cache[kid]

            # Cooldown check: prevent hammering the endpoint if an invalid kid is flooded
            if (now - self._last_refresh) < self._cooldown_seconds and self._cache:
                if kid in self._cache:
                    return self._cache[kid]
                raise ValueError(
                    f"Key ID '{kid}' not found in Supabase JWKS cache (refresh cooldown active)."
                )

            # Fetch fresh JWKS from published endpoint
            self._refresh_from_endpoint()

            if kid in self._cache:
                return self._cache[kid]

            raise ValueError(
                f"Key ID '{kid}' was not found in Supabase JWKS at {settings.effective_jwks_url}."
            )

    def _refresh_from_endpoint(self) -> None:
        """Fetches the JWKS keys set from the configured Supabase JWKS URL."""
        url = settings.effective_jwks_url
        logger.info(f"Fetching Supabase JWKS public keys from {url}")
        try:
            with httpx.Client(timeout=6.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    raise ValueError(f"Supabase JWKS endpoint returned HTTP {resp.status_code}")
                jwks_data = resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch Supabase JWKS from '{url}': {e}")
            raise ValueError(f"Unable to reach Supabase JWKS endpoint: {str(e)}")

        keys = jwks_data.get("keys", [])
        if not keys:
            raise ValueError("Supabase JWKS endpoint returned an empty keys array.")

        new_keys: Dict[str, PyJWK] = {}
        for k in keys:
            k_id = k.get("kid")
            if k_id:
                try:
                    new_keys[k_id] = PyJWK.from_dict(k)
                except Exception as parse_err:
                    logger.warning(f"Failed to parse JWK key {k_id}: {parse_err}")

        if not new_keys:
            raise ValueError("No valid public keys could be loaded from Supabase JWKS.")

        self._cache.update(new_keys)
        self._last_refresh = time.time()
        logger.info(f"Successfully cached {len(new_keys)} Supabase JWKS keys: {list(new_keys.keys())}")

    def set_jwks_for_testing(self, keys_list: List[Dict[str, Any]]) -> None:
        """Pre-populates the cache with mock JWKs for deterministic unit testing."""
        with self._lock:
            self._cache = {k["kid"]: PyJWK.from_dict(k) for k in keys_list if "kid" in k}
            self._last_refresh = time.time()

    def clear_cache(self) -> None:
        """Clears the public key cache."""
        with self._lock:
            self._cache.clear()
            self._last_refresh = 0.0


jwks_cache = SupabaseJWKSCache()


# ==============================================================================
# JWT Claims Verification Engine
# ==============================================================================

def verify_supabase_jwt_claims(token: str) -> Dict[str, Any]:
    """
    Verifies a Supabase JWT token and extracts verified claims.

    Security Validations & Algorithm Routing:
    1. Structure: Exactly 3 dot-separated segments (header.payload.signature).
    2. Header: Extracts unverified header to determine signing algorithm ('alg') and 'kid'.
    3. Rejection of Insecure Algorithms:
       - 'alg: none' and unsigned tokens are strictly forbidden.
       - Unsupported algorithms (RS256, PS256, etc.) are rejected with clear errors.
    4. Algorithm Routing:
       - If 'alg' == 'ES256' (Current Supabase ECC P-256 standard):
         * Requires 'kid' header parameter.
         * Looks up matching public key from Supabase JWKS cache (refreshing on demand).
         * Verifies ECDSA signature using curve P-256 with SHA-256.
         * Strictly DOES NOT fallback to HS256 on verification failure.
       - If 'alg' == 'HS256' (Legacy Supabase shared secret):
         * Explicitly requires settings.supabase_jwt_secret.
         * Fails closed if secret is not configured in backend environment.
         * Verifies HMAC-SHA256 signature.
         * Strictly DOES NOT fallback to ES256 on verification failure.
    5. Standard Claim Enforcement:
       - 'exp': Expiration timestamp must be present and in the future.
       - 'sub': Subject claim (User UUID) must be present and non-empty.
       - 'aud': Audience must match 'authenticated' or 'anon'.
       - 'iss': If present, issuer must match the expected Supabase project auth URL.

    Raises:
        ValueError: On any signature mismatch, malformation, expired token, or claim error.
    """
    if not token or not token.strip():
        raise ValueError("Token is empty")

    clean_token = token.strip()
    parts = clean_token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed JWT: expected 3 dot-separated segments")

    # 1. Inspect unverified header for algorithm and key identifier
    try:
        unverified_header = jwt.get_unverified_header(clean_token)
    except Exception as e:
        raise ValueError(f"Malformed JWT header: {e}")

    alg = unverified_header.get("alg")
    if not alg or alg == "none":
        raise ValueError("Unsigned tokens ('alg': 'none') are strictly forbidden")

    expected_issuer = settings.expected_jwt_issuer

    # 2. Algorithm-Specific Signature Verification
    if alg == "ES256":
        kid = unverified_header.get("kid")
        if not kid or not str(kid).strip():
            raise ValueError("ES256 token is missing required 'kid' (Key ID) header")

        pyjwk = jwks_cache.get_key(str(kid).strip())
        public_key = pyjwk.key

        try:
            payload = jwt.decode(
                clean_token,
                key=public_key,
                algorithms=["ES256"],
                audience=["authenticated", "anon"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "require": ["exp", "sub"],
                },
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidSignatureError:
            raise ValueError("Invalid token signature")
        except jwt.InvalidAudienceError as e:
            raise ValueError(f"Invalid audience in token: {e}")
        except jwt.MissingRequiredClaimError as e:
            raise ValueError(f"Token missing required claim: {e}")
        except Exception as e:
            raise ValueError(f"JWT verification failed: {e}")

    elif alg == "HS256":
        jwt_secret = settings.supabase_jwt_secret
        if not jwt_secret or not jwt_secret.strip():
            raise ValueError(
                "HS256 token rejected: Supabase JWT secret is not configured in backend settings"
            )

        try:
            payload = jwt.decode(
                clean_token,
                key=jwt_secret,
                algorithms=["HS256"],
                audience=["authenticated", "anon"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "require": ["exp", "sub"],
                },
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidSignatureError:
            raise ValueError("Invalid token signature")
        except jwt.InvalidAudienceError as e:
            raise ValueError(f"Invalid audience in token: {e}")
        except jwt.MissingRequiredClaimError as e:
            raise ValueError(f"Token missing required claim: {e}")
        except Exception as e:
            raise ValueError(f"JWT verification failed: {e}")

    else:
        raise ValueError(
            f"Unsupported JWT algorithm '{alg}'. Only ES256 (via JWKS) and HS256 (symmetric secret) are supported"
        )

    # 3. Validate subject claim (User UUID)
    sub = payload.get("sub")
    if not sub or not str(sub).strip():
        raise ValueError("Token missing required subject claim ('sub')")

    # 4. Validate issuer claim if present in token or required
    iss = payload.get("iss")
    if expected_issuer and iss:
        if iss != expected_issuer:
            raise ValueError(f"Token issuer mismatch: expected '{expected_issuer}', got '{iss}'")

    return payload


def verify_supabase_jwt(token: str) -> str:
    """
    Verifies Supabase JWT and returns the verified user ID ('sub' claim).
    Raises ValueError on validation failure.
    """
    payload = verify_supabase_jwt_claims(token)
    return str(payload["sub"]).strip()


# ==============================================================================
# Testing Helpers (ES256 & HS256)
# ==============================================================================

def create_test_supabase_jwt(
    sub: str,
    secret: str = "test-secret-key-12345",
    expires_in: int = 3600,
    role: str = "authenticated",
    aud: str = "authenticated",
    iss: Optional[str] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Creates a signed HS256 JWT for unit and integration testing.
    Uses standard PyJWT HS256 signing.
    """
    payload = {
        "sub": sub,
        "role": role,
        "aud": aud,
        "exp": int(time.time()) + expires_in,
        "iat": int(time.time()),
    }
    if iss:
        payload["iss"] = iss
    elif settings.expected_jwt_issuer:
        payload["iss"] = settings.expected_jwt_issuer

    if extra_claims:
        payload.update(extra_claims)

    headers = {"alg": "HS256", "typ": "JWT"}
    return jwt.encode(payload, secret, algorithm="HS256", headers=headers)


def create_test_supabase_es256_jwt(
    sub: str,
    private_key: Optional[Any] = None,
    kid: str = "test-ec-kid-1",
    expires_in: int = 3600,
    role: str = "authenticated",
    aud: str = "authenticated",
    iss: Optional[str] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Any]:
    """
    Creates a signed ES256 JWT using an EC P-256 private key for testing.
    If private_key is omitted, generates a new EC P-256 key pair.
    Returns (token_string, private_key).
    """
    from cryptography.hazmat.primitives.asymmetric import ec

    if private_key is None:
        private_key = ec.generate_private_key(ec.SECP256R1())

    payload = {
        "sub": sub,
        "role": role,
        "aud": aud,
        "exp": int(time.time()) + expires_in,
        "iat": int(time.time()),
    }
    if iss:
        payload["iss"] = iss
    elif settings.expected_jwt_issuer:
        payload["iss"] = settings.expected_jwt_issuer

    if extra_claims:
        payload.update(extra_claims)

    headers = {"alg": "ES256", "typ": "JWT", "kid": kid}
    token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
    return token, private_key


# ==============================================================================
# FastAPI Dependency & Enforcers
# ==============================================================================

async def get_current_user_id(
    x_user_id: Optional[str] = Header(
        None,
        alias="X-User-Id",
        description="Simulated user UUID (permitted ONLY in development and testing).",
    ),
    authorization: Optional[str] = Header(
        None,
        alias="Authorization",
        description="Bearer token (verified Supabase JWT in production).",
    ),
) -> Optional[str]:
    """
    Extracts and authenticates the active user ID based on environment context.

    Security & Environment Rules:
    1. Production (settings.is_production):
       - 'X-User-Id' simulation is strictly rejected and never trusted.
       - Missing, malformed, or invalid Authorization headers return HTTP 401 Unauthorized.
       - Bearer tokens are rigorously verified for ES256 (via JWKS) or HS256 signature, expiration, and claims.
       - Never returns None in production; unauthenticated requests fail immediately.

    2. Development / Testing (!settings.is_production):
       - If Authorization header is provided, it must be a valid, signed Supabase JWT.
         Unverified tokens, forged signatures, or malformed tokens return HTTP 401 Unauthorized.
         Unverified JWT decoding (verify_signature=False) is strictly forbidden.
       - If no Authorization header is provided, 'X-User-Id' is permitted for local identity simulation.
       - If neither is provided, returns None (unauthenticated local development mode).
    """
    if settings.is_production:
        if x_user_id:
            logger.warning(
                "Production security warning: X-User-Id simulation header was provided in "
                "production environment and was ignored."
            )

        if not authorization or not authorization.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required: Missing Authorization header in production.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme: Bearer token is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization[7:].strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token: Token payload is empty.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            return verify_supabase_jwt(token)
        except Exception as e:
            logger.warning(f"Production JWT verification failure: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Development or Testing mode (!settings.is_production)
    # If Authorization header is provided, strictly verify the Supabase JWT
    if authorization and authorization.strip():
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme: Bearer token is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization[7:].strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token: Token payload is empty.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            return verify_supabase_jwt(token)
        except Exception as e:
            logger.warning(f"Development JWT verification failure: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # In development/testing, allow X-User-Id simulation when Authorization header is absent
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    return None


def verify_ownership(
    resource_owner_id: Optional[Any],
    current_user_id: Optional[Any],
    resource_type: str = "resource",
) -> None:
    """
    Centrally enforces data ownership and multi-tenant access control.
    Supports both str and uuid.UUID representations robustly.

    Access Rules:
    1. Production mode (settings.is_production):
       - current_user_id must be non-empty (authenticated).
       - If resource_owner_id is None:
         Denies access with HTTP 403 Forbidden. Unowned legacy records must NOT be accessible in production.
       - If resource_owner_id != current_user_id:
         Denies access with HTTP 403 Forbidden. Knowing an ID does not grant permission.

    2. Development / Testing mode (!settings.is_production):
       - If resource_owner_id is None:
         Permits access to legacy local records.
       - If resource_owner_id is not None and current_user_id is not None:
         If resource_owner_id != current_user_id:
             Raises HTTP 403 Forbidden.
    """
    norm_owner = str(resource_owner_id).strip().lower() if resource_owner_id is not None else None
    norm_current = str(current_user_id).strip().lower() if current_user_id is not None else None

    if settings.is_production:
        if not norm_current:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if norm_owner is None:
            logger.warning(
                f"Production security block: authenticated user '{current_user_id}' attempted to access "
                f"unowned legacy {resource_type}."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Legacy unowned {resource_type}s cannot be accessed in production.",
            )
        if norm_owner != norm_current:
            logger.warning(
                f"Unauthorized access attempt: user '{current_user_id}' attempted to access "
                f"{resource_type} owned by '{resource_owner_id}'."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: You do not have permission to access or modify this {resource_type}.",
            )
    else:
        # Development / Testing mode
        if norm_owner is not None and norm_current is not None:
            if norm_owner != norm_current:
                logger.warning(
                    f"Unauthorized access attempt: user '{current_user_id}' attempted to access "
                    f"{resource_type} owned by '{resource_owner_id}'."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: You do not have permission to access or modify this {resource_type}.",
                )


async def verify_diagnostics_access(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
) -> None:
    """
    Secures diagnostics and test probe endpoints in production.
    - In development/test: unrestricted for local UI diagnostics.
    - In production: requires either:
        a) Valid X-Admin-Key header matching settings.admin_api_key, OR
        b) Valid Supabase JWT with role in ('service_role', 'admin', 'supabase_admin')
           or app_metadata.is_admin is True.
      Otherwise raises HTTP 403 Forbidden.
    """
    if not settings.is_production:
        return

    # Check X-Admin-Key header
    if settings.admin_api_key and x_admin_key:
        if hmac.compare_digest(x_admin_key.strip(), settings.admin_api_key.strip()):
            return

    # Check Bearer JWT claims
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        try:
            claims = verify_supabase_jwt_claims(token)
            role = claims.get("role")
            app_meta = claims.get("app_metadata", {})
            if role in ("service_role", "admin", "supabase_admin") or app_meta.get("is_admin") is True:
                return
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Administrative privileges required to access diagnostics in production.",
    )
