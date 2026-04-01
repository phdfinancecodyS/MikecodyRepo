# Audience Slant Backbone

Date: 2026-03-20
Status: Locked backbone for audience-specific guide generation and quiz routing.

## Purpose

Add audience resonance to all 79 guides without creating combination-specific content chaos.
The system supports multi-select audience matching while keeping one primary guide version and optional secondary overlays.

## Final Bucket List (17)

1. Christian
2. Military / Veteran
3. First Responder
4. General Mental Health
5. LGBTQ+
6. High Stress Jobs
7. Single Parent
8. Healthcare Workers
9. Educators
10. Social Workers / Counselors
11. BIPOC / Racial Trauma
12. Faith Beyond Christian
13. Neurodivergent
14. Grief / Loss
15. Chronic Illness / Chronic Pain
16. Young Adults / Gen Z
17. Addiction / Recovery

## TikTok Priority Recommendation

### Primary Buckets

Use these as the strongest front-door hooks because people quickly self-identify with them on TikTok:

1. Christian
2. Military / Veteran
3. First Responder
4. LGBTQ+
5. Neurodivergent
6. Single Parent
7. Addiction / Recovery
8. Grief / Loss
9. Healthcare Workers
10. Educators
11. Young Adults / Gen Z

### Overlay Buckets

Use these as strong personalization overlays, but not always as the first quiz-facing hook:

1. High Stress Jobs
2. Social Workers / Counselors
3. BIPOC / Racial Trauma
4. Faith Beyond Christian
5. Chronic Illness / Chronic Pain

### Fallback Bucket

1. General Mental Health

## Multi-Select Logic

Users can select multiple buckets.
System behavior:

1. Select up to 2 identity/community lenses.
2. Select up to 2 life-context lenses.
3. If multiple are selected, user chooses which one should lead.
4. One primary audience bucket determines the main guide version.
5. Up to 2 additional selections function as overlays for recommendation notes, examples, scripts, and follow-up messaging.
6. If no bucket is selected, default to General Mental Health.

## Quiz Question Recommendation

### Question 1

Prompt:
Which lens would make this feel most like it was written for you?

Rules:
- multi-select max 2
- optional
- identity/community focused

Options:
- Christian
- Military / Veteran
- First Responder
- LGBTQ+
- Neurodivergent
- BIPOC / Racial Trauma
- Young Adult / Gen Z
- Keep it general

### Question 2

Prompt:
What part of your life is shaping this most right now?

Rules:
- multi-select max 2
- optional
- role/circumstance focused

Options:
- Single Parent
- Healthcare Worker
- Educator
- Social Worker / Counselor
- High Stress Job
- Addiction / Recovery
- Grief / Loss
- Chronic Illness / Chronic Pain
- Faith Beyond Christian
- Keep it general

### Question 3

Prompt:
If we tailor this for you, which one should lead?

Rules:
- only display if user selected 2+ audience options across Q1/Q2
- single select
- options dynamically populated from prior selections

## Routing Rules

1. Prefer specific occupational buckets over broad ones.
   Example: Healthcare Workers beats High Stress Jobs.
2. Prefer identity bucket when user explicitly selects it as primary.
3. If Grief / Loss or Addiction / Recovery is selected, keep safety and relapse-aware language visible.
4. If Christian or Faith Beyond Christian is selected, keep tone invitational and practical, not preachy.
5. If LGBTQ+ or BIPOC / Racial Trauma is selected, include safety, belonging, and minority-stress-aware framing where relevant.
6. If no specific bucket is selected, serve General Mental Health.

## File Structure

Base guides remain source of truth:
- content/topic-guides/chapters/
- content/topic-guides/splits/
- content/topic-guides/new-topics/

Audience-specific guide versions generate into:
- content/topic-guides/audience-slants/<bucket-id>/<base-guide-filename>.md

Examples:
- content/topic-guides/audience-slants/christian/split-01-blow-up-recovery.md
- content/topic-guides/audience-slants/first-responder/ch-04-anger-and-short-fuse-days.md
- content/topic-guides/audience-slants/addiction-recovery/new-15-eating-patterns-under-stress-reset-guide.md

## Metadata Requirements For Audience Variants

Each generated guide should include:
- Status: draft_v1_complete
- Guide ID
- Guide type
- Source
- Batch
- Priority
- Audience Bucket
- Audience Tier (primary / overlay / fallback)
- Base Guide Path

## Build Counts

- Base guides: 79
- Audience buckets: 17
- Total audience-specific variants: 1343

## Drafting Rule

Each audience variant should preserve:
- core safety guidance
- same guide structure
- same worksheet count (2)
- same main user problem

Each audience variant should adapt:
- framing
- context examples
- scripts
- support references
- worksheet prompts where relevant
