from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.supabase import get_supabase_client

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token = credentials.credentials
    supabase = get_supabase_client(token)

    try:
        response = supabase.auth.get_user(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token") from exc

    if response.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token")

    return {"id": response.user.id, "client": supabase, "access_token": token}


def require_department_access(department_code: str, allowed_roles: list[str]):
    """FastAPI dependency that requires an active department assignment.

    Uses the caller's JWT-scoped client and the database authorization helper.
    The database RLS policies remain a separate required protection layer.
    """
    from app.services.ai_audit import resolve_organization_id

    def _check(current_user=Depends(get_current_user)):
        try:
            organization_id = resolve_organization_id(
                current_user["client"], current_user["id"]
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Organization membership could not be verified.",
            ) from exc
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active organization membership is required.",
            )
        # Owner/admin privileges come from the authoritative active membership row.
        try:
            membership = (
                current_user["client"]
                .table("organization_members")
                .select("role")
                .eq("organization_id", organization_id)
                .eq("user_id", current_user["id"])
                .eq("is_active", True)
                .maybe_single()
                .execute()
            )
            is_org_admin = bool(
                membership.data
                and membership.data.get("role") in {"owner", "admin"}
            )
            result = current_user["client"].rpc(
                "has_department_role",
                {
                    "p_organization_id": organization_id,
                    "p_department_code": department_code,
                    "p_allowed_roles": allowed_roles,
                },
            ).execute()
        except Exception as exc:
            # Fail closed if the authorization lookup is unavailable.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Department authorization could not be verified.",
            ) from exc
        if not is_org_admin and result.data is not True:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required department permissions.",
            )
        return current_user

    return _check


def require_org_admin():
    """Require an active organization owner/admin for cross-department features.

    Use this until the endpoint can filter every piece of retrieved data by the
    caller's department grants. Fails closed on membership lookup errors.
    """
    from app.services.ai_audit import resolve_organization_id

    def _check(current_user=Depends(get_current_user)):
        try:
            organization_id = resolve_organization_id(
                current_user["client"], current_user["id"]
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Organization membership could not be verified.",
            ) from exc
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active organization membership is required.",
            )
        try:
            membership = (
                current_user["client"]
                .table("organization_members")
                .select("role")
                .eq("organization_id", organization_id)
                .eq("user_id", current_user["id"])
                .eq("is_active", True)
                .maybe_single()
                .execute()
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Organization administrator access could not be verified.",
            ) from exc
        if not membership.data or membership.data.get("role") not in {"owner", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization administrator access is required.",
            )
        return current_user

    return _check
