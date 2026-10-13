from app.services.cross_module_context import collect_cross_module_context


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table

    def select(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        self.client.queried_tables.append(self.table_name)
        return type("Result", (), {"data": []})()


class FakeClient:
    def __init__(self):
        self.queried_tables = []

    def table(self, table_name):
        return FakeQuery(self, table_name)


def test_road_asset_context_never_queries_other_departments():
    client = FakeClient()

    ctx = collect_cross_module_context(client, allowed_modules={"road_asset"})

    assert set(client.queried_tables) == {
        "roads", "road_sections", "maintenance_plans", "work_orders", "materials"
    }
    assert not ({"machinery", "employees", "budgets", "expenses", "assets"} & set(client.queried_tables))
    assert ctx.summary["budget_allocated"] == 0
    assert ctx.summary["active_employees"] == 0
    assert "Financial Management" not in ctx.modules_consulted
    assert "HR Management" not in ctx.modules_consulted


def test_finance_context_only_queries_finance_tables():
    client = FakeClient()

    ctx = collect_cross_module_context(client, allowed_modules={"finance"})

    assert set(client.queried_tables) == {"budgets", "expenses"}
    assert ctx.modules_consulted == ["Financial Management"]
    assert ctx.summary["roads"] == 0
    assert ctx.summary["budget_allocated"] == 0


def test_unrestricted_context_still_collects_all_modules_for_admin():
    client = FakeClient()

    collect_cross_module_context(client)

    assert set(client.queried_tables) == {
        "roads", "road_sections", "maintenance_plans", "work_orders", "machinery",
        "employees", "budgets", "expenses", "assets", "materials",
    }
