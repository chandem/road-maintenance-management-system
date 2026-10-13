#!/usr/bin/env python3
"""Local-Auth-issued JWT/PostgREST smoke tests against disposable Supabase only.

Auth users are provisioned earlier via the local Supabase Auth Admin API.
This script obtains genuine access tokens through the password grant, then
exercises the real HTTP Data API. Never use production credentials here.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ORG_A_ROAD = "d2000000-0000-4000-8000-000000000001"
ORG_B_ROAD = "d2000000-0000-4000-8000-000000000002"
ORG_A_ID = "b2000000-0000-4000-8000-000000000001"


def local_auth_access_token(api_url: str, anon_key: str, email: str, password: str) -> str:
    # Disposable users were created via the local Auth Admin API.
    # This request obtains a real access token from local Supabase Auth.
    data = json.dumps({"email": email, "password": password}).encode()
    req = Request(
        api_url.rstrip("/") + "/auth/v1/token?grant_type=password",
        data=data,
        headers={"apikey": anon_key, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode())
    except HTTPError as exc:
        # Surface only the Auth error code/message for debugging; never log passwords or tokens.
        try:
            detail = json.loads(exc.read().decode(errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            detail = {}
        safe_code = detail.get("error_code") or detail.get("code") or "unknown"
        safe_message = detail.get("msg") or detail.get("message") or detail.get("error_description") or "no message"
        raise RuntimeError(
            f"Local Supabase Auth did not issue an access token for disposable user {email} "
            f"(HTTP {exc.code}, {safe_code}: {str(safe_message)[:180]})."
        ) from None
    token = result.get("access_token") if isinstance(result, dict) else None
    if not isinstance(token, str) or not token:
        raise RuntimeError(
            f"Local Supabase Auth response lacked an access token for disposable user {email}."
        )
    return token


class Api:
    def __init__(self, base: str, anon_key: str, tokens: dict[str, str]):
        self.base = base.rstrip("/")
        self.anon_key = anon_key
        self.tokens = tokens

    def anonymous_request(self, method: str, path: str, body=None):
        data = None if body is None else json.dumps(body).encode()
        headers = {
            "apikey": self.anon_key,
            "Authorization": "Bearer " + self.anon_key,
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

    def request(self, user_id: str, method: str, path: str, body=None):
        token = self.tokens.get(user_id)
        if not token:
            raise RuntimeError(f"No local Auth-issued token configured for test identity {user_id}")
        data = None if body is None else json.dumps(body).encode()
        headers = {
            "apikey": self.anon_key,
            "Authorization": "Bearer " + token,
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
    if "firzbqzbezuecvplsibi" in api_url:
        raise RuntimeError("Refusing to run JWT smoke tests against the production project.")

    admin = "a2000000-0000-4000-8000-000000000001"
    manager = "a2000000-0000-4000-8000-000000000002"
    read_only = "a2000000-0000-4000-8000-000000000003"
    finance = "a2000000-0000-4000-8000-000000000004"
    other_org = "a2000000-0000-4000-8000-000000000005"

    identities = {
        admin: "jwt-admin@example.com",
        manager: "jwt-road-manager@example.com",
        read_only: "jwt-road-readonly@example.com",
        finance: "jwt-finance@example.com",
        other_org: "jwt-other-org@example.com",
    }
    tokens = {}
    for index, (user_id, email) in enumerate(identities.items(), start=1):
        # Fixed disposable-only credentials; never print them or any access token.
        password = f"Local-CI-only-Road-Role-{index}-92!"
        tokens[user_id] = local_auth_access_token(api_url, anon_key, email, password)
    api = Api(api_url, anon_key, tokens)

    def roads(user_id: str):
        query = urlencode({"select": "id,road_code", "organization_id": f"eq.{ORG_A_ID}"})
        return api.request(user_id, "GET", "/rest/v1/roads?" + query)

    status, rows = roads(admin)
    require(status == 200 and isinstance(rows, list) and any(r.get("id") == ORG_A_ROAD for r in rows),
            "Auth-issued org-admin JWT reads its organization's road")

    status, rows = roads(manager)
    require(status == 200 and isinstance(rows, list) and any(r.get("id") == ORG_A_ROAD for r in rows),
            "Auth-issued road-manager JWT reads assigned road")

    status, rows = roads(read_only)
    require(status == 200 and isinstance(rows, list) and any(r.get("id") == ORG_A_ROAD for r in rows),
            "Auth-issued read-only JWT reads assigned road")

    status, rows = roads(finance)
    require(status == 200 and rows == [], "Auth-issued finance-only JWT cannot see road-asset data")

    status, rows = roads(other_org)
    require(status == 200 and rows == [], "Auth-issued other-organization JWT cannot see organization A roads")

    insert_path = "/rest/v1/roads"
    status, result = api.request(manager, "POST", insert_path, {
        "organization_id": ORG_A_ID,
        "road_code": "JWT-MANAGER-CREATE",
        "name": "Created through Auth-issued JWT",
    })
    require(status in (200, 201) and isinstance(result, list) and len(result) == 1,
            f"Auth-issued road-manager JWT can create a road (HTTP {status})")

    status, result = api.request(read_only, "POST", insert_path, {
        "organization_id": ORG_A_ID,
        "road_code": "JWT-READONLY-MUST-FAIL",
        "name": "Must not be created",
    })
    require(status in (401, 403) or (status in (200, 201) and result == []),
            f"Auth-issued read-only JWT cannot create a road (HTTP {status})")

    status, rows = api.request(manager, "GET", "/rest/v1/roads?" + urlencode({
        "select": "id", "id": f"eq.{ORG_B_ROAD}"
    }))
    require(status == 200 and rows == [], "Auth-issued road-manager JWT cannot read another organization's road")

    def document_rows(user_id: str):
        query = urlencode({"select": "id,title,department_code", "organization_id": f"eq.{ORG_A_ID}"})
        return api.request(user_id, "GET", "/rest/v1/documents?" + query)

    status, rows = document_rows(manager)
    require(status == 200 and any(r.get("id") == "e2000000-0000-4000-8000-000000000001" for r in rows)
            and all(r.get("id") != "e2000000-0000-4000-8000-000000000002" for r in rows),
            "Auth-issued road-manager JWT reads road documents but not finance documents")

    status, rows = document_rows(finance)
    require(status == 200 and any(r.get("id") == "e2000000-0000-4000-8000-000000000002" for r in rows)
            and all(r.get("id") != "e2000000-0000-4000-8000-000000000001" for r in rows),
            "Auth-issued finance-manager JWT reads finance documents but not road documents")

    status, rows = api.request(manager, "GET", "/rest/v1/document_chunks?" + urlencode({
        "select": "id,document_id,content", "organization_id": f"eq.{ORG_A_ID}"
    }))
    require(status == 200 and any(r.get("id") == "f2000000-0000-4000-8000-000000000001" for r in rows)
            and all(r.get("id") != "f2000000-0000-4000-8000-000000000002" for r in rows),
            "Auth-issued road-manager JWT retrieves road chunks only")

    status, result = api.request(manager, "PATCH", "/rest/v1/documents?id=eq.e2000000-0000-4000-8000-000000000001",
                                {"department_code": "finance"})
    require(status in (401, 403) or (status == 200 and result == []),
            f"road manager cannot reclassify a road document into finance (HTTP {status})")

    status, result = api.request(manager, "PATCH", "/rest/v1/document_chunks?id=eq.f2000000-0000-4000-8000-000000000001",
                                {"document_id": "e2000000-0000-4000-8000-000000000002"})
    require(status in (401, 403) or (status == 200 and result == []),
            f"road manager cannot re-parent a road chunk to a finance document (HTTP {status})")

    conversation_payload = {
        "organization_id": ORG_A_ID,
        "created_by": manager,
        "title": "Signed JWT test conversation",
    }
    status, result = api.request(manager, "POST", "/rest/v1/ai_conversations", conversation_payload)
    require(status in (200, 201) and isinstance(result, list) and len(result) == 1,
            f"Auth-issued road-manager JWT creates own AI conversation (HTTP {status})")
    manager_conversation_id = result[0]["id"] if status in (200, 201) and result else None
    require(bool(manager_conversation_id), "new conversation returns an identifier for message authorization tests")

    status, rows = api.request(read_only, "GET", "/rest/v1/ai_conversations?" + urlencode({
        "select": "id,created_by", "id": "eq.72000000-0000-4000-8000-000000000001"
    }))
    require(status == 200 and isinstance(rows, list) and len(rows) == 1,
            "read-only user can read their own conversation")

    status, rows = api.request(manager, "GET", "/rest/v1/ai_conversations?" + urlencode({
        "select": "id", "id": "eq.72000000-0000-4000-8000-000000000001"
    }))
    require(status == 200 and rows == [], "road manager cannot read another user's conversation")

    status, rows = api.request(manager, "GET", "/rest/v1/ai_messages?" + urlencode({
        "select": "id,conversation_id", "conversation_id": "eq.72000000-0000-4000-8000-000000000001"
    }))
    require(status == 200 and rows == [], "road manager cannot read messages from another user's conversation")

    status, result = api.request(manager, "POST", "/rest/v1/ai_messages", {
        "conversation_id": manager_conversation_id,
        "role": "user",
        "content": "Authorized user message",
    })
    require(status in (200, 201) and isinstance(result, list) and len(result) == 1,
            f"road manager can post a user message to own active conversation (HTTP {status})")

    for forged_role in ("assistant", "system"):
        status, result = api.request(manager, "POST", "/rest/v1/ai_messages", {
            "conversation_id": manager_conversation_id,
            "role": forged_role,
            "content": "Forged role must be denied",
        })
        require(status in (401, 403) or (status in (200, 201) and result == []),
                f"road manager cannot forge a {forged_role} message (HTTP {status})")

    status, result = api.request(manager, "POST", "/rest/v1/ai_messages", {
        "conversation_id": "72000000-0000-4000-8000-000000000001",
        "role": "user",
        "content": "Must not post into another user's conversation",
    })
    require(status in (401, 403) or (status in (200, 201) and result == []),
            "road manager cannot post to another user's conversation")

    status, result = api.request(read_only, "POST", "/rest/v1/ai_messages", {
        "conversation_id": "72000000-0000-4000-8000-000000000001",
        "role": "user",
        "content": "Read-only user must not post",
    })
    require(status in (401, 403) or (status in (200, 201) and result == []),
            "read-only user cannot post messages")

    status, result = api.request(manager, "POST", "/rest/v1/ai_messages", {
        "conversation_id": "72000000-0000-4000-8000-000000000002",
        "role": "user",
        "content": "Archived conversation must reject writes",
    })
    require(status in (401, 403) or (status in (200, 201) and result == []),
            "manager cannot post into an archived conversation")

    status, result = api.request(read_only, "POST", "/rest/v1/ai_conversations", {
        "organization_id": ORG_A_ID,
        "created_by": read_only,
        "title": "Read-only must not create",
    })
    require(status in (401, 403) or (status in (200, 201) and result == []),
            "Auth-issued read-only JWT cannot create AI conversations")

    status, rows = api.request(finance, "GET", "/rest/v1/ai_conversations?" + urlencode({
        "select": "id", "organization_id": f"eq.{ORG_A_ID}"
    }))
    require(status == 200 and rows == [], "finance-only user cannot read road AI conversations")


    # Profile and department-role privilege regression coverage.
    profile_path = "/rest/v1/user_profiles"
    profile_query = profile_path + "?" + urlencode({"select": "id,full_name,organization_id,department_id,employee_code,is_active", "id": f"eq.{manager}"})
    status, profile_rows = api.request(manager, "GET", profile_query)
    require(status == 200 and isinstance(profile_rows, list),
            "authenticated user can query their own profile through the Data API")
    if not profile_rows:
        status, result = api.request(manager, "POST", profile_path, {"id": manager, "full_name": "JWT Road Manager"})
        require(status in (200, 201) and isinstance(result, list) and len(result) == 1,
                f"user can bootstrap a minimal own profile (HTTP {status})")
    else:
        status, result = api.request(manager, "PATCH", profile_path + "?id=eq." + manager,
                                     {"full_name": "JWT Road Manager Updated"})
        require(status in (200, 204) and (status == 204 or isinstance(result, list)),
                f"user can update own profile name (HTTP {status})")

    status, result = api.request(manager, "PATCH", profile_path + "?id=eq." + manager,
                                 {"organization_id": "b2000000-0000-4000-8000-000000000002"})
    require(status in (401, 403) or (status in (200, 204) and result == []),
            f"user cannot change their own organization assignment (HTTP {status}; response={result!r})")

    status, result = api.request(manager, "PATCH", profile_path + "?id=eq." + manager,
                                 {"is_active": False})
    require(status in (401, 403) or (status in (200, 204) and result == []),
            f"user cannot deactivate their own account profile (HTTP {status}; response={result!r})")

    role_path = "/rest/v1/user_department_roles"
    status, result = api.anonymous_request("GET", role_path + "?" + urlencode({"select": "id", "limit": "1"}))
    require(status in (401, 403), f"anonymous client cannot read department-role assignments (HTTP {status})")

    status, result = api.anonymous_request("POST", role_path, {
        "organization_id": ORG_A_ID,
        "user_id": manager,
        "department_id": "c2000000-0000-4000-8000-000000000002",
        "role": "department_manager",
        "is_active": True,
    })
    require(status in (401, 403), f"anonymous client cannot create department-role assignments (HTTP {status})")

    # Organization admins should retain their intended ability to assign roles,
    # while ordinary department managers must not grant themselves privileges.
    status, result = api.request(admin, "POST", role_path, {
        "organization_id": ORG_A_ID,
        "user_id": read_only,
        "department_id": "c2000000-0000-4000-8000-000000000002",
        "role": "read_only",
        "is_active": True,
    })
    require(status in (200, 201) and isinstance(result, list) and len(result) == 1,
            f"organization admin can assign a department role (HTTP {status})")

    status, result = api.request(manager, "POST", role_path, {
        "organization_id": ORG_A_ID,
        "user_id": manager,
        "department_id": "c2000000-0000-4000-8000-000000000002",
        "role": "department_manager",
        "is_active": True,
    })
    require(status in (401, 403) or (status in (200, 201) and result == []),
            f"department manager cannot assign themselves another department role (HTTP {status})")


if __name__ == "__main__":
    main()
