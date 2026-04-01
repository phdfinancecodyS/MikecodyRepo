# Quiz MVP Implementation Contract

Date: 2026-03-20
Purpose: Single source of truth for MVP engineering implementation.

## Product Principles (Non-Negotiable)

1. Quiz is free.
2. Results are shown immediately after question 10 scoring.
3. Email/phone capture is optional and only shown after results render.
4. Crisis resources are visible on every result page.
5. No paid product is primary on critical results.
6. On critical, contact capture cannot appear before crisis actions.

## Scoring Contract

Question count:
- 10 questions
- Each question score: 0-3
- Total score range: 0-30

Primary score bands:
- 0-10: low_risk
- 11-20: moderate_risk
- 21-25: high_risk
- 26-30: critical

Override logic:
- If q5 score is 3: force critical
- If q5 score is 2: minimum high_risk

Required persistence fields:
- total_score
- risk_level
- answers_by_question
- selected_audience_bucket_ids
- primary_audience_bucket_id
- overlay_audience_bucket_ids
- utm_source
- utm_medium
- utm_campaign
- email_opt_in
- sms_opt_in
- timestamp

## Routing Contract

Screen order:
1. Landing page
2. Quiz intro
3. Questions 1-10 (one per screen)
4. Results page
5. Optional post-result contact capture
6. Product/resource actions

Flow constraints:
- Next disabled until option selected.
- Back button enabled.
- Save answer on each step.
- Progress bar visible.

Low/moderate add-on module:
- For low_risk and moderate_risk results, render post-result branch module from quiz/conversation-branch-flow.json.
- For high_risk and critical, keep crisis-first result flow and do not auto-render this module.

Topic matcher add-on module:
- Render post-quiz topic matcher from quiz/topic-matcher-flow.json using quiz/topic-catalog.json.
- Show for low_risk and moderate_risk by default.
- For high_risk, prepend crisis actions and then allow matcher.
- For critical, skip matcher and keep crisis-only flow.

Audience lens add-on module:
- Render optional audience-lens matcher from quiz/audience-bucket-flow.json after topic recommendations are computed.
- Show for low_risk and moderate_risk by default.
- For high_risk, prepend crisis actions and then allow audience-lens selection.
- For critical, skip audience-lens matcher and keep crisis-only flow.
- If multiple audience buckets are selected, require one primary audience bucket before final recommendation render.
- If no audience bucket is selected, default to general-mental-health lens.

## Result Page CTA Contract

Low risk:
- Message: you are managing fairly well right now
- CTA order:
  1) optional capture (copy of results)
  2) How to Help Guide
  3) Check On Me
  4) therapist directory

Moderate risk:
- Message: something real is going on, and support would help now
- CTA order:
  1) optional capture (next steps)
  2) Crisis Kit
  3) Check On Me
  4) therapist directory
  5) How to Help Guide

High risk:
- Message: you matter, and support is needed now
- CTA order:
  1) Call 988
  2) Text HOME to 741741
  3) therapist directory
  4) optional capture (send resources)
  5) Crisis Kit (secondary only)

Critical:
- Message: you are in crisis, get help right now
- CTA order:
  1) Call 988 now
  2) Text HOME to 741741
  3) Call 911
  4) optional capture (email crisis resources)
- Paid product placement: not primary, not above crisis actions

Global result-page rule:
- Crisis resources must remain visible even if user declines capture.

## Analytics Event Contract

Required event names:
- landing_page_view
- quiz_started
- quiz_question_answered
- quiz_completed
- result_viewed
- crisis_cta_clicked
- product_cta_clicked
- email_opt_in
- sms_opt_in

Minimum event payload:
- user/session id
- risk_level
- total_score
- question_id (for quiz_question_answered)
- primary_audience_bucket_id
- overlay_audience_bucket_ids
- utm_source
- utm_medium
- utm_campaign
- timestamp

## MVP QA Gate (Must Pass Before Launch)

1. Score and band mapping verified for all boundaries.
2. q5=3 always routes to critical.
3. q5=2 cannot route below high_risk.
4. Result appears before any capture prompt.
5. Critical page shows crisis actions before capture.
6. Crisis resources visible on every result level.
7. UTM values preserved from landing to persistence.
8. Mobile links work for 988 and 741741.
9. Audience lens defaults to general-mental-health when user skips it.
10. If multiple audience buckets are selected, one primary bucket is stored.
