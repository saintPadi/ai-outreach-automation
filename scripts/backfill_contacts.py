"""
Backfill missing contact info on the existing "Leads Sheet".

The scraper's exporter dedupes by domain, so re-running it will NOT add emails
to companies already in the sheet. This script instead walks the existing rows
and, for any row missing an email:

  1. runs the improved website enrichment (free), and
  2. optionally (--hunter) falls back to the Hunter.io API for rows still
     missing an email.

Matches are written (Email / FirstName / LastName / Title / Domain) back into
the same row. Empty cells only, unless the row is in --include-rows.

Run from the project root:

    python .claude/skills/staffing-outreach/scripts/backfill_contacts.py --dry-run
    python .claude/skills/staffing-outreach/scripts/backfill_contacts.py --limit 20
    python .claude/skills/staffing-outreach/scripts/backfill_contacts.py --hunter --hunter-max 20
    python .claude/skills/staffing-outreach/scripts/backfill_contacts.py --include-rows 36

Hunter.io free plan is ~25 searches/month. Results are cached in
state/hunter_cache.json so re-runs don't re-spend credits, and --hunter-max
caps how many *new* API calls a single run may make.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import gspread
    from gspread.utils import rowcol_to_a1
    from google.oauth2.service_account import Credentials
    from scraper.config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_NAME
    from scraper.enrichment.website_scraper import enrich
    from scraper.enrichment import hunter
    from scraper.models import Company
except ImportError as exc:  # pragma: no cover
    sys.exit(f"[backfill] Import failed: {exc}\nRun from the project root.")

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
_WORKSHEET_NAME = "Sheet1"
_HUNTER_CACHE = SKILL_DIR / "state" / "hunter_cache.json"


def _resolve_creds_path() -> Path:
    p = Path(GOOGLE_CREDENTIALS_PATH)
    for c in ([p] if p.is_absolute() else [p, Path.cwd() / p, PROJECT_ROOT / p]):
        if c.exists():
            return c
    sys.exit(f"[backfill] Service account key not found (GOOGLE_CREDENTIALS_PATH={GOOGLE_CREDENTIALS_PATH}).")


def _ws() -> "gspread.Worksheet":
    creds = Credentials.from_service_account_file(str(_resolve_creds_path()), scopes=_SCOPES)
    return gspread.authorize(creds).open(GOOGLE_SHEET_NAME).worksheet(_WORKSHEET_NAME)


def _load_cache() -> dict:
    try:
        return json.loads(_HUNTER_CACHE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict) -> None:
    _HUNTER_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _HUNTER_CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill missing emails on the Leads Sheet.")
    ap.add_argument("--limit", type=int, default=0, help="Max rows to process (0 = all).")
    ap.add_argument("--dry-run", action="store_true", help="Print what would change; don't write.")
    ap.add_argument(
        "--include-rows",
        default="",
        help="Comma-separated RowIds to (re)enrich even if they already have an email.",
    )
    ap.add_argument("--hunter", action="store_true", help="Use Hunter.io as a fallback.")
    ap.add_argument(
        "--hunter-max",
        type=int,
        default=15,
        help="Max NEW Hunter API calls this run (cached domains don't count). Default 15.",
    )
    ap.add_argument(
        "--hunter-min-confidence",
        type=int,
        default=50,
        help="Ignore Hunter matches below this confidence (0-100). Default 50.",
    )
    args = ap.parse_args()
    force_ids = {r.strip() for r in args.include_rows.split(",") if r.strip()}

    use_hunter = args.hunter
    hunter_cache = _load_cache() if use_hunter else {}
    hunter_calls = 0
    if use_hunter:
        if not hunter.is_configured():
            sys.exit("[backfill] --hunter given but HUNTER_API_KEY is not set (see .env.example).")
        left = hunter.requests_left()
        print(f"[backfill] Hunter.io enabled. Monthly searches remaining: "
              f"{left if left is not None else 'unknown'}. This run will make at most "
              f"{args.hunter_max} new calls.")

    ws = _ws()
    rows = ws.get_all_values()
    if len(rows) <= 1:
        sys.exit("[backfill] Sheet is empty.")

    header = [h.strip().lower() for h in rows[0]]
    col = {name: header.index(name) for name in header}
    for required in ("email", "company", "domain"):
        if required not in col:
            sys.exit(f"[backfill] Sheet missing '{required}' column.")

    def cval(row: list[str], key: str) -> str:
        i = col.get(key, -1)
        return row[i].strip() if 0 <= i < len(row) else ""

    updates: list[dict] = []
    filled = skipped_have = no_result = 0
    filled_by_hunter = 0
    considered = 0

    for sheet_row_idx, row in enumerate(rows[1:], start=2):  # 1-based, +header
        row_id = cval(row, "rowid")
        has_email = bool(cval(row, "email"))
        forced = row_id in force_ids
        if has_email and not forced:
            continue
        company_name = cval(row, "company")
        domain = cval(row, "domain")
        if not company_name and not domain:
            continue

        considered += 1
        if args.limit and considered > args.limit:
            considered -= 1
            break

        tag = ""
        lead = enrich(Company(name=company_name, website=domain), row_id=int(row_id or sheet_row_idx))
        first, last, email, title = lead.first_name, lead.last_name, lead.email, lead.title
        out_domain = lead.domain or domain

        # --- Hunter.io fallback -------------------------------------------------
        if not email and use_hunter and out_domain:
            key = out_domain.lower()
            hit = hunter_cache.get(key)
            if hit is None and hunter_calls < args.hunter_max:
                try:
                    contact = hunter.best_contact(key)
                    hunter_calls += 1
                    hit = contact or {}
                    hunter_cache[key] = hit
                    _save_cache(hunter_cache)
                except hunter.HunterError as exc:
                    print(f"  [hunter] stopping: {exc}")
                    use_hunter = False
                    hit = None
            if hit:
                if (hit.get("confidence") or 0) >= args.hunter_min_confidence:
                    email = hit.get("email", "")
                    first = first or hit.get("first_name", "")
                    last = last or hit.get("last_name", "")
                    title = title or hit.get("position", "")
                    tag = f"  [hunter c={hit.get('confidence')}]"
                else:
                    tag = f"  [hunter skipped: low confidence {hit.get('confidence')}]"

        if not email:
            no_result += 1
            print(f"  row {row_id or sheet_row_idx:>4} {company_name[:38]:38} -> (no email found){tag}")
            continue

        # Fill empty cells. For forced rows, also correct/clear stale values.
        candidates = (
            ("email", email), ("firstname", first), ("lastname", last),
            ("title", (title or "")[:80]), ("domain", out_domain),
        )
        changes: dict[str, str] = {}
        for k, value in candidates:
            if k not in col:
                continue
            current = cval(row, k)
            if forced and k in ("firstname", "lastname", "title"):
                if value != current:
                    changes[k] = value  # may be "" to clear a bad parse
            elif value and (forced or not current):
                changes[k] = value

        if not changes:
            skipped_have += 1
            continue

        for k, value in changes.items():
            updates.append({"range": rowcol_to_a1(sheet_row_idx, col[k] + 1), "values": [[value]]})
        filled += 1
        if tag.startswith("  [hunter c="):
            filled_by_hunter += 1
        who = f"  ({first} {last})".rstrip() if first else ""
        print(f"  row {row_id or sheet_row_idx:>4} {company_name[:38]:38} -> {email}{who}{tag}")

    print(
        f"\n[backfill] considered={considered} filled={filled} "
        f"(hunter={filled_by_hunter}) already-had-fields={skipped_have} "
        f"no-email-found={no_result} hunter-calls-made={hunter_calls}"
    )

    if not updates:
        print("[backfill] Nothing to write.")
        return
    if args.dry_run:
        print(f"[backfill] DRY RUN — would write {len(updates)} cell(s).")
        return

    for i in range(0, len(updates), 400):
        ws.batch_update(updates[i:i + 400], value_input_option="USER_ENTERED")
        time.sleep(1)
    print(f"[backfill] Wrote {len(updates)} cell(s) to \"{GOOGLE_SHEET_NAME}\".")


if __name__ == "__main__":
    main()
