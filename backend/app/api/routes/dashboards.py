"""Dashboard and analytics summary endpoints (Step 8)."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.schemas.dashboards import (
    AlertItem,
    ExecutiveDashboard,
    MetricCount,
    ModuleDashboard,
)
from app.services.cross_module_context import collect_cross_module_context

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _alerts_from_summary(summary: dict) -> list[AlertItem]:
    alerts: list[AlertItem] = []
    if summary.get("critical_sections", 0) > 0:
        alerts.append(
            AlertItem(
                severity="high",
                module="RAMS",
                message=(
                    f"{summary['critical_sections']} section(s) have condition "
                    "rating >= 4 and may need priority attention."
                ),
            )
        )
    if summary.get("down_machinery", 0) > 0:
        alerts.append(
            AlertItem(
                severity="medium",
                module="MMMS",
                message=(
                    f"{summary['down_machinery']} machinery unit(s) are down "
                    "or under maintenance."
                ),
            )
        )
    allocated = float(summary.get("budget_allocated") or 0)
    spent = float(summary.get("budget_spent") or 0)
    committed = float(summary.get("budget_committed") or 0)
    if allocated > 0 and (spent + committed) / allocated >= 0.9:
        alerts.append(
            AlertItem(
                severity="high",
                module="Financial Management",
                message="Budget utilization (spent + committed) is at or above 90%.",
            )
        )
    if summary.get("active_work_orders", 0) > 20:
        alerts.append(
            AlertItem(
                severity="medium",
                module="Maintenance Operations",
                message=(
                    f"{summary['active_work_orders']} active work orders — "
                    "review capacity and prioritization."
                ),
            )
        )
    return alerts


@router.get("/executive", response_model=ExecutiveDashboard)
def executive_dashboard(current_user=Depends(get_current_user)):
    """Organization-wide KPI snapshot for executives."""
    ctx = collect_cross_module_context(current_user["client"])
    s = ctx.summary
    metrics = [
        MetricCount(label="Roads", value=s.get("roads", 0)),
        MetricCount(label="Road sections", value=s.get("sections", 0)),
        MetricCount(label="Critical sections", value=s.get("critical_sections", 0)),
        MetricCount(label="Active work orders", value=s.get("active_work_orders", 0)),
        MetricCount(label="Available machinery", value=s.get("available_machinery", 0)),
        MetricCount(label="Down machinery", value=s.get("down_machinery", 0)),
        MetricCount(label="Active employees", value=s.get("active_employees", 0)),
        MetricCount(
            label="Budget allocated",
            value=round(float(s.get("budget_allocated") or 0), 2),
            unit="currency",
        ),
        MetricCount(
            label="Budget spent",
            value=round(float(s.get("budget_spent") or 0), 2),
            unit="currency",
        ),
        MetricCount(label="Active assets", value=s.get("active_assets", 0)),
    ]
    return ExecutiveDashboard(
        metrics=metrics,
        alerts=_alerts_from_summary(s),
        modules=ctx.modules_consulted,
    )


@router.get("/maintenance", response_model=ModuleDashboard)
def maintenance_dashboard(current_user=Depends(get_current_user)):
    """Maintenance operations dashboard (plans + work orders + sections)."""
    client = current_user["client"]
    ctx = collect_cross_module_context(client)
    orders = ctx.samples.get("work_orders") or []
    # Prefer full counts from summary; status breakdown from sample + live query
    try:
        all_orders = (
            client.table("work_orders")
            .select("status,priority")
            .limit(1000)
            .execute()
            .data
            or []
        )
    except Exception:
        all_orders = orders

    by_status = Counter((o.get("status") or "unknown").lower() for o in all_orders)
    by_priority = Counter((o.get("priority") or "unspecified").lower() for o in all_orders)

    metrics = [
        MetricCount(label="Road sections", value=ctx.summary.get("sections", 0)),
        MetricCount(
            label="Critical sections",
            value=ctx.summary.get("critical_sections", 0),
        ),
        MetricCount(
            label="Active work orders",
            value=ctx.summary.get("active_work_orders", 0),
        ),
        MetricCount(label="Work orders (total sampled)", value=len(all_orders)),
    ]
    for status, count in sorted(by_status.items()):
        metrics.append(MetricCount(label=f"WO status: {status}", value=count))
    for priority, count in sorted(by_priority.items()):
        metrics.append(MetricCount(label=f"WO priority: {priority}", value=count))

    return ModuleDashboard(
        module="Maintenance Operations",
        title="Maintenance Dashboard",
        metrics=metrics,
        alerts=[
            a
            for a in _alerts_from_summary(ctx.summary)
            if a.module in {"RAMS", "Maintenance Operations"}
        ],
    )


@router.get("/financial", response_model=ModuleDashboard)
def financial_dashboard(current_user=Depends(get_current_user)):
    """Financial management dashboard."""
    ctx = collect_cross_module_context(current_user["client"])
    s = ctx.summary
    allocated = float(s.get("budget_allocated") or 0)
    spent = float(s.get("budget_spent") or 0)
    committed = float(s.get("budget_committed") or 0)
    remaining = allocated - spent - committed
    utilization = ((spent + committed) / allocated * 100) if allocated > 0 else 0.0

    metrics = [
        MetricCount(label="Allocated", value=round(allocated, 2), unit="currency"),
        MetricCount(label="Spent", value=round(spent, 2), unit="currency"),
        MetricCount(label="Committed", value=round(committed, 2), unit="currency"),
        MetricCount(label="Remaining", value=round(remaining, 2), unit="currency"),
        MetricCount(label="Utilization %", value=round(utilization, 2), unit="percent"),
    ]
    return ModuleDashboard(
        module="Financial Management",
        title="Financial Dashboard",
        metrics=metrics,
        alerts=[a for a in _alerts_from_summary(s) if a.module == "Financial Management"],
    )


@router.get("/machinery", response_model=ModuleDashboard)
def machinery_dashboard(current_user=Depends(get_current_user)):
    """MMMS machinery dashboard."""
    client = current_user["client"]
    ctx = collect_cross_module_context(client)
    try:
        rows = (
            client.table("machinery")
            .select("status,machinery_type")
            .limit(2000)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []

    by_status = Counter((r.get("status") or "unknown").lower() for r in rows)
    by_type = Counter((r.get("machinery_type") or "unspecified").lower() for r in rows)

    metrics = [
        MetricCount(label="Total machinery", value=len(rows)),
        MetricCount(
            label="Available/operational",
            value=ctx.summary.get("available_machinery", 0),
        ),
        MetricCount(
            label="Down / under maintenance",
            value=ctx.summary.get("down_machinery", 0),
        ),
    ]
    for status, count in sorted(by_status.items()):
        metrics.append(MetricCount(label=f"Status: {status}", value=count))
    for mtype, count in sorted(by_type.items()):
        metrics.append(MetricCount(label=f"Type: {mtype}", value=count))

    return ModuleDashboard(
        module="MMMS",
        title="Machinery Dashboard",
        metrics=metrics,
        alerts=[a for a in _alerts_from_summary(ctx.summary) if a.module == "MMMS"],
    )


@router.get("/hr", response_model=ModuleDashboard)
def hr_dashboard(current_user=Depends(get_current_user)):
    """HR workforce dashboard."""
    client = current_user["client"]
    ctx = collect_cross_module_context(client)
    try:
        rows = (
            client.table("employees")
            .select("status,employment_type,job_title")
            .limit(2000)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []

    by_status = Counter((r.get("status") or "unknown").lower() for r in rows)
    by_type = Counter((r.get("employment_type") or "unspecified").lower() for r in rows)

    metrics = [
        MetricCount(label="Total employees", value=len(rows)),
        MetricCount(label="Active", value=ctx.summary.get("active_employees", 0)),
    ]
    for status, count in sorted(by_status.items()):
        metrics.append(MetricCount(label=f"Status: {status}", value=count))
    for etype, count in sorted(by_type.items()):
        metrics.append(MetricCount(label=f"Employment: {etype}", value=count))

    return ModuleDashboard(
        module="HR Management",
        title="HR Dashboard",
        metrics=metrics,
        alerts=[],
    )
