#!/usr/bin/env python3
"""Create disposable local Supabase Auth users via the Admin API.

Must run only against a disposable local Supabase instance in CI.
Never use production credentials or production Auth endpoints.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


IDENTITIES = [
    ("a2000000-0000-4000-8000-000000000001", "jwt-admin@example.com", 1),
    ("a2000000-0000-4000-8000-000000000002", "jwt-road-manager@example.com", 2),
    ("a2000000-0000-4000-8000-000000000003", "jwt-road-readonly@example.com", 3),
    ("a2000000-0000-4000-8000-000000000004", "jwt-finance@example.com", 4),
    ("a2000000-0000-4000-8000-000000000005", "jwt-other-org@example.com", 5),
    ("a2000000-0000-4000-8000-000000000006", "jwt-onboarding-new@example.com", 6),
    ("a2000000-0000-4000-8000-000000000007", "jwt-onboarding-duplicate@example.com", 7),
]


def _safe_error(exc: HTTPError) -> str:
    try:
        detail = json.loads(exc.read().decode(errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        detail = {}
    code = detail.get("error_code") or detail.get("code") or "unknown"
    message = detail.get("msg") or detail.get("message") or "no message"
    return f"HTTP {exc.code}, {code}: {str(message)[:180]}"


def admin_headers(service_role_key: str) -> dict[str, str]:
    return {
        "apikey": service_role_key,
        "Authorization": "Bearer " + service_role_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def create_or_update_user(
    api_url: str, service_role_key: str, user_id: str, email: str, password: str
) -> None:
    """Create a disposable Auth user with a fixed UUID; update if already present."""
    base = api_url.rstrip("/") + "/auth/v1/admin/users"
    payload = {
        "id": user_id,
        "email": email,
        "password": password,
        "email_confirm": True,
        "app_metadata": {"provider": "email", "providers": ["email"]},
    }
    req = Request(
        base,
        data=json.dumps(payload).encode(),
        headers=admin_headers(service_role_key),
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as response:
            response.read()
        print(f"CREATED disposable Auth user {email}")
        return
    except HTTPError as exc:
        # User may already exist from a prior step in the same disposable DB.
        if exc.code not in (422, 400, 409):
            raise RuntimeError(
                f"Local Supabase Auth could not create disposable user {email} "
                f"({_safe_error(exc)})."
            ) from None
        # Consume body from the failed create before issuing the update request.
        _ = _safe_error(exc)

    update = Request(
        base.rstrip("/") + "/" + user_id,
        data=json.dumps({"password": password, "email_confirm": True, "email": email}).encode(),
        headers=admin_headers(service_role_key),
        method="PUT",
    )
    try:
        with urlopen(update, timeout=20) as response:
            response.read()
        print(f"UPDATED disposable Auth user {email}")
    except HTTPError as exc:
        raise RuntimeError(
            f"Local Supabase Auth could not update disposable user {email} "
            f"({_safe_error(exc)})."
        ) from None


def main() -> None:
    api_url = os.environ["API_URL"]
    service_role_key = os.environ["SERVICE_ROLE_KEY"]
    if "firzbqzbezuecvplsibi" in api_url:
        raise RuntimeError("Refusing to provision Auth users against the production project.")

    for user_id, email, index in IDENTITIES:
        password = f"Local-CI-only-Road-Role-{index}-92!"
        create_or_update_user(api_url, service_role_key, user_id, email, password)
    print("Disposable Auth users are ready for public fixtures and JWT smoke tests.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - surface clean CI failure
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
