#!/usr/bin/env python3
"""Organization onboarding RPC regression tests for disposable local Supabase only.

Uses genuine Auth-issued JWTs and service-role reads only to verify that failed
calls leave no partial organization/membership rows. Never run against production.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ORG_A_ID = "b2000000-0000-4000-8000-000000000001"
ORG_ADMIN_ID = "a2000000-0000-4000-8000-000000000001"
NEW_USER_ID = "a2000000-0000-4000-8000-000000000006"
DUPLICATE_USER_ID = "a2000000-0000-4000-8000-000000000007"


def call(base: str, headers: dict[str, str], method: str, path: str, body=None):
    data = None if body is None else json.dumps(body).encode()
    request_headers = {**headers, "Accept": "application/json"}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
        request_headers["Prefer"] = "return=representation"
    req = Request(base.rstrip("/") + path, data=data, headers=request_headers, method=method)
    try:
        with urlopen(req, timeout=20) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = raw[:200]
        return exc.code, payload


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("PASS " + message)


def auth_token(api_url: str, anon_key: str, email: str, password: str) -> str:
    status, payload = call(
        api_url,
        {"apikey": anon_key},
        "POST",
        "/auth/v1/token?grant_type=password",
        {"email": email, "password": password},
    )
    if status != 200 or not isinstance(payload, dict) or not payload.get("access_token"):
        raise AssertionError(f"Local Auth did not issue a token for disposable identity {email} (HTTP {status})")
    return payload["access_token"]


def main() -> None:
    api_url = os.environ["API_URL"]
    anon_key = os.environ["ANON_KEY"]
    service_key = os.environ["SERVICE_ROLE_KEY"]
    if "firzbqzbezuecvplsibi" in api_url:
        raise RuntimeError("Refusing to run onboarding regression tests against production.")

    identities = [
        (ORG_ADMIN_ID, "jwt-admin@example.com", 1),
        (NEW_USER_ID, "jwt-onboarding-new@example.com", 6),
        (DUPLICATE_USER_ID, "jwt-onboarding-duplicate@example.com", 7),
    ]
    tokens = {
        user_id: auth_token(api_url, anon_key, email, f"Local-CI-only-Road-Role-{index}-92!")
        for user_id, email, index in identities
    }

    def user_headers(user_id: str) -> dict[str, str]:
        return {"apikey": anon_key, "Authorization": "Bearer " + tokens[user_id]}

    service_headers = {"apikey": service_key, "Authorization": "Bearer " + service_key}

    # An unauthenticated/anon caller must never be allowed to create an organization.
    status, _ = call(
        api_url, {"apikey": anon_key, "Authorization": "Bearer " + anon_key},
        "POST", "/rest/v1/rpc/create_organization_for_current_user",
        {"p_name": "Anonymous Must Not Create", "p_code": "ANON-MUST-FAIL"},
    )
    require(status in (401, 403), f"anonymous caller cannot execute organization onboarding RPC (HTTP {status})")

    # First-time authenticated user creates their organization.
    status, created = call(
        api_url, user_headers(NEW_USER_ID), "POST",
        "/rest/v1/rpc/create_organization_for_current_user",
        {"p_name": "JWT Onboarding Created Organization", "p_code": "JWT-ONBOARDING-NEW"},
    )
    require(status == 200 and isinstance(created, str) and bool(created),
            f"new authenticated user can create an organization (HTTP {status})")
    new_org_id = created

    status, profiles = call(
        api_url, user_headers(NEW_USER_ID), "GET",
        "/rest/v1/user_profiles?" + urlencode({
            "select": "id,organization_id,is_active", "id": "eq." + NEW_USER_ID
        }),
    )
    require(status == 200 and isinstance(profiles, list) and len(profiles) == 1
            and profiles[0].get("organization_id") == new_org_id
            and profiles[0].get("is_active") is True,
            "successful onboarding assigns the organization and activates the user's profile")

    status, memberships = call(
        api_url, user_headers(NEW_USER_ID), "GET",
        "/rest/v1/organization_members?" + urlencode({
            "select": "organization_id,user_id,role,is_active",
            "organization_id": "eq." + new_org_id,
            "user_id": "eq." + NEW_USER_ID,
        }),
    )
    require(status == 200 and isinstance(memberships, list) and len(memberships) == 1
            and memberships[0].get("is_active") is True
            and memberships[0].get("role") in ("owner", "admin"),
            "successful onboarding creates an active organization membership")

    # Existing organization member must not create a second organization.
    status, _ = call(
        api_url, user_headers(ORG_ADMIN_ID), "POST",
        "/rest/v1/rpc/create_organization_for_current_user",
        {"p_name": "Second Organization Must Fail", "p_code": "JWT-SECOND-ORG"},
    )
    require(status >= 400, f"user already assigned to an organization cannot create another (HTTP {status})")

    # Duplicate code must fail and leave no partial organization or membership rows.
    status, _ = call(
        api_url, user_headers(DUPLICATE_USER_ID), "POST",
        "/rest/v1/rpc/create_organization_for_current_user",
        {"p_name": "Duplicate Code Attempt", "p_code": "JWT-TEST-A"},
    )
    require(status >= 400, f"duplicate organization code is rejected (HTTP {status})")

    query = urlencode({"select": "id,name,code", "name": "eq.Duplicate Code Attempt"})
    status, rows = call(api_url, service_headers, "GET", "/rest/v1/organizations?" + query)
    require(status == 200 and rows == [], "failed duplicate-code onboarding leaves no organization row")

    query = urlencode({"select": "organization_id,user_id", "user_id": "eq." + DUPLICATE_USER_ID})
    status, rows = call(api_url, service_headers, "GET", "/rest/v1/organization_members?" + query)
    require(status == 200 and rows == [], "failed duplicate-code onboarding leaves no membership row")


if __name__ == "__main__":
    main()
