"""AI analysis audit logging.

Persists runs to the ai_analysis_runs table so every AI-assisted decision
can be reviewed later with its inputs, evidence, and outcome.
"""

from __future__ import annotations

from typing import Any


def log_analysis_run(
    client: Any,
    *,
    organization_id: str,
    analysis_type: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    input_reference: str | None = None,
    status: str = "completed",
    confidence: float | None = None,
    result: dict | list | None = None,
    evidence: dict | list | None = None,
    error_message: str | None = None,
    created_by: str | None = None,
) -> str | None:
    """Insert one ai_analysis_runs row. Returns the new id, or None on failure."""
    try:
        payload: dict[str, Any] = {
            "organization_id": organization_id,
            "analysis_type": analysis_type,
            "status": status,
        }
        if entity_type:
            payload["entity_type"] = entity_type
        if entity_id:
            payload["entity_id"] = entity_id
        if input_reference:
            payload["input_reference"] = input_reference
        if confidence is not None:
            payload["confidence"] = confidence
        if result is not None:
            payload["result"] = result
        if evidence is not None:
            payload["evidence"] = evidence
        if error_message:
            payload["error_message"] = error_message
        if created_by:
            payload["created_by"] = created_by

        response = client.table("ai_analysis_runs").insert(payload).execute()
        if response.data:
            return str(response.data[0].get("id"))
    except Exception:
        # Audit logging must never break the main request path.
        pass
    return None


def resolve_organization_id(client: Any, user_id: str) -> str | None:
    """Return the profile organization only when backed by active membership.

    user_profiles.organization_id is user-editable under the current profile
    policy, so it is a selector, not an authorization source. The active
    organization_members row is authoritative.
    """
    try:
        profile = (
            client.table("user_profiles")
            .select("organization_id")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        organization_id = (profile.data or {}).get("organization_id")
        if not organization_id:
            return None

        membership = (
            client.table("organization_members")
            .select("organization_id")
            .eq("organization_id", organization_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )
        if not membership.data:
            return None
        return str(membership.data["organization_id"])
    except Exception:
        return None
