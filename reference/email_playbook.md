# Outreach email playbook

## Goal

A short, credible first-touch email to a potential **client company** (not a job
seeker). Outcome we want: a quick reply or a 15-minute call about their staffing
needs.

## Who the leads are

Rows come from municipal Business Directories (Brampton + Mississauga) filtered to
**manufacturing, wholesale, construction, transportation & warehousing, and
admin/support** employers with **20+ staff**. The `Employees` column tells you the
size band — reference it lightly if useful ("teams your size", "a 200-person
plant"), never quote it back verbatim. The `Phone` column is the business's main
line; only use it in the signature block, never imply you'll cold-call them.

## Structure (~90–150 words, 3 paragraphs)

1. **Opening (1–2 sentences)** — name the company and a plausible, honest reason
   for reaching out: the kind of labour they likely use (warehouse / production /
   drivers / general labour), their location in Southern Ontario, seasonal or
   shift-based hiring. No fabricated specifics ("I saw your press release…").
2. **Value (2–3 sentences)** — what Ready Konnect does, drawn only from
   `company.md`. Lead with the outcome that fits the prospect: fill roles fast,
   cut permanent staffing cost, scale up/down, 24/7 availability, recruiters who
   come from the trades.
3. **Call to action (1 sentence)** — one ask. A short call this week, or "reply
   and I'll send our rate sheet." Include the booking link if `sender.json` has
   one.

Then the **signature + CASL footer** (below).

## Greeting

- `FirstName` present → "Hi {FirstName},"
- No name → "Hi there," or "Hello,"

## Subject lines (rotate across the batch — don't reuse one line for everyone)

- Staffing support for {Company}?
- Warehouse & production staff, filled fast
- Cutting staffing overhead at {Company}
- {City}-area labour on 24-hour notice
- Skilled & general labour when you need it
- Quick question about {Company}'s staffing
- Forklift & DZ/AZ drivers, pre-screened
- Scaling your crew up (or down) this season

## Tone

Warm, direct, peer-to-peer B2B. Plain language. No hype stacking, no more than
one exclamation mark in the whole email, no "Dear Sir/Madam", no walls of text,
no em dashes (—): use a comma, a colon, or split into two sentences instead.
Contractions are good. Sound like a person who works in the industry, not a
template with fields swapped in: vary sentence rhythm and paragraph openers
from one draft to the next.

## Personalization inputs available per lead

- `Company` — use in the opening and subject.
- `Title` — if it's an operations / plant / HR / owner role, address their world
  (throughput, turnover, overtime, coverage). If blank, stay general.
- `Domain` — infer sector only if obvious (e.g. "metals", "logistics",
  "foods"); otherwise ignore. Never assert something you're guessing.
- `City` is not a column — only reference a city if it's clearly in the company
  name; otherwise say "the GTA" or "Southern Ontario".

## CASL footer (required on every email)

Canada's Anti-Spam Legislation applies. Every draft must end with:

```
{from_name}, {title}
Ready Konnect Inc. | Staffing Solutions, Southern Ontario
{phone} | {from_email} | www.readykonnect.ca

You're receiving this at your business address regarding staffing services.
Reply "unsubscribe" and I won't contact you again.
```

Keep that opt-out line exactly — it's the required unsubscribe mechanism.
Do not email anyone who previously replied "unsubscribe" (they'll be in
`state/processed.json` if you mark them; when in doubt, ask the user).

`{mailing_address}` was removed from this template at the user's request.
CASL requires a valid mailing address (or a readily available way to obtain
one) in every commercial email — omitting it is a compliance gap, not a
neutral style choice. If `sender.json`'s `mailing_address` is ever filled
back in, add it as its own line under the phone/email/website line.

## Do not

- Promise specific fill times, headcounts, pay rates, or savings percentages.
- Name other clients or use testimonials (none are provided).
- Attach anything or paste large rate tables into a cold email.
- Send. This skill drafts only.
