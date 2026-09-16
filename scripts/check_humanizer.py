"""
Lint outbox/drafts.json for AI-cold-email "tells" before creating real drafts.

Deterministic checks only (no LLM, no network, no new dependencies) — this
catches the mechanical stuff (em dashes, stock phrases, run-on sentences,
repeated subject lines). The actual humanizing rewrite is done by Claude
inline per reference/email_playbook.md / SKILL.md step 6a; this script is
the verification gate before step 8 (creating drafts).

    python .claude/skills/staffing-outreach/scripts/check_humanizer.py
    python .claude/skills/staffing-outreach/scripts/check_humanizer.py outbox/drafts.json

Exit code 0 = clean, 1 = at least one draft has findings (or the file is
missing/invalid).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]

EM_DASH = "—"

# Short, high-signal list of stock AI-cold-email phrases. Matched case-insensitively.
STOCK_PHRASES = [
    "i hope this email finds you",
    "i hope this finds you well",
    "in today's fast-paced",
    "in today's competitive",
    "furthermore,",
    "moreover,",
    "in conclusion,",
    "unlock the potential",
    "unlock your",
    "take your business to the next level",
    "streamline your operations",
    "look no further",
    "in this day and age",
    "i wanted to reach out",
    "i am writing to",
]

RUN_ON_WORD_LIMIT = 30
RUN_ON_MAX_ALLOWED = 2  # more than this many long sentences in one body is a finding
SUBJECT_REUSE_THRESHOLD = 4  # more than this many identical subjects across the batch


def _sentences(text: str) -> list[str]:
    # Rough sentence split — good enough for a run-on proxy, not real NLP.
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _paragraphs(body: str) -> list[str]:
    return [p.strip() for p in body.split("\n\n") if p.strip()]


def check_draft(draft: dict) -> list[str]:
    """Return a list of human-readable findings for one draft (empty = clean)."""
    findings: list[str] = []
    body = draft.get("body") or ""

    if EM_DASH in body:
        findings.append("contains an em dash (—)")

    lowered = body.lower()
    hit_phrases = [p for p in STOCK_PHRASES if p in lowered]
    if hit_phrases:
        findings.append(f"stock AI phrase(s): {', '.join(hit_phrases)}")

    long_sentences = 0
    for para in _paragraphs(body):
        for sent in _sentences(para):
            if len(sent.split()) > RUN_ON_WORD_LIMIT:
                long_sentences += 1
    if long_sentences > RUN_ON_MAX_ALLOWED:
        findings.append(
            f"{long_sentences} run-on sentence(s) over {RUN_ON_WORD_LIMIT} words "
            f"(allowed: {RUN_ON_MAX_ALLOWED})"
        )

    openers = [para.split()[0].lower().strip(",.:;") for para in _paragraphs(body) if para.split()]
    dupe_openers = {w for w in openers if openers.count(w) > 1}
    if dupe_openers:
        findings.append(f"repeated paragraph opener(s): {', '.join(sorted(dupe_openers))}")

    return findings


def check_batch(drafts: list[dict]) -> list[str]:
    """Batch-level findings (e.g. subject line reuse) that apply across drafts."""
    findings: list[str] = []
    subjects = [d.get("subject", "").strip() for d in drafts if d.get("subject", "").strip()]
    counts: dict[str, int] = {}
    for s in subjects:
        counts[s] = counts.get(s, 0) + 1
    overused = {s: n for s, n in counts.items() if n > SUBJECT_REUSE_THRESHOLD}
    for subject, n in overused.items():
        findings.append(
            f'subject "{subject}" reused {n} times (threshold: {SUBJECT_REUSE_THRESHOLD})'
        )
    return findings


def main() -> None:
    ap = argparse.ArgumentParser(description="Check outbox/drafts.json for AI-sounding tells.")
    ap.add_argument(
        "path",
        nargs="?",
        default=str(SKILL_DIR / "outbox" / "drafts.json"),
        help="Path to drafts.json (default: outbox/drafts.json).",
    )
    args = ap.parse_args()

    src = Path(args.path)
    if not src.exists():
        sys.exit(f"[check_humanizer] Not found: {src}")

    try:
        drafts = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"[check_humanizer] Invalid JSON in {src}: {exc}")

    if not isinstance(drafts, list) or not drafts:
        sys.exit(f"[check_humanizer] {src} must be a non-empty JSON list.")

    total_findings = 0
    for i, draft in enumerate(drafts, start=1):
        company = draft.get("company", "?")
        findings = check_draft(draft)
        if findings:
            total_findings += len(findings)
            print(f"[check_humanizer] #{i:02d} {company}: {len(findings)} finding(s)")
            for f in findings:
                print(f"[check_humanizer]     - {f}")

    batch_findings = check_batch(drafts)
    if batch_findings:
        total_findings += len(batch_findings)
        print(f"[check_humanizer] batch: {len(batch_findings)} finding(s)")
        for f in batch_findings:
            print(f"[check_humanizer]     - {f}")

    print(f"[check_humanizer] {len(drafts)} draft(s) checked, {total_findings} finding(s) total")

    if total_findings:
        print("[check_humanizer] FAIL: revise flagged bodies and re-run before step 8.")
        sys.exit(1)

    print("[check_humanizer] OK, clean: proceed to step 8.")


if __name__ == "__main__":
    main()
