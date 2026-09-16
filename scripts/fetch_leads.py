"""
Fetch leads from the "Leads Sheet" Google Sheet for the staffing-outreach skill.

Reuses the leads scraper's service-account credentials and sheet name
(scraper/config.py + .env). Run from the project root:

    python .claude/skills/staffing-outreach/scripts/fetch_leads.py --limit 25

Output: JSON list of leads at outbox/leads.json (override with --out).
By default only rows that have an Email are included.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# --- Make the scraper package importable regardless of where python is invoked ---
PROJECT_ROOT = Path(__file__).resolve().parents[4]  # .../Skills
SKILL_DIR = Path(__file__).resolve().parents[1]     # .../staffing-outreach
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import gspread
    from google.oauth2.service_account import Credentials
    from scraper.config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_NAME
except ImportError as exc:  # pragma: no cover
    sys.exit(
        f"[fetch_leads] Missing dependency or scraper package: {exc}\n"
        "Run from the project root after `pip install -r requirements.txt`."
    )

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
_WORKSHEET_NAME = "Sheet1"


def _resolve_creds_path() -> Path:
    p = Path(GOOGLE_CREDENTIALS_PATH)
    candidates = [p]
    if not p.is_absolute():
        candidates += [Path.cwd() / p, PROJECT_ROOT / p, (PROJECT_ROOT / p).resolve()]
    for c in candidates:
        if c.exists():
            return c
    sys.exit(
        f"[fetch_leads] Service account key not found. Tried: "
        + ", ".join(str(c) for c in candidates)
        + "\nSet GOOGLE_CREDENTIALS_PATH in .env (see README.md)."
    )


def _client() -> "gspread.Client":
    creds = Credentials.from_service_account_file(str(_resolve_creds_path()), scopes=_SCOPES)
    return gspread.authorize(creds)


def fetch(limit: int, include_company_only: bool, worksheet: str) -> list[dict]:
    ws = _client().open(GOOGLE_SHEET_NAME).worksheet(worksheet)
    rows = ws.get_all_values()
    if len(rows) <= 1:
        return []

    header = [h.strip().lower() for h in rows[0]]

    def col(name: str) -> int:
        try:
            return header.index(name)
        except ValueError:
            return -1

    idx = {k: col(k) for k in (
        "rowid", "firstname", "lastname", "email", "company",
        "title", "domain", "phone", "employees",
    )}

    def get(row: list[str], key: str) -> str:
        i = idx[key]
        return row[i].strip() if 0 <= i < len(row) else ""

    leads: list[dict] = []
    for row in rows[1:]:
        email = get(row, "email")
        company = get(row, "company")
        if not company:
            continue
        if not email and not include_company_only:
            continue
        leads.append(
            {
                "row_id": get(row, "rowid"),
                "first_name": get(row, "firstname"),
                "last_name": get(row, "lastname"),
                "email": email,
                "company": company,
                "title": get(row, "title"),
                "domain": get(row, "domain"),
                "phone": get(row, "phone"),
                "employees": get(row, "employees"),
                "needs_address": not email,
            }
        )
        if limit and len(leads) >= limit:
            break
    return leads


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch leads from the Leads Sheet.")
    ap.add_argument("--limit", type=int, default=0, help="Max leads (0 = all).")
    ap.add_argument(
        "--include-company-only",
        action="store_true",
        help="Also include rows that have no email address.",
    )
    ap.add_argument("--worksheet", default=_WORKSHEET_NAME, help="Worksheet/tab name.")
    ap.add_argument(
        "--out",
        default=str(SKILL_DIR / "outbox" / "leads.json"),
        help="Output JSON path.",
    )
    args = ap.parse_args()

    leads = fetch(args.limit, args.include_company_only, args.worksheet)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(leads, indent=2, ensure_ascii=False), encoding="utf-8")

    with_email = sum(1 for l in leads if l["email"])
    print(f"[fetch_leads] {len(leads)} leads written to {out}")
    print(f"[fetch_leads]   with email:        {with_email}")
    print(f"[fetch_leads]   company-only:      {len(leads) - with_email}")
    print(f'[fetch_leads] Sheet: "{GOOGLE_SHEET_NAME}" / worksheet "{args.worksheet}"')


if __name__ == "__main__":
    main()
