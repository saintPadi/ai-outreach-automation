---
name: staffing-outreach
description: >-
  Draft personalized cold-outreach emails for Ready Konnect Inc. (a Southern
  Ontario staffing agency) to potential client companies pulled from the
  "Leads Sheet" Google Sheet. Generates one draft per lead, creates it as a
  Gmail draft via the Gmail connector when available, and otherwise writes
  .eml files locally. Draft-only — it never sends. Use when the user wants to
  email prospects / potential clients about the staffing agency, generate
  outreach drafts, or "continue the staffing outreach process".
---

# Staffing Outreach — Ready Konnect Inc.

Generate **draft** outreach emails to prospective client companies. This skill
**never sends email.** It produces Gmail drafts (via the `claude.ai Gmail`
connector) or local `.eml` files for the user to review and send themselves.

## Inputs

- **Leads**: the `Leads Sheet` Google Sheet (same sheet the leads scraper writes
  to). Columns: `RowId | FirstName | LastName | Email | Company | Title | Domain`.
- **Company facts**: `reference/company.md` — do not invent claims beyond this.
- **Sender identity**: `reference/sender.json` — the user must fill this in once.
  If any required field is still a `FILL_ME` placeholder, stop and ask the user
  for it before drafting.
- **Playbook**: `reference/email_playbook.md` — subject lines, structure,
  personalization rules, and CASL compliance requirements.

## Procedure

1. **Check sender identity.** Read `reference/sender.json`. If it is missing or
   any required field (`from_name`, `from_email`, `title`, `phone`) is
   `FILL_ME`, ask the user to provide those and stop.

2. **(Optional) Backfill missing contacts.** The sheet often has rows with a
   domain but no email. To fill them in place (the scraper's exporter dedupes
   by domain and will not add emails to existing rows):

   ```bash
   # free website scraping only
   python .claude/skills/staffing-outreach/scripts/backfill_contacts.py --dry-run
   python .claude/skills/staffing-outreach/scripts/backfill_contacts.py

   # add Hunter.io fallback (needs HUNTER_API_KEY in .env; free plan ~25/month)
   python .claude/skills/staffing-outreach/scripts/backfill_contacts.py --hunter --hunter-max 20
   ```

   Website scraping yields little (dead domains, bot-blocking, JS contact
   forms) — expect mostly generic `info@` addresses. Hunter.io adds named
   contacts but is quota-limited; calls are cached in
   `state/hunter_cache.json` and capped by `--hunter-max`. Use `--include-rows
   36` to re-enrich a specific mis-parsed row.

4. **Fetch leads.** From the project root (`c:\Users\Padib\Downloads\Skills`):

   ```bash
   python .claude/skills/staffing-outreach/scripts/fetch_leads.py --limit 25
   ```

   Writes `outbox/leads.json`. By default only rows **with an email** are
   included. Flags:
   - `--limit N` — cap number of leads (default: all).
   - `--include-company-only` — also include rows with no email (you will need
     to note these as "needs an address" — do not guess addresses).
   - `--out PATH` — override output path.

5. **Skip already-processed leads.** Read `state/processed.json` (a list of
   lowercased emails already drafted in past runs). Exclude those unless the
   user explicitly asks to redo them.

6. **Draft one email per remaining lead.** Follow `reference/email_playbook.md`:
   - Personalize the opening to the lead's company (industry, city, role type
     they likely staff for) using the `Company`, `Title`, and `Domain` fields.
     Keep personalization honest and non-creepy — no fake "I saw your recent…".
   - If `FirstName` is present, greet by first name; otherwise use a neutral
     greeting ("Hi there," / "Hello,").
   - Pull the value proposition and services **only** from `reference/company.md`.
   - Keep it to ~90–150 words, 3 short paragraphs, one clear call to action.
   - Include the CASL-required footer (sender identity block + how to opt out)
     from the playbook.
   - Vary subject lines across the batch (see playbook list).

7. **Humanize the drafts.** Before saving, do an inline rewrite pass over
   every drafted body:
   - Remove every em dash (`—`). Rewrite each one as two sentences, a comma,
     or a colon, whichever reads most naturally in context — don't just
     swap it for a hyphen.
   - Avoid stock AI-cold-email phrases ("I hope this email finds you", "In
     today's fast-paced...", "Furthermore,", "Moreover,", "unlock your
     potential", etc.).
   - Vary sentence rhythm and paragraph openers across the batch — don't let
     every email start its second paragraph with "Ready Konnect provides..."
     or every email lean on the same sentence structure. It should read like
     a person wrote each one, not like a template with fields swapped in.
   - Keep contractions.
   - Do **not** change any factual claim from `reference/company.md` while
     doing this — this is a style pass only, not a content rewrite.

8. **Write drafts to a review file.** Save all drafts to
   `outbox/drafts.json` as a list of objects:
   `{ "to", "to_name", "company", "subject", "body", "from_name", "from_email" }`.
   Then run the humanizer check as a gate before moving on:

   ```bash
   python .claude/skills/staffing-outreach/scripts/check_humanizer.py
   ```

   It flags em dashes, stock AI phrases, run-on sentences, and overused
   subject lines, and exits non-zero if anything is flagged. If it reports
   findings, revise the flagged bodies (per step 7) and re-run it until it's
   clean. Then show the user a numbered summary (recipient, company,
   subject) and 1–2 full sample bodies. Ask them to review.

9. **Create the drafts (only after the user says to proceed):**
   - **Preferred — Gmail connector:** if `claude.ai Gmail` connector tools are
     available, create one Gmail draft per entry (to, subject, body, from the
     sender address). Do **not** send. Report how many drafts were created and
     tell the user they're in their Gmail Drafts folder.
   - **Fallback — local .eml:** if the Gmail connector is not authorized, run:

     ```bash
     python .claude/skills/staffing-outreach/scripts/build_eml.py outbox/drafts.json
     ```

     This writes `outbox/eml/*.eml` (openable in any mail client) plus
     `outbox/eml/index.md`. Tell the user the connector wasn't available and
     point them at that folder.

10. **Update state.** Append every drafted lead's lowercased email to
    `state/processed.json` so re-runs don't duplicate.

## Guardrails

- Draft-only. Never call a send action, even if asked — direct the user to
  review and send from Gmail themselves.
- Never fabricate recipient email addresses. Company-only rows are listed as
  "needs an address", nothing more.
- Never claim capabilities, client names, stats, or guarantees that are not in
  `reference/company.md`.
- Keep batches modest (default 25). Warn the user that large volumes of
  near-identical cold email can hurt sender reputation and CASL standing.
