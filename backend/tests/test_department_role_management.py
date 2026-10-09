from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.routes import departments


ORG = "11111111-1111-1111-1111-111111111111"
USER = "22222222-2222-2222-2222-222222222222"
DEPT = "33333333-3333-3333-3333-333333333333"
ASSIGNMENT = "44444444-4444-4444-4444-444444444444"


class Query:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table
        self.filters = {}
        self.operation = "select"
        self.payload = None
        self.conflict = None

    def select(self, *_args, **_kwargs):
        self.operation = "select"
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def maybe_single(self):
        self.single = True
        return self

    def order(self, *_args, **_kwargs):
        return self

    def upsert(self, payload, on_conflict=None):
        self.operation = "upsert"
        self.payload = payload
        self.conflict = on_conflict
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def execute(self):
        self.client.calls.append({
            "table": self.table_name,
            "operation": self.operation,
            "filters": dict(self.filters),
            "payload": self.payload,
            "conflict": self.conflict,
        })
        rows = self.client.rows.get(self.table_name, [])
        matched = [
            row for row in rows
            if all(row.get(key) == value for key, value in self.filters.items())
        ]
        if self.operation == "upsert":
            self.client.upserted = self.payload
            return SimpleNamespace(data=[self.payload])
        if self.operation == "update":
            updated = []
            for row in matched:
                row.update(self.payload)
                updated.append(dict(row))
            return SimpleNamespace(data=updated)
        if getattr(self, "single", False):
            return SimpleNamespace(data=matched[0] if matched else None)
        return SimpleNamespace(data=matched)


class Client:
    def __init__(self, *, role="admin", active_member=True, department=True, target_member=True):
        self.rows = {
            "organization_members": [{
                "organization_id": ORG,
                "user_id": USER,
                "role": role,
                "is_active": active_member,
            }],
            "departments": ([{"id": DEPT, "organization_id": ORG}] if department else []),
            "user_department_roles": ([{
                "id": ASSIGNMENT,
                "organization_id": ORG,
                "user_id": USER,
                "department_id": DEPT,
                "role": "officer",
                "is_active": True,
            }] if target_member else []),
        }
        self.calls = []
        self.upserted = None

    def table(self, name):
        return Query(self, name)


def current_user(client):
    return {"id": USER, "client": client}


def patch_org(monkeypatch):
    monkeypatch.setattr(departments, "resolve_organization_id", lambda *_args: ORG)


def test_admin_can_assign_role_to_active_org_member(monkeypatch):
    patch_org(monkeypatch)
    client = Client()
    payload = departments.DepartmentRoleAssignment(
        user_id=UUID(USER), department_id=UUID(DEPT), role="officer"
    )

    result = departments.assign_department_role(payload, current_user(client))

    assert result["role"] == "officer"
    assert client.upserted["organization_id"] == ORG
    assert client.upserted["assigned_by"] == USER
    assert client.upserted["is_active"] is True
    assert any(c["table"] == "user_department_roles" and c["operation"] == "upsert"
               and c["conflict"] == "organization_id,user_id,department_id"
               for c in client.calls)


@pytest.mark.parametrize("role", ["member", "department_manager", "officer"])
def test_non_admin_cannot_assign_roles(monkeypatch, role):
    patch_org(monkeypatch)
    client = Client(role=role)
    payload = departments.DepartmentRoleAssignment(
        user_id=UUID(USER), department_id=UUID(DEPT), role="officer"
    )

    with pytest.raises(HTTPException) as exc:
        departments.assign_department_role(payload, current_user(client))

    assert exc.value.status_code == 403
    assert client.upserted is None


def test_inactive_admin_cannot_assign_roles(monkeypatch):
    patch_org(monkeypatch)
    client = Client(active_member=False)
    payload = departments.DepartmentRoleAssignment(
        user_id=UUID(USER), department_id=UUID(DEPT), role="officer"
    )

    with pytest.raises(HTTPException) as exc:
        departments.assign_department_role(payload, current_user(client))

    assert exc.value.status_code == 403


def test_cannot_assign_role_for_department_outside_organization(monkeypatch):
    patch_org(monkeypatch)
    client = Client(department=False)
    payload = departments.DepartmentRoleAssignment(
        user_id=UUID(USER), department_id=UUID(DEPT), role="officer"
    )

    with pytest.raises(HTTPException) as exc:
        departments.assign_department_role(payload, current_user(client))

    assert exc.value.status_code == 404
    assert client.upserted is None


def test_cannot_assign_role_to_inactive_or_nonmember_user(monkeypatch):
    patch_org(monkeypatch)
    client = Client(target_member=False)
    payload = departments.DepartmentRoleAssignment(
        user_id=UUID(USER), department_id=UUID(DEPT), role="officer"
    )

    with pytest.raises(HTTPException) as exc:
        departments.assign_department_role(payload, current_user(client))

    assert exc.value.status_code == 422
    assert client.upserted is None


def test_admin_revokes_role_without_deleting_audit_row(monkeypatch):
    patch_org(monkeypatch)
    client = Client()

    result = departments.revoke_department_role(UUID(ASSIGNMENT), current_user(client))

    assert result["ok"] is True
    assert result["assignment"]["is_active"] is False
    update = next(c for c in client.calls if c["operation"] == "update")
    assert update["payload"] == {"is_active": False}
    assert update["filters"] == {"id": ASSIGNMENT, "organization_id": ORG}


def test_non_admin_cannot_revoke_role(monkeypatch):
    patch_org(monkeypatch)
    client = Client(role="member")

    with pytest.raises(HTTPException) as exc:
        departments.revoke_department_role(UUID(ASSIGNMENT), current_user(client))

    assert exc.value.status_code == 403
    assert not any(c["operation"] == "update" for c in client.calls)


def test_cannot_revoke_assignment_from_another_organization(monkeypatch):
    patch_org(monkeypatch)
    client = Client()
    client.rows["user_department_roles"] = [{
        "id": ASSIGNMENT,
        "organization_id": "other-org",
        "is_active": True,
    }]

    with pytest.raises(HTTPException) as exc:
        departments.revoke_department_role(UUID(ASSIGNMENT), current_user(client))

    assert exc.value.status_code == 404
    update = next(c for c in client.calls if c["operation"] == "update")
    assert update["filters"]["organization_id"] == ORG
