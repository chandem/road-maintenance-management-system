"""Collect cross-module operational context for the AI office assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrossModuleContext:
    evidence: list[str] = field(default_factory=list)
    modules_consulted: list[str] = field(default_factory=list)
    samples: dict[str, list[dict]] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


def collect_cross_module_context(client: Any) -> CrossModuleContext:
    """Load structured snapshots from all core management modules."""
    ctx = CrossModuleContext()

    roads = _select(
        client, "roads", "id,road_code,name,total_length_km,status", 100
    )
    sections = _select(
        client,
        "road_sections",
        "id,road_id,section_code,condition_rating,status",
        500,
    )
    plans = _select(
        client,
        "maintenance_plans",
        "id,name,fiscal_year,plan_type,status,budget_amount,start_date,end_date",
        100,
    )
    work_orders = _select(
        client,
        "work_orders",
        "id,road_section_id,work_order_no,title,maintenance_type,"
        "priority,status,planned_cost,actual_cost",
        500,
    )
    machinery = _select(
        client,
        "machinery",
        "id,asset_code,name,machinery_type,status,current_hours",
        200,
    )
    employees = _select(
        client,
        "employees",
        "id,employee_code,full_name,job_title,status",
        200,
    )
    budgets = _select(
        client,
        "budgets",
        "id,fiscal_year,budget_code,category,allocated_amount,"
        "spent_amount,committed_amount,status",
        50,
    )
    expenses = _select(
        client,
        "expenses",
        "id,budget_id,work_order_id,expense_date,description,"
        "category,amount,status",
        200,
    )
    assets = _select(
        client,
        "assets",
        "id,asset_code,name,category,location,status,current_value",
        200,
    )

    active_orders = [
        item
        for item in work_orders
        if (item.get("status") or "").lower()
        not in {"completed", "closed", "cancelled"}
    ]
    critical_sections = [
        item
        for item in sections
        if item.get("condition_rating") is not None
        and float(item["condition_rating"]) >= 4
    ]
    available_machinery = [
        item
        for item in machinery
        if (item.get("status") or "").lower()
        in {"available", "ready", "operational"}
    ]
    down_machinery = [
        item
        for item in machinery
        if (item.get("status") or "").lower()
        in {"down", "under_maintenance", "broken", "unavailable"}
    ]
    active_employees = [
        item
        for item in employees
        if (item.get("status") or "").lower() == "active"
    ]
    active_assets = [
        item
        for item in assets
        if (item.get("status") or "").lower() == "active"
    ]

    total_allocated = sum(float(b.get("allocated_amount") or 0) for b in budgets)
    total_spent = sum(float(b.get("spent_amount") or 0) for b in budgets)
    total_committed = sum(float(b.get("committed_amount") or 0) for b in budgets)

    ctx.modules_consulted = [
        "RAMS",
        "Maintenance Operations",
        "MMMS",
        "Financial Management",
        "HR Management",
        "General Asset Management",
    ]

    ctx.evidence = [
        f"Road records available: {len(roads)}.",
        f"Road sections available: {len(sections)}.",
        f"Maintenance plans available: {len(plans)}.",
        f"Work orders available: {len(work_orders)}; active: {len(active_orders)}.",
        f"Sections with condition rating >= 4: {len(critical_sections)}.",
        (
            f"Machinery: {len(machinery)}; available/operational: "
            f"{len(available_machinery)}; down/under maintenance: {len(down_machinery)}."
        ),
        f"Employees: {len(employees)}; active: {len(active_employees)}.",
        (
            f"Budgets: {len(budgets)}; allocated: {total_allocated:.2f}; "
            f"spent: {total_spent:.2f}; committed: {total_committed:.2f}."
        ),
        f"Expense records: {len(expenses)}.",
        f"General assets: {len(assets)}; active: {len(active_assets)}.",
    ]

    ctx.samples = {
        "roads": roads[:10],
        "sections": sections[:15],
        "plans": plans[:10],
        "work_orders": work_orders[:15],
        "machinery": machinery[:10],
        "employees": employees[:10],
        "budgets": budgets[:10],
        "expenses": expenses[:10],
        "assets": assets[:10],
    }

    ctx.summary = {
        "roads": len(roads),
        "sections": len(sections),
        "active_work_orders": len(active_orders),
        "critical_sections": len(critical_sections),
        "available_machinery": len(available_machinery),
        "down_machinery": len(down_machinery),
        "active_employees": len(active_employees),
        "budget_allocated": total_allocated,
        "budget_spent": total_spent,
        "budget_committed": total_committed,
        "active_assets": len(active_assets),
    }
    return ctx


def _select(client: Any, table: str, columns: str, limit: int) -> list[dict]:
    try:
        return (
            client.table(table).select(columns).limit(limit).execute().data or []
        )
    except Exception:
        return []
