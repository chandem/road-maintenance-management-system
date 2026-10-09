#!/usr/bin/env python3
"""Read-only Supabase Data API smoke test for road-row RLS.

Run ONLY against an isolated staging project with fake test data. This script
performs GET requests only; it never inserts, updates, or deletes records.

Required environment variables:
  STAGING_SUPABASE_URL       e.g. https://<staging-ref>.supabase.co
  STAGING_SUPABASE_ANON_KEY  staging project's anon/publishable API key
  STAGING_ROAD_ID            ID of one seeded road in the test organization
  TOKEN_ORG_ADMIN            access token for active org owner/admin
  TOKEN_ROAD_MANAGER         access token for active road_asset manager/officer
  TOKEN_FINANCE_MANAGER      access token for finance-only member
  TOKEN_NO_DEPARTMENT_ROLE   access token for active member with no department role
  TOKEN_OTHER_ORG            access token for member of a different organization

The script expects the admin and road manager to see STAGING_ROAD_ID and the
other identities to receive an empty result. Seed fake records and confirm
role assignments before running. Do not use production tokens or keys.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

# Guard against accidentally running this smoke test against the known production
# project. This is an additional safeguard, not a substitute for checking the URL.
KNOWN_PRODUCTION_REF = "firzbqzbezuecvplsibi"


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    base_url = required("STAGING_SUPABASE_URL").rstrip("/")
    anon_key = required("STAGING_SUPABASE_ANON_KEY")
    road_id = required("STAGING_ROAD_ID")

    if KNOWN_PRODUCTION_REF in base_url.lower():
        raise SystemExit(
            "Refusing to run: STAGING_SUPABASE_URL points to the known production project."
        )
    if not base_url.startswith("https://"):
        raise SystemExit("STAGING_SUPABASE_URL must use https://.")

    identities = {
        "org_admin": (required("TOKEN_ORG_ADMIN"), True),
        "road_manager": (required("TOKEN_ROAD_MANAGER"), True),
        "finance_only": (required("TOKEN_FINANCE_MANAGER"), False),
        "no_department_role": (required("TOKEN_NO_DEPARTMENT_ROLE"), False),
        "other_organization": (required("TOKEN_OTHER_ORG"), False),
    }

    query = f"/rest/v1/roads?id=eq.{quote(road_id, safe='')}&select=id"
    endpoint = base_url + query
    failures: list[str] = []

    for identity, (token, should_see_road) in identities.items():
        request = Request(
            endpoint,
            headers={
                "apikey": anon_key,
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=20) as response:
                if response.status != 200:
                    failures.append(f"{identity}: expected HTTP 200, got {response.status}")
                    continue
                rows = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            failures.append(f"{identity}: HTTP {exc.code}: {body}")
            continue
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures.append(f"{identity}: request/response error: {exc}")
            continue

        if not isinstance(rows, list):
            failures.append(f"{identity}: expected a JSON array, got {type(rows).__name__}")
            continue

        saw_road = any(str(row.get("id")) == road_id for row in rows if isinstance(row, dict))
        if saw_road != should_see_road:
            expectation = "visible" if should_see_road else "hidden"
            failures.append(
                f"{identity}: road should be {expectation}; returned {len(rows)} row(s)"
            )
        else:
            result = "visible as expected" if saw_road else "hidden as expected"
            print(f"PASS {identity}: seeded road is {result}")

    if failures:
        print("\nFAILURES:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("\nRead-only road SELECT smoke test passed.")
    print("Note: this checks one row and SELECT visibility only; run the full JWT/RLS matrix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
