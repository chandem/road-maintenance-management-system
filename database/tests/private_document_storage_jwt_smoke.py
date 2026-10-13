#!/usr/bin/env python3
"""Exercise real Supabase Storage HTTP authorization using disposable local Auth JWTs.

This must run only against the disposable local Supabase instance created by CI.
It does not call production or use a service-role key for Storage requests.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ORG_A_ROAD_PATH = (
    "b2000000-0000-4000-8000-000000000001/road_asset/"
    "e2000000-0000-4000-8000-000000000001/road-original.pdf"
)
ORG_A_FINANCE_PATH = (
    "b2000000-0000-4000-8000-000000000001/finance/"
    "e2000000-0000-4000-8000-000000000002/finance-original.pdf"
)
ORG_B_ROAD_PATH = (
    "b2000000-0000-4000-8000-000000000002/road_asset/"
    "e2000000-0000-4000-8000-000000000003/other-org-original.pdf"
)
ORG_A_OFFICER_PATH = (
    "b2000000-0000-4000-8000-000000000001/road_asset/"
    "e2000000-0000-4000-8000-000000000004/officer-original.pdf"
)


def auth_token(api_url: str, anon_key: str, email: str, password: str) -> str:
    request = Request(
        api_url.rstrip("/") + "/auth/v1/token?grant_type=password",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode())
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError(f"Local Auth did not issue a token for {email}")
    return token


def request_storage(api_url: str, anon_key: str, token: str | None, method: str, path: str,
                    content: bytes | None = None) -> tuple[int, bytes]:
    endpoint = api_url.rstrip("/") + "/storage/v1"
    headers = {"apikey": anon_key, "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    else:
        headers["Authorization"] = "Bearer " + anon_key
    if content is not None:
        headers["Content-Type"] = "application/pdf"
        headers["x-upsert"] = "false"
    request = Request(endpoint + path, data=content, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def expect(condition: bool, message: str, status: int) -> None:
    if not condition:
        raise AssertionError(f"FAIL {message} (HTTP {status})")
    print(f"PASS {message} (HTTP {status})")


def main() -> None:
    api_url = os.environ["API_URL"]
    anon_key = os.environ["ANON_KEY"]
    if "firzbqzbezuecvplsibi" in api_url:
        raise RuntimeError("Refusing to run private-storage JWT tests against production.")

    # These credentials are created exclusively by the local CI Auth setup step.
    manager = auth_token(api_url, anon_key, "jwt-road-manager@example.com", "Local-CI-only-Road-Role-2-92!")
    read_only = auth_token(api_url, anon_key, "jwt-road-readonly@example.com", "Local-CI-only-Road-Role-3-92!")
    finance = auth_token(api_url, anon_key, "jwt-finance@example.com", "Local-CI-only-Road-Role-4-92!")
    other_org = auth_token(api_url, anon_key, "jwt-other-org@example.com", "Local-CI-only-Road-Role-5-92!")
    officer = auth_token(api_url, anon_key, "jwt-onboarding-new@example.com", "Local-CI-only-Road-Role-6-92!")

    object_route = lambda path: "/object/documents-private/" + path
    download_route = lambda path: "/object/authenticated/documents-private/" + path
    test_bytes = b"%PDF-1.4\n% disposable private storage authorization test\n"

    # Try unauthorized write before the authorized upload so duplicate-object
    # handling cannot be mistaken for an RLS denial.
    status, _ = request_storage(api_url, anon_key, read_only, "POST", object_route(ORG_A_ROAD_PATH), test_bytes)
    expect(status in (400, 401, 403), "read-only user cannot upload a private original", status)

    status, _ = request_storage(api_url, anon_key, finance, "POST", object_route(ORG_A_ROAD_PATH), test_bytes)
    expect(status in (400, 401, 403), "finance-only user cannot upload into road-asset department", status)

    status, _ = request_storage(api_url, anon_key, other_org, "POST", object_route(ORG_A_ROAD_PATH), test_bytes)
    expect(status in (400, 401, 403), "other-organization user cannot upload into organization A", status)

    status, _ = request_storage(api_url, anon_key, officer, "POST", object_route(ORG_A_OFFICER_PATH), test_bytes)
    expect(status in (200, 201), "road department officer can upload authorized private original", status)

    status, _ = request_storage(api_url, anon_key, manager, "POST", object_route(ORG_A_ROAD_PATH), test_bytes)
    expect(status in (200, 201), "road manager can upload authorized private original", status)

    status, body = request_storage(api_url, anon_key, read_only, "GET", download_route(ORG_A_ROAD_PATH))
    expect(status == 200 and b"disposable private storage authorization test" in body,
           "read-only user can download authorized road original", status)

    status, _ = request_storage(api_url, anon_key, finance, "GET", download_route(ORG_A_ROAD_PATH))
    expect(status in (400, 401, 403, 404), "finance-only user cannot download road original", status)

    status, _ = request_storage(api_url, anon_key, other_org, "GET", download_route(ORG_A_ROAD_PATH))
    expect(status in (400, 401, 403, 404), "other-organization user cannot download organization A original", status)

    status, _ = request_storage(api_url, anon_key, manager, "GET", download_route(ORG_A_FINANCE_PATH))
    expect(status in (400, 401, 403, 404), "road manager cannot download finance original", status)

    status, _ = request_storage(api_url, anon_key, None, "GET", download_route(ORG_A_ROAD_PATH))
    expect(status in (400, 401, 403, 404), "anonymous client cannot download private original", status)

    # No UPDATE policy is expected. Attempting to replace object bytes must fail.
    status, _ = request_storage(api_url, anon_key, manager, "PUT", object_route(ORG_A_ROAD_PATH), test_bytes)
    expect(status in (400, 401, 403, 404), "road manager cannot update/overwrite an existing private object", status)

    # Keep the cross-organization path unused; matching the path's segments
    # without a real object/document authorization must not grant access.
    status, _ = request_storage(api_url, anon_key, manager, "GET", download_route(ORG_B_ROAD_PATH))
    expect(status in (400, 401, 403, 404), "organization A manager cannot download organization B original", status)


if __name__ == "__main__":
    main()
