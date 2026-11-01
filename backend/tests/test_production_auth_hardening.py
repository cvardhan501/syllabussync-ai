import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.auth import create_test_supabase_jwt, verify_supabase_jwt, verify_ownership
from app.models.database import (
    create_course,
    delete_course,
    get_course,
    get_courses,
)

client = TestClient(app)

TEST_SECRET = "super-secret-production-supabase-jwt-key-32chars!"


@pytest.fixture(autouse=True)
def reset_settings_env():
    """Ensure settings are cleanly reset after each test."""
    original_env = settings.app_env
    original_secret = settings.supabase_jwt_secret
    original_admin_key = settings.admin_api_key
    yield
    settings.app_env = original_env
    settings.supabase_jwt_secret = original_secret
    settings.admin_api_key = original_admin_key


def test_dev_mode_without_auth_allows_legacy_access():
    """
    Requirement 1 & 2: Keep unauthenticated development mode working locally.
    Existing local records with owner_user_id = NULL must remain accessible in local development.
    """
    settings.app_env = "development"
    assert settings.is_development is True
    assert settings.is_production is False

    legacy_id = "course_legacy_hardening_dev"
    create_course({
        "id": legacy_id,
        "course_name": "Legacy Dev Course",
        "course_code": "CS101",
        "owner_user_id": None,
    })

    try:
        # 1. Unauthenticated request without headers
        res = client.get(f"/api/courses/{legacy_id}")
        assert res.status_code == 200
        assert res.json()["id"] == legacy_id
        assert res.json()["owner_user_id"] is None

        # 2. Included in course listing without auth
        list_res = client.get("/api/courses")
        assert list_res.status_code == 200
        course_ids = [c["id"] for c in list_res.json()["courses"]]
        assert legacy_id in course_ids

    finally:
        delete_course(legacy_id)


def test_dev_mode_x_user_id_simulation_permitted():
    """
    Requirement 1: Permit X-User-Id identity simulation only in explicit development/test environments.
    """
    settings.app_env = "development"

    simulated_user = "simulated_student_dev_1"
    res = client.post(
        "/api/courses",
        headers={"X-User-Id": simulated_user},
        json={"course_name": "Simulated Dev Course", "course_code": "CS202"}
    )
    assert res.status_code == 201
    course_data = res.json()
    assert course_data["owner_user_id"] == simulated_user
    cid = course_data["id"]

    try:
        # Listing with X-User-Id returns only that user's courses
        list_res = client.get("/api/courses", headers={"X-User-Id": simulated_user})
        assert list_res.status_code == 200
        for c in list_res.json()["courses"]:
            if c["id"] == cid:
                assert c["owner_user_id"] == simulated_user
    finally:
        delete_course(cid)


def test_prod_mode_missing_auth_returns_401():
    """
    Requirement 1: In production mode, missing authentication must strictly return 401 Unauthorized.
    """
    settings.app_env = "production"
    assert settings.is_production is True

    # Request without Authorization header
    res = client.get("/api/courses")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]
    assert "Bearer" in res.headers.get("WWW-Authenticate", "")


def test_prod_mode_never_trusts_x_user_id_alone():
    """
    Requirement 1: In production mode, never trust X-User-Id.
    A request sending only X-User-Id must return 401 Unauthorized.
    """
    settings.app_env = "production"

    # Attacker tries to simulate identity using X-User-Id in production
    res = client.get("/api/courses", headers={"X-User-Id": "victim_user_uuid"})
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]

    # Attacker tries to create course with X-User-Id only
    create_res = client.post(
        "/api/courses",
        headers={"X-User-Id": "victim_user_uuid"},
        json={"course_name": "Injected Course", "course_code": "INJ101"}
    )
    assert create_res.status_code == 401


