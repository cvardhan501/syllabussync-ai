import time
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
import jwt
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.auth import (
    jwks_cache,
    ec_public_key_to_jwk,
    create_test_supabase_es256_jwt,
    create_test_supabase_jwt,
    verify_supabase_jwt,
    verify_supabase_jwt_claims,
)
from app.models.database import delete_course

client = TestClient(app)

TEST_HS256_SECRET = "test-legacy-hs256-shared-secret-32ch!"


@pytest.fixture(autouse=True)
def setup_teardown_auth_environment():
    """Ensure clean environment and JWKS cache for each test."""
    orig_env = settings.app_env
    orig_secret = settings.supabase_jwt_secret
    orig_project_url = settings.supabase_project_url
    orig_jwks_url = settings.supabase_jwks_url

    # Standard Supabase project test settings
    settings.app_env = "production"
    settings.supabase_project_url = "https://qdlnupgdtgmhvkknjmlv.supabase.co"
    settings.supabase_jwt_secret = TEST_HS256_SECRET

    yield

    settings.app_env = orig_env
    settings.supabase_jwt_secret = orig_secret
    settings.supabase_project_url = orig_project_url
    settings.supabase_jwks_url = orig_jwks_url
    jwks_cache.clear_cache()


def test_valid_es256_token_verifies_successfully_via_jwks():
    """
    Requirement 2, 3, 4: Valid ES256 token signed by matching EC P-256 key
    verifies correctly using the public key matching token's kid.
    """
    priv_key = ec.generate_private_key(ec.SECP256R1())
    kid = "supabase-ec-key-test-1"
    jwk_dict = ec_public_key_to_jwk(priv_key.public_key(), kid=kid)
    jwks_cache.set_jwks_for_testing([jwk_dict])

    user_uuid = "student-es256-uuid-1111"
    token, _ = create_test_supabase_es256_jwt(
        sub=user_uuid,
        private_key=priv_key,
        kid=kid,
        expires_in=3600,
        role="authenticated",
        aud="authenticated",
        iss="https://qdlnupgdtgmhvkknjmlv.supabase.co/auth/v1",
    )

    verified_sub = verify_supabase_jwt(token)
    assert verified_sub == user_uuid

    claims = verify_supabase_jwt_claims(token)
    assert claims["sub"] == user_uuid
    assert claims["aud"] == "authenticated"
    assert claims["role"] == "authenticated"
    assert claims["iss"] == "https://qdlnupgdtgmhvkknjmlv.supabase.co/auth/v1"


def test_es256_invalid_signature_rejected():
    """
    Requirement 5: Token signed by an unknown/wrong private key must fail signature verification.
    """
    key_a = ec.generate_private_key(ec.SECP256R1())
    key_b = ec.generate_private_key(ec.SECP256R1())  # Imposter key
    kid = "supabase-ec-key-test-2"

    # Cache has Key A's public key
    jwk_dict = ec_public_key_to_jwk(key_a.public_key(), kid=kid)
    jwks_cache.set_jwks_for_testing([jwk_dict])

    # Token signed with Key B, claiming Key A's kid
    token, _ = create_test_supabase_es256_jwt(
        sub="student-uuid-attacker",
        private_key=key_b,
        kid=kid,
    )

    with pytest.raises(ValueError, match="Invalid token signature"):
        verify_supabase_jwt(token)


def test_es256_expired_token_rejected():
    """
    Requirement 4 & 5: Expired tokens must be strictly rejected.
    """
    priv_key = ec.generate_private_key(ec.SECP256R1())
    kid = "supabase-ec-key-test-3"
    jwks_cache.set_jwks_for_testing([ec_public_key_to_jwk(priv_key.public_key(), kid=kid)])

    token, _ = create_test_supabase_es256_jwt(
        sub="student-uuid-expired",
        private_key=priv_key,
        kid=kid,
        expires_in=-30,  # Expired 30 seconds ago
    )

    with pytest.raises(ValueError, match="Token has expired"):
        verify_supabase_jwt(token)


def test_es256_missing_kid_rejected():
    """
    Requirement 3: ES256 tokens without a 'kid' header must be rejected.
    """
    priv_key = ec.generate_private_key(ec.SECP256R1())
    payload = {
        "sub": "user-without-kid",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        "iss": settings.expected_jwt_issuer,
    }
    # No kid in header
    token = jwt.encode(payload, priv_key, algorithm="ES256", headers={"alg": "ES256"})

    with pytest.raises(ValueError, match="missing required 'kid'"):
        verify_supabase_jwt(token)


