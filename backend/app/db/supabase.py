"""Supabase clients for the AI-RMMS backend.

Two client modes:

1. **User-scoped client** (`get_supabase_client(access_token)`)
   Uses the publishable key + the caller's JWT.
   RLS and `private.is_org_member()` apply. Use for all API requests.

2. **Service client** (`get_service_client()`)
   Uses the service-role key when configured.
   Bypasses RLS — only for controlled server jobs (migrations helpers,
   bulk embedding backfills). Prefer the user-scoped client whenever possible.
"""

from __future__ import annotations

from supabase import Client, create_client

from app.core.config import get_settings


def get_supabase_client(access_token: str | None = None) -> Client:
    """Create a Supabase client, optionally authenticated as the end user."""
    settings = get_settings()

    client = create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
    )
    
    if access_token:
        client.auth.set_session(access_token, access_token)
    
    return client


def get_service_client() -> Client:
    """Create a service-role client. Raises if the key is not configured."""
    settings = get_settings()
    if not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not configured. "
            "Set it only on the backend for privileged server jobs."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


def probe_supabase() -> dict[str, str | bool]:
    """Lightweight connectivity check against the configured project.

    Does not require a user token. Returns status fields suitable for health.
    """
    settings = get_settings()
    if not settings.has_supabase:
        return {
            "configured": False,
            "reachable": False,
            "detail": "SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY missing",
        }

    try:
        client = get_supabase_client()
        # Auth settings endpoint is a cheap authenticated-API surface probe.
        client.auth.get_session()
        return {
            "configured": True,
            "reachable": True,
            "region": settings.supabase_region,
            "project_ref": settings.supabase_project_ref or "not-set",
            "service_role_configured": settings.has_service_role,
            "detail": "ok",
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "region": settings.supabase_region,
            "project_ref": settings.supabase_project_ref or "not-set",
            "service_role_configured": settings.has_service_role,
            "detail": type(exc).__name__,
        }
