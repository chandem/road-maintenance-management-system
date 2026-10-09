from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.dependencies import require_department_access, require_org_admin
from app.services.ai_audit import resolve_organization_id


class FakeQuery:
    def __init__(self, result):
        self.result = result
        self.filters = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def maybe_single(self):
        return self

    def execute(self):
        if callable(self.result):
            return SimpleNamespace(data=self.result(self.filters))
        return SimpleNamespace(data=self.result)


class FakeClient:
    def __init__(self, *, profile=None, membership=None, rpc_result=True, rpc_error=None):
        self.profile = profile
        self.membership = membership
        self.rpc_result = rpc_result
        self.rpc_error = rpc_error

    def table(self, table_name):
        if table_name == "user_profiles":
            return FakeQuery(self.profile)
        if table_name == "organization_members":
            def membership_for(filters):
                if not self.membership:
                    return None
                return self.membership if all(
                    key not in self.membership
                    or filters.get(key) == self.membership[key]
                    for key in ("organization_id", "user_id", "is_active")
                ) else None
            return FakeQuery(membership_for)
        raise AssertionError(f"Unexpected table: {table_name}")

    def rpc(self, _name, _params):
        if self.rpc_error:
            raise self.rpc_error
        return FakeQuery(self.rpc_result)


def test_resolve_organization_requires_active_membership():
    client = FakeClient(
        profile={"organization_id": "org-1"},
        membership={
            "organization_id": "org-1",
            "user_id": "user-1",
            "is_active": True,
        },
    )

    assert resolve_organization_id(client, "user-1") == "org-1"


def test_resolve_organization_rejects_profile_without_membership():
    client = FakeClient(
        profile={"organization_id": "org-other"},
        membership={
            "organization_id": "org-1",
            "user_id": "user-1",
            "is_active": True,
        },
    )

    assert resolve_organization_id(client, "user-1") is None


def test_resolve_organization_rejects_inactive_membership():
    client = FakeClient(
        profile={"organization_id": "org-1"},
        membership={
            "organization_id": "org-1",
            "user_id": "user-1",
            "is_active": False,
        },
    )

    assert resolve_organization_id(client, "user-1") is None


def test_owner_can_access_department_without_department_assignment(monkeypatch):
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(
        membership={"role": "owner"},
        rpc_result=False,
    )
    current_user = {"id": "user-1", "client": client}

    dependency = require_department_access("road_asset", ["department_manager"])
    assert dependency(current_user=current_user) == current_user


def test_missing_department_role_is_forbidden(monkeypatch):
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(
        membership={"role": "member"},
        rpc_result=False,
    )
    dependency = require_department_access("road_asset", ["officer"])

    with pytest.raises(HTTPException) as exc:
        dependency(current_user={"id": "user-1", "client": client})

    assert exc.value.status_code == 403


def test_department_lookup_failure_fails_closed(monkeypatch):
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(
        membership={"role": "member"},
        rpc_error=RuntimeError("database unavailable"),
    )
    dependency = require_department_access("road_asset", ["officer"])

    with pytest.raises(HTTPException) as exc:
        dependency(current_user={"id": "user-1", "client": client})

    assert exc.value.status_code == 503



def test_org_admin_dependency_allows_active_owner(monkeypatch):
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(membership={"role": "owner"})
    current_user = {"id": "user-1", "client": client}

    assert require_org_admin()(current_user=current_user) == current_user


def test_org_admin_dependency_rejects_department_member(monkeypatch):
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(membership={"role": "member"})

    with pytest.raises(HTTPException) as exc:
        require_org_admin()(current_user={"id": "user-1", "client": client})

    assert exc.value.status_code == 403


def test_org_admin_dependency_fails_closed_on_lookup_error(monkeypatch):
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")

    class BrokenClient(FakeClient):
        def table(self, table_name):
            if table_name == "organization_members":
                raise RuntimeError("database unavailable")
            return super().table(table_name)

    with pytest.raises(HTTPException) as exc:
        require_org_admin()(current_user={"id": "user-1", "client": BrokenClient()})

    assert exc.value.status_code == 503



def test_document_department_authorization_allows_matching_manager(monkeypatch):
    from app.api.routes.documents import _authorize_department
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(
        membership={
            "organization_id": "org-1",
            "user_id": "user-1",
            "is_active": True,
            "role": "member",
        },
        rpc_result=True,
    )
    assert _authorize_department(
        {"id": "user-1", "client": client}, "road_asset", write=True
    ) == "org-1"


def test_document_department_authorization_requires_scope_for_non_admin(monkeypatch):
    from app.api.routes.documents import _authorize_department
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(
        membership={
            "organization_id": "org-1",
            "user_id": "user-1",
            "is_active": True,
            "role": "member",
        }
    )
    with pytest.raises(HTTPException) as exc:
        _authorize_department({"id": "user-1", "client": client}, None)
    assert exc.value.status_code == 403


def test_document_department_authorization_keeps_legacy_documents_admin_only(monkeypatch):
    from app.api.routes.documents import _authorize_document_row
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(
        membership={
            "organization_id": "org-1",
            "user_id": "user-1",
            "is_active": True,
            "role": "member",
        }
    )
    with pytest.raises(HTTPException) as exc:
        _authorize_document_row(
            {"id": "user-1", "client": client},
            {
                "id": "doc-1",
                "organization_id": "org-1",
                "department_code": None,
            },
        )
    assert exc.value.status_code == 403


def test_document_department_authorization_fails_closed_on_rpc_error(monkeypatch):
    from app.api.routes.documents import _authorize_department
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(
        membership={
            "organization_id": "org-1",
            "user_id": "user-1",
            "is_active": True,
            "role": "member",
        },
        rpc_error=RuntimeError("database unavailable"),
    )
    with pytest.raises(HTTPException) as exc:
        _authorize_department(
            {"id": "user-1", "client": client}, "road_asset"
        )
    assert exc.value.status_code == 503



def test_document_department_authorization_rejects_read_only_write(monkeypatch):
    from app.api.routes.documents import _authorize_department
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(
        membership={
            "organization_id": "org-1",
            "user_id": "user-1",
            "is_active": True,
            "role": "member",
        },
        rpc_result=False,
    )
    with pytest.raises(HTTPException) as exc:
        _authorize_department(
            {"id": "user-1", "client": client}, "finance", write=True
        )
    assert exc.value.status_code == 403


def test_document_department_authorization_rejects_invalid_department(monkeypatch):
    from app.api.routes.documents import _authorize_department
    from app.services import ai_audit

    monkeypatch.setattr(ai_audit, "resolve_organization_id", lambda *_args: "org-1")
    client = FakeClient(
        membership={
            "organization_id": "org-1",
            "user_id": "user-1",
            "is_active": True,
            "role": "admin",
        }
    )
    with pytest.raises(HTTPException) as exc:
        _authorize_department(
            {"id": "user-1", "client": client}, "not-a-department"
        )
    assert exc.value.status_code == 422


def test_document_department_authorization_fails_closed_on_org_resolution_error(monkeypatch):
    from app.api.routes.documents import _authorize_department
    from app.services import ai_audit

    def broken_resolve(*_args):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(ai_audit, "resolve_organization_id", broken_resolve)
    with pytest.raises(HTTPException) as exc:
        _authorize_department(
            {"id": "user-1", "client": FakeClient()}, "road_asset"
        )
    assert exc.value.status_code == 503