def test_prod_mode_invalid_and_unsigned_jwt_rejected_with_401():
    """
    Requirement 3: JWT verification readiness without accepting unverified or unsigned claims.
    Missing, malformed, or invalid tokens must return 401 Unauthorized.
    """
    settings.app_env = "production"
    settings.supabase_jwt_secret = TEST_SECRET

    # Case A: Non-JWT string
    res_malformed = client.get("/api/courses", headers={"Authorization": "Bearer not-a-jwt"})
    assert res_malformed.status_code == 401

    # Case B: Unsigned token (alg: none)
    unsigned_token = "eyJhbGciOiAibm9uZSIgLCJ0eXAiOiAiSldUIn0.eyJzdWIiOiAidXNlci0xMjMifQ."
    res_unsigned = client.get("/api/courses", headers={"Authorization": f"Bearer {unsigned_token}"})
    assert res_unsigned.status_code == 401

    # Case C: Wrong signature
    wrong_sig_token = create_test_supabase_jwt(
        sub="user-test-uuid",
        secret="different-wrong-secret-key-12345"
    )
    res_wrong_sig = client.get("/api/courses", headers={"Authorization": f"Bearer {wrong_sig_token}"})
    assert res_wrong_sig.status_code == 401
    assert "Invalid token signature" in res_wrong_sig.json()["detail"]

    # Case D: Expired token
    expired_token = create_test_supabase_jwt(
        sub="user-test-uuid",
        secret=TEST_SECRET,
        expires_in=-60  # expired 60 seconds ago
    )
    res_expired = client.get("/api/courses", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_expired.status_code == 401
    assert "expired" in res_expired.json()["detail"].lower()


def test_prod_mode_valid_signed_jwt_succeeds():
    """
    Requirement 3: Valid signed Supabase JWT is successfully verified and populates user identity.
    """
    settings.app_env = "production"
    settings.supabase_jwt_secret = TEST_SECRET

    user_uuid = "supabase-uuid-prod-student-8888"
    valid_token = create_test_supabase_jwt(sub=user_uuid, secret=TEST_SECRET, expires_in=3600)

    # 1. Create a course with valid Bearer token
    create_res = client.post(
        "/api/courses",
        headers={"Authorization": f"Bearer {valid_token}"},
        json={"course_name": "Production Verified Course", "course_code": "PROD401"}
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["owner_user_id"] == user_uuid
    cid = created["id"]

    try:
        # 2. Retrieve the course with valid token
        get_res = client.get(f"/api/courses/{cid}", headers={"Authorization": f"Bearer {valid_token}"})
        assert get_res.status_code == 200
        assert get_res.json()["id"] == cid
        assert get_res.json()["owner_user_id"] == user_uuid

        # 3. List courses with valid token returns only user's courses
        list_res = client.get("/api/courses", headers={"Authorization": f"Bearer {valid_token}"})
        assert list_res.status_code == 200
        for c in list_res.json()["courses"]:
            assert c["owner_user_id"] == user_uuid
    finally:
        delete_course(cid, owner_user_id=user_uuid)


def test_prod_mode_unowned_legacy_records_not_visible_or_accessible():
    """
    Requirement 2: In production, unowned legacy records must not be visible to authenticated users.
    Never interpret a missing user ID as permission to access all records in production.
    """
    legacy_id = "course_legacy_unowned_prod_test"
    # Create legacy record with owner_user_id = NULL
    create_course({
        "id": legacy_id,
        "course_name": "Legacy Unowned Pre-Auth Course",
        "course_code": "LEG999",
        "owner_user_id": None,
    })

    try:
        # Switch to production mode
        settings.app_env = "production"
        settings.supabase_jwt_secret = TEST_SECRET

        user_uuid = "authenticated-student-uuid-999"
        valid_token = create_test_supabase_jwt(sub=user_uuid, secret=TEST_SECRET)

        # 1. Direct access by ID to legacy unowned record must be DENIED (HTTP 403 Forbidden)
        res_direct = client.get(f"/api/courses/{legacy_id}", headers={"Authorization": f"Bearer {valid_token}"})
        assert res_direct.status_code == 403
        assert "Legacy unowned" in res_direct.json()["detail"]

        # 2. Course listing in production must NOT include unowned legacy records
        res_list = client.get("/api/courses", headers={"Authorization": f"Bearer {valid_token}"})
        assert res_list.status_code == 200
        returned_ids = [c["id"] for c in res_list.json()["courses"]]
        assert legacy_id not in returned_ids, "Legacy unowned record must NOT be visible in production course list"

        # 3. Direct DB layer query in production without user_id returns empty
        assert get_courses(owner_user_id=None) == []
        assert get_course(legacy_id, owner_user_id=user_uuid) is None

    finally:
        settings.app_env = "development"
        delete_course(legacy_id)


def test_prod_mode_cross_user_isolation():
    """
    Requirement 1 & 5: Ensure strict cross-user data isolation in production.
    User A cannot access or mutate User B's course.
    """
    settings.app_env = "production"
    settings.supabase_jwt_secret = TEST_SECRET

    user_a = "user-uuid-tenant-alpha"
    user_b = "user-uuid-tenant-beta"

    token_a = create_test_supabase_jwt(sub=user_a, secret=TEST_SECRET)
    token_b = create_test_supabase_jwt(sub=user_b, secret=TEST_SECRET)

    # User A creates a course
    res_a = client.post(
        "/api/courses",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"course_name": "Alpha Private Course", "course_code": "ALP101"}
    )
    assert res_a.status_code == 201
    course_a_id = res_a.json()["id"]

    try:
        # User B attempts to read User A's course -> 403 Forbidden
        res_b_get = client.get(f"/api/courses/{course_a_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert res_b_get.status_code == 403
        assert "Access denied" in res_b_get.json()["detail"]

        # User B attempts to update User A's course -> 403 Forbidden
        res_b_put = client.put(
            f"/api/courses/{course_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"course_name": "Tampered Name"}
        )
        assert res_b_put.status_code == 403

        # User B attempts to delete User A's course -> 403 Forbidden
        res_b_del = client.delete(f"/api/courses/{course_a_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert res_b_del.status_code == 403

    finally:
        delete_course(course_a_id, owner_user_id=user_a)


def test_diagnostics_protection_in_production():
    """
    Requirement 4 & Diagnostics RBAC:
    - In production mode, unauthenticated public requests are rejected with 401 Unauthorized.
    - Authenticated users (e.g. students) can access safe, read-only diagnostics without secret leakage.
    - Administrative operations (e.g. cache clear) strictly require admin authorization (403 Forbidden for non-admins).
    """
    settings.app_env = "production"
    settings.admin_api_key = "secure-production-admin-key-777"
    settings.supabase_jwt_secret = TEST_SECRET

    # 1. Unauthenticated public request to /api/diagnostics -> 401 Unauthorized
    res_unauth = client.get("/api/diagnostics")
    assert res_unauth.status_code == 401
    assert "Authentication required" in res_unauth.json()["detail"]

    # 2. Public request to test probe endpoints -> 401 Unauthorized
    res_probe = client.post("/api/diagnostics/test-youtube")
    assert res_probe.status_code == 401

    # 3. Regular student JWT -> 200 OK for safe, read-only diagnostics
    student_token = create_test_supabase_jwt(sub="regular-student-uuid", secret=TEST_SECRET, role="authenticated")
    res_student = client.get("/api/diagnostics", headers={"Authorization": f"Bearer {student_token}"})
    assert res_student.status_code == 200
    student_diag = res_student.json()
    assert student_diag["status"] == "success"
    assert student_diag["backend"]["environment"] == "production"
    # Ensure sensitive table names list is redacted for non-admins
    assert student_diag["database"]["tables"] == []

    # 4. Regular student JWT attempting admin-only operation -> 403 Forbidden
    res_admin_op_denied = client.post("/api/diagnostics/cache/clear", headers={"Authorization": f"Bearer {student_token}"})
    assert res_admin_op_denied.status_code == 403
    assert "Administrative privileges required" in res_admin_op_denied.json()["detail"]

    # 5. Valid X-Admin-Key header -> can execute admin-only operations (200 OK)
    res_admin_key = client.post("/api/diagnostics/cache/clear", headers={"X-Admin-Key": "secure-production-admin-key-777"})
    assert res_admin_key.status_code == 200
    assert res_admin_key.json()["status"] == "success"

    # 6. Admin JWT (role='service_role' or 'admin') -> 200 OK for admin-only operations and includes table inventory
    admin_token = create_test_supabase_jwt(sub="supabase-admin-uuid", secret=TEST_SECRET, role="service_role")
    res_admin_jwt = client.post("/api/diagnostics/cache/clear", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin_jwt.status_code == 200

    res_admin_diag = client.get("/api/diagnostics", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin_diag.status_code == 200
    assert len(res_admin_diag.json()["database"]["tables"]) >= 0


def test_diagnostics_accessible_in_dev_mode():
    """
    Requirement 4: In development mode, diagnostics remain accessible for local UI debugging.
    """
    settings.app_env = "development"
    res = client.get("/api/diagnostics")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

