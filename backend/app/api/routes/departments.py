"""Department discovery and role assignment endpoints.

All queries use the caller's JWT-scoped Supabase client so database RLS remains
an independent authorization layer. Organization admins are the only users
allowed to assign or revoke department roles.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/departments", tags=["departments"])


class DepartmentRoleAssignment(BaseModel):
    user_id: UUID
    department_id: UUID
    role: str = Field(pattern=r"^(department_manager|officer|read_only)$")


def _organization_id(current_user) -> str:
    try:
        organization_id = resolve_organization_id(
            current_user["client"], current_user["id"]
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify organization membership.",
        ) from exc
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is not an active member of an organization.",
        )
    return str(organization_id)


def _require_org_admin(current_user, organization_id: str) -> None:
    try:
        result = (
            current_user["client"]
            .table("organization_members")
            .select("role,is_active")
            .eq("organization_id", organization_id)
            .eq("user_id", current_user["id"])
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify organization administrator permission.",
        ) from exc
    if not result.data or result.data.get("role") not in {"owner", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization administrator permission required.",
        )


@router.get("")
def list_departments(current_user=Depends(get_current_user)):
    """List departments in the caller's organization."""
    organization_id = _organization_id(current_user)
    response = (
        current_user["client"]
        .table("departments")
        .select("id,organization_id,name,code")
        .eq("organization_id", organization_id)
        .order("name")
        .execute()
    )
    return response.data or []


@router.get("/me/roles")
def list_my_department_roles(current_user=Depends(get_current_user)):
    """Return only the signed-in user's active department assignments."""
    organization_id = _organization_id(current_user)
    response = (
        current_user["client"]
        .table("user_department_roles")
        .select("id,department_id,role,is_active,created_at,departments(name,code)")
        .eq("organization_id", organization_id)
        .eq("user_id", current_user["id"])
        .eq("is_active", True)
        .execute()
    )
    return response.data or []


@router.get("/roles")
def list_department_roles(current_user=Depends(get_current_user)):
    """Organization-admin view of active and inactive department assignments."""
    organization_id = _organization_id(current_user)
    _require_org_admin(current_user, organization_id)
    response = (
        current_user["client"]
        .table("user_department_roles")
        .select(
            "id,user_id,department_id,role,is_active,assigned_by,created_at,updated_at,"
            "departments(name,code)"
        )
        .eq("organization_id", organization_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def assign_department_role(
    payload: DepartmentRoleAssignment,
    current_user=Depends(get_current_user),
):
    """Create or update a role; caller must be an organization admin."""
    organization_id = _organization_id(current_user)
    _require_org_admin(current_user, organization_id)
    supabase = current_user["client"]

    try:
        department = (
            supabase.table("departments")
            .select("id")
            .eq("id", str(payload.department_id))
            .eq("organization_id", organization_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify department membership.",
        ) from exc
    if not department.data:
        raise HTTPException(status_code=404, detail="Department not found in this organization.")

    try:
        membership = (
            supabase.table("organization_members")
            .select("user_id")
            .eq("organization_id", organization_id)
            .eq("user_id", str(payload.user_id))
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify target organization membership.",
        ) from exc
    if not membership.data:
        raise HTTPException(
            status_code=422,
            detail="Target user must be an active member of this organization.",
        )

    row = {
        "organization_id": organization_id,
        "user_id": str(payload.user_id),
        "department_id": str(payload.department_id),
        "role": payload.role,
        "is_active": True,
        "assigned_by": current_user["id"],
    }
    response = (
        supabase.table("user_department_roles")
        .upsert(row, on_conflict="organization_id,user_id,department_id")
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Department role assignment failed.")
    return response.data[0]


@router.delete("/roles/{assignment_id}")
def revoke_department_role(
    assignment_id: UUID,
    current_user=Depends(get_current_user),
):
    """Deactivate an assignment without deleting its audit history."""
    organization_id = _organization_id(current_user)
    _require_org_admin(current_user, organization_id)
    response = (
        current_user["client"]
        .table("user_department_roles")
        .update({"is_active": False})
        .eq("id", str(assignment_id))
        .eq("organization_id", organization_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Department role assignment not found.")
    return {"ok": True, "assignment": response.data[0]}