def test_es256_unknown_kid_rejected():
    """
    Requirement 3 & 6: Token referencing an unknown kid not found in JWKS must be rejected.
    """
    priv_key = ec.generate_private_key(ec.SECP256R1())
    # Cache only knows key-1
    jwks_cache.set_jwks_for_testing([ec_public_key_to_jwk(priv_key.public_key(), kid="known-key-1")])

    # Token requests unknown-key-999
    token, _ = create_test_supabase_es256_jwt(
        sub="student-uuid-unknown-kid",
        private_key=priv_key,
        kid="unknown-key-999",
    )

    with pytest.raises(ValueError, match="not found in Supabase JWKS"):
        verify_supabase_jwt(token)


def test_es256_wrong_issuer_rejected():
    """
    Requirement 4: Token from a different Supabase project/issuer must be rejected.
    """
    priv_key = ec.generate_private_key(ec.SECP256R1())
    kid = "supabase-ec-key-test-iss"
    jwks_cache.set_jwks_for_testing([ec_public_key_to_jwk(priv_key.public_key(), kid=kid)])

    token, _ = create_test_supabase_es256_jwt(
        sub="student-wrong-issuer",
        private_key=priv_key,
        kid=kid,
        iss="https://other-rogue-project.supabase.co/auth/v1",
    )

    with pytest.raises(ValueError, match="Token issuer mismatch"):
        verify_supabase_jwt(token)


def test_es256_wrong_audience_rejected():
    """
    Requirement 4: Token with an invalid audience claim must be rejected.
    """
    priv_key = ec.generate_private_key(ec.SECP256R1())
    kid = "supabase-ec-key-test-aud"
    jwks_cache.set_jwks_for_testing([ec_public_key_to_jwk(priv_key.public_key(), kid=kid)])

    token, _ = create_test_supabase_es256_jwt(
        sub="student-wrong-aud",
        private_key=priv_key,
        kid=kid,
        aud="untrusted-external-audience",
    )

    with pytest.raises(ValueError, match="Invalid audience"):
        verify_supabase_jwt(token)


def test_es256_missing_sub_rejected():
    """
    Requirement 4: Token missing subject claim ('sub') must be rejected.
    """
    priv_key = ec.generate_private_key(ec.SECP256R1())
    kid = "supabase-ec-key-test-sub"
    jwks_cache.set_jwks_for_testing([ec_public_key_to_jwk(priv_key.public_key(), kid=kid)])

    payload = {
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        "iss": settings.expected_jwt_issuer,
    }
    token = jwt.encode(payload, priv_key, algorithm="ES256", headers={"alg": "ES256", "kid": kid})

    with pytest.raises(ValueError, match="Token missing required.*sub"):
        verify_supabase_jwt(token)


def test_unsupported_algorithms_rejected():
    """
    Requirement 5: alg=none and unsupported algorithms (e.g. RS256, PS256) must be rejected.
    """
    # 1. alg=none
    unsigned_token = "eyJhbGciOiAibm9uZSIgLCJ0eXAiOiAiSldUIn0.eyJzdWIiOiAidXNlci0xMjMifQ."
    with pytest.raises(ValueError, match="strictly forbidden"):
        verify_supabase_jwt(unsigned_token)

    # 2. alg=RS256 (not supported when expecting ES256/HS256)
    from cryptography.hazmat.primitives.asymmetric import rsa
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_token = jwt.encode({"sub": "u1", "exp": int(time.time()) + 3600}, rsa_key, algorithm="RS256")
    with pytest.raises(ValueError, match="Unsupported JWT algorithm 'RS256'"):
        verify_supabase_jwt(rsa_token)


def test_legacy_hs256_token_supported_explicitly():
    """
    Requirement 9: Legacy HS256 tokens remain explicitly supported using settings.supabase_jwt_secret.
    """
    settings.supabase_jwt_secret = TEST_HS256_SECRET
    user_uuid = "legacy-student-hs256-uuid"
    hs256_token = create_test_supabase_jwt(sub=user_uuid, secret=TEST_HS256_SECRET)

    verified_sub = verify_supabase_jwt(hs256_token)
    assert verified_sub == user_uuid


