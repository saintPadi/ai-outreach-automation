# AI Outreach Automation

A [Claude Code](https://claude.com/claude-code) **skill** that turns a lead list into personalized, legally-compliant cold-outreach emails — governed end to end by a structured prompt system rather than a one-off prompt. 

This repo is less "a script that calls an LLM" and more a small case study in **prompt engineering as a discipline**: a reusable prompt library, explicit guardrails, and an automated QA pass that checks the model's own output before it's allowed to ship.

## Why this is here

Most AI demos stop at "the prompt works once." The interesting engineering problem is what happens at draft #24 of a batch, after the model has settled into a repetitive cadence, or when a legal requirement (Canada's Anti-Spam Legislation) has to be satisfied in *every single output*, not just the one you eyeballed. This project's answer to that is three layered artifacts:

1. **A reusable prompt library** (`reference/email_playbook.md`) — not a single prompt, but a versioned set of rules: structure, tone, personalization inputs, subject-line rotation, and a CASL-compliant footer template. `SKILL.md` is the orchestrating system prompt that tells Claude when and how to apply it.
2. **Guardrails baked into the prompt, not bolted on after** — explicit "do not fabricate," "do not promise unverified numbers," and "never send, draft only" rules live in the prompt library itself, so the model can't accidentally reason its way around them.
3. **Automated AI governance** (`scripts/check_humanizer.py`) — a deterministic lint pass that runs *after* generation and flags AI "tells" (em dashes, stock cold-email phrases, run-on sentences, repeated subject lines, repeated paragraph openers) before a batch goes to a human for final review. It was added after a real review round caught the model drifting into templated phrasing, then the fix was codified as a standing rule instead of a one-time correction — the kind of iteration loop that separates a demo prompt from a production one.

## How the skill works

```
Leads Sheet (Google Sheets, from the scraper)
        │
        ▼
scripts/fetch_leads.py  ──▶  outbox/leads.json
        │
        ▼
Claude drafts each email using reference/email_playbook.md + reference/company.md
        │  (personalization, tone rules, CASL footer, subject rotation)
        ▼
outbox/drafts.json
        │
        ▼
scripts/check_humanizer.py  ──▶  pass/fail report (em dashes, stock phrases, run-ons, subject reuse)
        │  fail → revise and re-run · pass → proceed
        ▼
Gmail draft (via connector) or scripts/build_eml.py  ──▶  .eml files
```

Nothing is ever sent automatically — every draft lands in a review queue (Gmail Drafts or local `.eml` files) for a human to approve.

## What's in here

| Path | Role |
|---|---|
| `SKILL.md` | The orchestrating prompt: procedure, guardrails, and when to invoke each script |
| `reference/email_playbook.md` | The reusable prompt library — structure, tone rules, personalization inputs, CASL footer template |
| `reference/company.md` | Ground-truth facts the model is restricted to (prevents fabricated claims) |
| `reference/sender.example.json` | Sender identity config — copy to `sender.json` and fill in your own |
| `scripts/fetch_leads.py` | Pulls leads from the Google Sheet into `outbox/leads.json` |
| `scripts/check_humanizer.py` | Post-generation AI-governance lint (stdlib only — no dependencies) |
| `scripts/build_eml.py` | Fallback local `.eml` export when no Gmail connector is available |
| `scripts/backfill_contacts.py` | Optional contact enrichment (website scraping + Hunter.io fallback) |
| `outbox/example_leads.json` | Fabricated example data showing the lead schema (real leads/drafts are gitignored) |

## Setup

```bash
pip install -r requirements.txt   # requests, beautifulsoup4, gspread, google-auth, python-dotenv, tqdm
cp .env.example .env              # Google Sheets + optional Hunter.io config
cp reference/sender.example.json reference/sender.json   # fill in your real identity
```

This is a Claude Code **skill**, not a standalone CLI — the drafting step (`SKILL.md`'s procedure) runs inside a Claude Code session, which is what gives it governed, guardrail-checked output rather than a raw API call. `fetch_leads.py`, `check_humanizer.py`, and `build_eml.py` can run standalone for the mechanical steps.

## Guardrails, by design

- **Draft-only.** The skill's instructions explicitly forbid a send action, even if asked.
- **No fabricated recipients.** Company-only rows without a verified email are flagged "needs an address," never guessed.
- **No unverified claims.** Every value proposition must trace back to `company.md` — no invented client names, stats, or guarantees.
- **CASL compliance is structural, not optional.** The footer template (sender identity + mailing address + opt-out mechanism) is part of the prompt library itself, not a step a busy run can skip.

Built with [Claude Code](https://claude.com/claude-code).
