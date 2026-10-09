"""Collect operational context, optionally restricted to authorized modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrossModuleContext:
    evidence: list[str] = field(default_factory=list)
    modules_consulted: list[str] = field(default_factory=list)
    samples: dict[str, list[dict]] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


MODULE_TABLES = {
    "road_asset": {"roads", "road_sections", "maintenance_plans", "work_orders", "materials"},
    "machinery_maintenance": {"machinery"},
    "finance": {"budgets", "expenses"},
    "human_resources": {"employees"},
    "general_assets": {"assets"},
}


def collect_cross_module_context(
    client: Any, allowed_modules: set[str] | None = None
) -> CrossModuleContext:
    """Load only authorized module data when a module scope is supplied.

    None means all modules and is reserved for organization-admin features.
    """
    ctx = CrossModuleContext()

    def select(table: str, columns: str, limit: int) -> list[dict]:
        if allowed_modules is not None and not any(
            table in MODULE_TABLES.get(module, set()) for module in allowed_modules
        ):
            return []
        return _select(client, table, columns, limit)

    roads = select("roads", "id,road_code,name,total_length_km,status", 100)
    sections = select("road_sections", "id,road_id,section_code,condition_rating,status", 500)
    plans = select("maintenance_plans", "id,name,fiscal_year,plan_type,status,budget_amount,start_date,end_date", 100)
    work_orders = select("work_orders", "id,road_section_id,work_order_no,title,maintenance_type,priority,status,planned_cost,actual_cost", 500)
    machinery = select("machinery", "id,asset_code,name,machinery_type,status,current_hours", 200)
    employees = select("employees", "id,employee_code,full_name,job_title,status", 200)
    budgets = select("budgets", "id,fiscal_year,budget_code,category,allocated_amount,spent_amount,committed_amount,status", 50)
    expenses = select("expenses", "id,budget_id,work_order_id,expense_date,description,category,amount,status", 200)
    assets = select("assets", "id,asset_code,name,category,location,status,current_value", 200)
    materials = select("materials", "id,material_code,name,category,unit,quantity_on_hand,reorder_level,status", 200)

    active_orders = [
        item for item in work_orders
        if (item.get("status") or "").lower() not in {"completed", "closed", "cancelled"}
    ]
    critical_sections = [
        item for item in sections
        if item.get("condition_rating") is not None and float(item["condition_rating"]) >= 4
    ]
    available_machinery = [
        item for item in machinery
        if (item.get("status") or "").lower() in {"available", "ready", "operational"}
    ]
    down_machinery = [
        item for item in machinery
        if (item.get("status") or "").lower() in {"down", "under_maintenance", "broken", "unavailable"}
    ]
    active_employees = [
        item for item in employees if (item.get("status") or "").lower() == "active"
    ]
    active_assets = [
        item for item in assets if (item.get("status") or "").lower() == "active"
    ]

    total_allocated = sum(float(b.get("allocated_amount") or 0) for b in budgets)
    total_spent = sum(float(b.get("spent_amount") or 0) for b in budgets)
    total_committed = sum(float(b.get("committed_amount") or 0) for b in budgets)

    module_names = {
        "road_asset": ["RAMS", "Maintenance Operations", "Materials Management"],
        "machinery_maintenance": ["MMMS"],
        "finance": ["Financial Management"],
        "human_resources": ["HR Management"],
        "general_assets": ["General Asset Management"],
    }
    if allowed_modules is None:
        ctx.modules_consulted = [
            "RAMS", "Maintenance Operations", "MMMS", "Financial Management",
            "HR Management", "General Asset Management", "Materials Management",
        ]
    else:
        ctx.modules_consulted = [
            name for module in module_names if module in allowed_modules
            for name in module_names[module]
        ]

    ctx.evidence = []
    if allowed_modules is None or "road_asset" in allowed_modules:
        ctx.evidence.extend([
            f"Road records available: {len(roads)}.",
            f"Road sections available: {len(sections)}.",
            f"Maintenance plans available: {len(plans)}.",
            f"Work orders available: {len(work_orders)}; active: {len(active_orders)}.",
            f"Sections with condition rating >= 4: {len(critical_sections)}.",
            f"Materials inventory records: {len(materials)}.",
        ])
    if allowed_modules is None or "machinery_maintenance" in allowed_modules:
        ctx.evidence.append(
            f"Machinery: {len(machinery)}; available/operational: {len(available_machinery)}; "
            f"down/under maintenance: {len(down_machinery)}."
        )
    if allowed_modules is None or "human_resources" in allowed_modules:
        ctx.evidence.append(f"Employees: {len(employees)}; active: {len(active_employees)}.")
    if allowed_modules is None or "finance" in allowed_modules:
        ctx.evidence.extend([
            f"Budgets: {len(budgets)}; allocated: {total_allocated:.2f}; spent: {total_spent:.2f}; committed: {total_committed:.2f}.",
            f"Expense records: {len(expenses)}.",
        ])
    if allowed_modules is None or "general_assets" in allowed_modules:
        ctx.evidence.append(f"General assets: {len(assets)}; active: {len(active_assets)}.")

    ctx.samples = {
        "roads": roads[:10], "sections": sections[:15], "plans": plans[:10],
        "work_orders": work_orders[:15], "machinery": machinery[:10],
        "employees": employees[:10], "budgets": budgets[:10],
        "expenses": expenses[:10], "assets": assets[:10], "materials": materials[:10],
    }
    ctx.summary = {
        "roads": len(roads), "sections": len(sections),
        "active_work_orders": len(active_orders), "critical_sections": len(critical_sections),
        "available_machinery": len(available_machinery), "down_machinery": len(down_machinery),
        "active_employees": len(active_employees), "budget_allocated": total_allocated,
        "budget_spent": total_spent, "budget_committed": total_committed,
        "active_assets": len(active_assets), "materials": len(materials),
    }
    return ctx


def _select(client: Any, table: str, columns: str, limit: int) -> list[dict]:
    try:
        return client.table(table).select(columns).limit(limit).execute().data or []
    except Exception:
        return []
