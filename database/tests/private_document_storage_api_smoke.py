#!/usr/bin/env python3
"""Exercise actual Supabase Storage REST authorization against disposable local Supabase.

Uses Auth-issued JWTs for synthetic users. Never run against production.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ORG_A = "b2000000-0000-4000-8000-000000000001"
ROAD_DOC_PATH = f"{ORG_A}/road_asset/e2000000-0000-4000-8000-000000000001/manager-upload.pdf"
READONLY_DOC_PATH = f"{ORG_A}/road_asset/e2000000-0000-4000-8000-000000000004/readonly-denied.txt"
CROSS_DEPT_DOC_PATH = f"{ORG_A}/road_asset/e2000000-0000-4000-8000-000000000005/finance-denied.txt"
ADMIN_DOC_PATH = f"{ORG_A}/finance/e2000000-0000-4000-8000-000000000006/admin-authorized.txt"
PAYLOAD = b"synthetic private document storage authorization test\n"


def access_token(api_url: str, anon_key: str, email: str, password: str) -> str:
    request = Request(
        api_url.rstrip("/") + "/auth/v1/token?grant_type=password",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode())
    except HTTPError as exc:
        raise RuntimeError(
            f"Local Auth failed for synthetic test user {email} (HTTP {exc.code})."
        ) from None
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError(f"Local Auth returned no access token for {email}.")
    return token


class StorageApi:
    def __init__(self, api_url: str, anon_key: str, tokens: dict[str, str]):
        self.base = api_url.rstrip("/") + "/storage/v1"
        self.anon_key = anon_key
        self.tokens = tokens

    def request(self, user: str | None, method: str, path: str, payload: bytes | None = None):
        headers = {
            "apikey": self.anon_key,
            "Authorization": "Bearer " + (self.tokens[user] if user else self.anon_key),
            "Accept": "application/json",
        }
        if payload is not None:
            headers["Content-Type"] = "text/plain"
            headers["x-upsert"] = "false"
        request = Request(self.base + path, data=payload, headers=headers, method=method)
        try:
            with urlopen(request, timeout=20) as response:
                return response.status, response.read()
        except HTTPError as exc:
            return exc.code, exc.read()


def require(condition: bool, message: str, status: int | None = None) -> None:
    if not condition:
        suffix = f" (HTTP {status})" if status is not None else ""
        raise AssertionError("FAIL " + message + suffix)
    suffix = f" (HTTP {status})" if status is not None else ""
    print("PASS " + message + suffix)


def object_path(path: str) -> str:
    return "/object/documents-private/" + quote(path, safe="/")


def download_path(path: str) -> str:
    return "/object/authenticated/documents-private/" + quote(path, safe="/")


def main() -> None:
    api_url = os.environ["API_URL"]
    anon_key = os.environ["ANON_KEY"]
    if "firzbqzbezuecvplsibi" in api_url:
        raise RuntimeError("Refusing to run Storage API tests against the production project.")

    identities = {
        "admin": ("jwt-admin@example.com", "Local-CI-only-Road-Role-1-92!"),
        "manager": ("jwt-road-manager@example.com", "Local-CI-only-Road-Role-2-92!"),
        "read_only": ("jwt-road-readonly@example.com", "Local-CI-only-Road-Role-3-92!"),
        "finance": ("jwt-finance@example.com", "Local-CI-only-Road-Role-4-92!"),
        "other_org": ("jwt-other-org@example.com", "Local-CI-only-Road-Role-5-92!"),
    }
    tokens = {
        key: access_token(api_url, anon_key, email, password)
        for key, (email, password) in identities.items()
    }
    api = StorageApi(api_url, anon_key, tokens)

    status, _ = api.request("manager", "POST", object_path(ROAD_DOC_PATH), PAYLOAD)
    require(status in (200, 201), "road department manager can upload an authorized original", status)

    status, body = api.request("manager", "GET", download_path(ROAD_DOC_PATH))
    require(status == 200 and body == PAYLOAD, "road department manager can download its original", status)

    status, body = api.request("read_only", "GET", download_path(ROAD_DOC_PATH))
    require(status == 200 and body == PAYLOAD, "read-only road user can download an authorized original", status)

    status, _ = api.request("read_only", "POST", object_path(READONLY_DOC_PATH), PAYLOAD)
    require(status in (400, 401, 403), "read-only road user cannot upload an original", status)

    status, _ = api.request("finance", "POST", object_path(CROSS_DEPT_DOC_PATH), PAYLOAD)
    require(status in (400, 401, 403), "finance manager cannot upload into road-asset storage", status)

    status, _ = api.request("other_org", "GET", download_path(ROAD_DOC_PATH))
    require(status in (400, 401, 403, 404), "user from another organization cannot download the road original", status)

    status, _ = api.request(None, "GET", download_path(ROAD_DOC_PATH))
    require(status in (400, 401, 403, 404), "anonymous client cannot download a private original", status)

    status, _ = api.request("admin", "POST", object_path(ADMIN_DOC_PATH), PAYLOAD)
    require(status in (200, 201), "organization admin can upload within their organization", status)

    status, body = api.request("admin", "GET", download_path(ADMIN_DOC_PATH))
    require(status == 200 and body == PAYLOAD, "organization admin can download the authorized original", status)


if __name__ == "__main__":
    main()
