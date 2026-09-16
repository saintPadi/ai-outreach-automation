"""
Turn outbox/drafts.json into .eml files (fallback when the Gmail connector
is unavailable). These are DRAFTS — nothing is sent.

    python .claude/skills/staffing-outreach/scripts/build_eml.py outbox/drafts.json

drafts.json is a list of objects:
    { "to", "to_name", "company", "subject", "body", "from_name", "from_email" }

Output: outbox/eml/<NN>_<slug>.eml  +  outbox/eml/index.md
"""

from __future__ import annotations

import json
import re
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]


def _slug(text: str, n: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:n] or "lead").strip("-")


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SKILL_DIR / "outbox" / "drafts.json"
    if not src.exists():
        sys.exit(f"[build_eml] Not found: {src}")

    drafts = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(drafts, list) or not drafts:
        sys.exit("[build_eml] drafts.json must be a non-empty JSON list.")

    out_dir = SKILL_DIR / "outbox" / "eml"
    out_dir.mkdir(parents=True, exist_ok=True)

    index_lines = ["# Outreach drafts (.eml)", "", "Review each, then send from your mail client. Nothing here has been sent.", ""]
    written = 0
    for i, d in enumerate(drafts, start=1):
        to = (d.get("to") or "").strip()
        if not to:
            index_lines.append(f"{i:02d}. SKIPPED (no address) — {d.get('company', '?')}")
            continue

        msg = EmailMessage()
        from_name = d.get("from_name", "").strip()
        from_email = d.get("from_email", "").strip()
        msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
        msg["To"] = f"{d.get('to_name','').strip()} <{to}>" if d.get("to_name") else to
        msg["Subject"] = d.get("subject", "").strip()
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        msg["X-Unsent"] = "1"  # Outlook: open as unsent draft
        msg.set_content(d.get("body", ""))

        fname = f"{i:02d}_{_slug(d.get('company', to))}.eml"
        (out_dir / fname).write_bytes(bytes(msg))
        index_lines.append(f"{i:02d}. {d.get('company','?')} — {to} — \"{msg['Subject']}\"  →  `{fname}`")
        written += 1

    (out_dir / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"[build_eml] Wrote {written} .eml file(s) to {out_dir}")
    print(f"[build_eml] Index: {out_dir / 'index.md'}")


if __name__ == "__main__":
    main()