def test_failed_es256_does_not_fallback_to_hs256():
    """
    Requirement 9: An invalid ES256 token must FAIL directly and NEVER fallback to HS256.
    """
    settings.supabase_jwt_secret = TEST_HS256_SECRET

    key_a = ec.generate_private_key(ec.SECP256R1())
    key_b = ec.generate_private_key(ec.SECP256R1())
    kid = "es256-no-fallback-test"
    jwks_cache.set_jwks_for_testing([ec_public_key_to_jwk(key_a.public_key(), kid=kid)])

    # Token signed with key B (invalid signature)
    bad_es256_token, _ = create_test_supabase_es256_jwt(
        sub="attacker-sub",
        private_key=key_b,
        kid=kid,
    )

    with pytest.raises(ValueError, match="Invalid token signature"):
        verify_supabase_jwt(bad_es256_token)


def test_jwks_cache_refresh_on_new_kid():
    """
    Requirement 6: Dynamic cache retrieval and refresh when a new kid arrives.
    """
    key_1 = ec.generate_private_key(ec.SECP256R1())
    key_2 = ec.generate_private_key(ec.SECP256R1())

    # Pre-populate cache with only key-1
    jwks_cache.set_jwks_for_testing([ec_public_key_to_jwk(key_1.public_key(), kid="key-1")])
    assert jwks_cache.get_key("key-1") is not None

    # Now add key-2 to simulated JWKS
    jwks_cache.set_jwks_for_testing([
        ec_public_key_to_jwk(key_1.public_key(), kid="key-1"),
        ec_public_key_to_jwk(key_2.public_key(), kid="key-2"),
    ])

    token_2, _ = create_test_supabase_es256_jwt(sub="user-key-2", private_key=key_2, kid="key-2")
    assert verify_supabase_jwt(token_2) == "user-key-2"


def test_prod_api_es256_end_to_end_and_user_isolation():
    """
    Requirement 7, 8, 10: Full end-to-end API test with ES256 Bearer tokens in production mode.
    Tests user identity extraction, course creation, and cross-user isolation.
    """
    settings.app_env = "production"

    key_user_a = ec.generate_private_key(ec.SECP256R1())
    key_user_b = ec.generate_private_key(ec.SECP256R1())

    kid_a = "kid-student-alpha"
    kid_b = "kid-student-beta"

    jwks_cache.set_jwks_for_testing([
        ec_public_key_to_jwk(key_user_a.public_key(), kid=kid_a),
        ec_public_key_to_jwk(key_user_b.public_key(), kid=kid_b),
    ])

    user_a = "supabase-es256-student-alpha"
    user_b = "supabase-es256-student-beta"

    token_a, _ = create_test_supabase_es256_jwt(sub=user_a, private_key=key_user_a, kid=kid_a)
    token_b, _ = create_test_supabase_es256_jwt(sub=user_b, private_key=key_user_b, kid=kid_b)

    # 1. User A creates a course with ES256 Bearer token
    res_a = client.post(
        "/api/courses",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"course_name": "Distributed Systems ES256", "course_code": "CS401"},
    )
    assert res_a.status_code == 201
    course_data = res_a.json()
    assert course_data["owner_user_id"] == user_a
    course_id = course_data["id"]

    try:
        # 2. User A retrieves their own course
        res_get_a = client.get(f"/api/courses/{course_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert res_get_a.status_code == 200
        assert res_get_a.json()["id"] == course_id

        # 3. User B attempts to access User A's course -> 403 Forbidden (cross-user isolation)
        res_get_b = client.get(f"/api/courses/{course_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert res_get_b.status_code == 403
        assert "Access denied" in res_get_b.json()["detail"]

        # 4. In production, request without Bearer token -> 401 Unauthorized
        res_unauth = client.get(f"/api/courses/{course_id}")
        assert res_unauth.status_code == 401

        # 5. In production, X-User-Id spoofing attempt -> 401 Unauthorized
        res_spoof = client.get(f"/api/courses/{course_id}", headers={"X-User-Id": user_a})
        assert res_spoof.status_code == 401

    finally:
        delete_course(course_id, owner_user_id=user_a)
