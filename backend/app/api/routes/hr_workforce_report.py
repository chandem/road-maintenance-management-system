"""Aggregated HR workforce report from employees, leave, and training."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, Depends

from app.api.dependencies import require_department_access

router = APIRouter(prefix="/employees", tags=["hr-workforce-report"])


@router.get("/workforce-report")
def workforce_report(
    current_user=Depends(
        require_department_access(
            "human_resources", ["department_manager", "officer", "read_only"]
        )
    ),
) -> dict:
    """Workforce totals, leave pipeline, and qualification expiry snapshot."""
    client = current_user["client"]

    employees = (
        client.table("employees")
        .select("id,employee_code,full_name,status,employment_type,job_title")
        .limit(2000)
        .execute()
        .data
        or []
    )
    by_status = Counter((r.get("status") or "unknown").lower() for r in employees)
    by_type = Counter((r.get("employment_type") or "unspecified").lower() for r in employees)

    leave_rows: list = []
    try:
        leave_rows = (
            client.table("hr_leave_requests")
            .select("status,leave_type,days_requested")
            .limit(2000)
            .execute()
            .data
            or []
        )
    except Exception:
        leave_rows = []
    leave_by_status = Counter((r.get("status") or "unknown").lower() for r in leave_rows)

    training_rows: list = []
    expiring_soon = 0
    horizon = date.today() + timedelta(days=60)
    try:
        training_rows = (
            client.table("hr_training_records")
            .select("status,record_type,expires_on,title,employee_id")
            .limit(2000)
            .execute()
            .data
            or []
        )
        for row in training_rows:
            if (row.get("status") or "").lower() != "valid":
                continue
            exp = row.get("expires_on")
            if not exp:
                continue
            try:
                exp_d = date.fromisoformat(str(exp)[:10])
            except ValueError:
                continue
            if date.today() <= exp_d <= horizon:
                expiring_soon += 1
    except Exception:
        training_rows = []

    train_by_status = Counter((r.get("status") or "unknown").lower() for r in training_rows)

    return {
        "title": "HR Workforce Report",
        "workforce": {
            "total": len(employees),
            "active_count": by_status.get("active", 0),
            "by_status": dict(by_status),
            "by_employment_type": dict(by_type),
        },
        "leave": {
            "total_requests": len(leave_rows),
            "pending_count": leave_by_status.get("pending", 0),
            "approved_count": leave_by_status.get("approved", 0),
            "by_status": dict(leave_by_status),
        },
        "qualifications": {
            "total_records": len(training_rows),
            "valid_count": train_by_status.get("valid", 0),
            "expired_count": train_by_status.get("expired", 0),
            "expiring_within_60_days": expiring_soon,
        },
        "advisory_note": (
            "Decision-support only. Figures come from employees, leave requests, "
            "and training records visible to your HR department role."
        ),
    }
