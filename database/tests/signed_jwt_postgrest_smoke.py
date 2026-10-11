#!/usr/bin/env python3
"""Signed-JWT/PostgREST smoke tests against disposable local Supabase only.

Uses the local development JWT secret to sign short-lived authenticated JWTs,
then exercises the real HTTP Data API. Fixtures are synthetic and must be seeded
by signed_jwt_api_fixtures.sql immediately before this script.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ORG_A_ROAD = "d2000000-0000-4000-8000-000000000001"
ORG_B_ROAD = "d2000000-0000-4000-8000-000000000002"
ORG_A_ID = "b2000000-0000-4000-8000-000000000001"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def jwt_for(user_id: str, secret: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "aud": "authenticated",
        "exp": now + 300,
        "iat": now,
        "iss": "supabase",
        "sub": user_id,
        "role": "authenticated",
        "email": f"{user_id}@example.invalid",
        "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {},
    }
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + b64url(json.dumps(payload, separators=(",", ":")).encode())
    )
    signature = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return signing_input + "." + b64url(signature)


class Api:
    def __init__(self, base: str, anon_key: str, secret: str):
        self.base = base.rstrip("/")
        self.anon_key = anon_key
        self.secret = secret

    def request(self, user_id: str, method: str, path: str, body=None):
        data = None if body is None else json.dumps(body).encode()
        headers = {
            "apikey": self.anon_key,
            "Authorization": "Bearer " + jwt_for(user_id, self.secret),
            "Accept": "application/json",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
            headers["Prefer"] = "return=representation"
        req = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=15) as response:
                raw = response.read().decode()
                return response.status, json.loads(raw) if raw else None
        except HTTPError as exc:
            raw = exc.read().decode(errors="replace")
            try:
                parsed = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw[:200]
            return exc.code, parsed


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("PASS " + message)


def main() -> None:
    api_url = os.environ["API_URL"]
    anon_key = os.environ["ANON_KEY"]
    jwt_secret = os.environ["JWT_SECRET"]
    api = Api(api_url, anon_key, jwt_secret)

    admin = "a2000000-0000-4000-8000-000000000001"
    manager = "a2000000-0000-4000-8000-000000000002"
    read_only = "a2000000-0000-4000-8000-000000000003"
    finance = "a2000000-0000-4000-8000-000000000004"
    other_org = "a2000000-0000-4000-8000-000000000005"

    def roads(user_id: str):
        query = urlencode({"select": "id,road_code", "organization_id": f"eq.{ORG_A_ID}"})
        return api.request(user_id, "GET", "/rest/v1/roads?" + query)

    status, rows = roads(admin)
    require(status == 200 and isinstance(rows, list) and any(r.get("id") == ORG_A_ROAD for r in rows),
            "signed org-admin JWT reads its organization's road")

    status, rows = roads(manager)
    require(status == 200 and isinstance(rows, list) and any(r.get("id") == ORG_A_ROAD for r in rows),
            "signed road-manager JWT reads assigned road")

    status, rows = roads(read_only)
    require(status == 200 and isinstance(rows, list) and any(r.get("id") == ORG_A_ROAD for r in rows),
            "signed read-only JWT reads assigned road")

    status, rows = roads(finance)
    require(status == 200 and rows == [], "signed finance-only JWT cannot see road-asset data")

    status, rows = roads(other_org)
    require(status == 200 and rows == [], "signed other-organization JWT cannot see organization A roads")

    insert_path = "/rest/v1/roads"
    status, result = api.request(manager, "POST", insert_path, {
        "organization_id": ORG_A_ID,
        "road_code": "JWT-MANAGER-CREATE",
        "name": "Created through signed JWT",
    })
    require(status in (200, 201) and isinstance(result, list) and len(result) == 1,
            f"signed road-manager JWT can create a road (HTTP {status})")

    status, result = api.request(read_only, "POST", insert_path, {
        "organization_id": ORG_A_ID,
        "road_code": "JWT-READONLY-MUST-FAIL",
        "name": "Must not be created",
    })
    require(status in (401, 403) or (status in (200, 201) and result == []),
            f"signed read-only JWT cannot create a road (HTTP {status})")

    # Ensure a caller cannot force an org-A road into org-B by filtering the
    # result; the row from B must never be returned to an org-A identity.
    status, rows = api.request(manager, "GET", "/rest/v1/roads?" + urlencode({
        "select": "id", "id": f"eq.{ORG_B_ROAD}"
    }))
    require(status == 200 and rows == [], "signed road-manager JWT cannot read another organization's road")


if __name__ == "__main__":
    main()
