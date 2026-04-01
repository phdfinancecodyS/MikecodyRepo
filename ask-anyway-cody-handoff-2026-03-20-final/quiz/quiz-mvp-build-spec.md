# QUIZ MVP BUILD SPEC

## Goal
Ship a mobile-first quiz that is fast, private, non-diagnostic, and routes users to the right next step in under 3 minutes.

---

## MVP SCOPE

Launch with:
- landing page
- 10-question quiz
- 4 results states
- post-results contact capture
- optional SMS opt-in
- Crisis Kit offer
- crisis resources on every result screen

Defer to v2:
- full personalization by audience type
- branching questions
- retake logic
- advanced analytics dashboards
- all multi-email nurture tracks beyond first send

---

## QUIZ UX

### Entry
User lands from TikTok, IG, Reddit, or affiliate link.

Screen order:
1. Landing page
2. Quiz intro screen
3. Questions 1-10
4. Results page
5. Optional contact capture
6. Product / resource actions

### Quiz intro copy
Headline:
- Take a quick check-in

Body:
- This quiz takes about 2 minutes.
- It is not a diagnosis.
- Based on your answers, we will show you the support that best fits where you are right now.
- You will see your result right away.

Button:
- Start the quiz

### Contact capture principle
- never gate the result behind email or phone collection
- show the result first, then offer a copy of the result and next steps
- contact info should feel optional and useful, not like a trade
- critical users should see crisis resources before any capture prompt

### Progress behavior
- one question per screen
- visible progress bar
- back button allowed
- next button disabled until response selected
- save answer on every step

### UX constraints
- mobile-first layout
- thumb-friendly answer buttons
- no giant paragraphs on question screens
- calm visual tone, not medical or alarmist

---

## REQUIRED SYSTEM LOGIC

### Score rules
- total possible score: 0-30
- q5 score 3 -> critical immediately
- q5 score 2 -> high risk minimum

### Result levels
- 0-10 -> low_risk
- 11-20 -> moderate_risk
- 21-25 -> high_risk
- 26-30 -> critical

### Required persistence
Save:
- total score
- risk level
- answers by question
- utm source/medium/campaign
- email opt-in status
- SMS opt-in status
- timestamp

---

## RESULT PAGE REQUIREMENTS

### Low risk
Primary message:
- you are managing fairly well right now

CTAs:
- How to Help Guide
- Check On Me
- therapist directory

CTA order:
- optional email capture for a copy of results
- How to Help Guide
- Check On Me
- therapist directory

### Moderate risk
Primary message:
- something real is going on, and support would help now

CTAs:
- Crisis Kit
- Check On Me
- therapist directory
 - How to Help Guide

CTA order:
- optional email capture for next steps
- Crisis Kit
- Check On Me
- therapist directory
- How to Help Guide


### High risk
Primary message:
- you matter, and support is needed now

CTAs:
- Call 988
- text 741741
- therapist directory
 - Crisis Kit as secondary support tool

CTA order:
- Call 988
- Text HOME to 741741
- therapist directory
- optional email capture to send steps and resources
- Crisis Kit as secondary support tool

### Critical
Primary message:
- you are in crisis, get help right now

CTAs:
- Call 988 now
- text HOME to 741741
- call 911

Rule:
- no paid product should be the primary CTA on critical
- no contact capture should appear before crisis resources on critical

Canonical behavior for all result pages:
- always show result first
- never gate results behind email or phone
- keep crisis resources visible on every result level

---

## POST-RESULTS CONTACT CAPTURE COPY

### Low risk
Headline:
- Want a copy of your results?

Body:
- We can send you your result and a few support tools to keep on hand.
- Optional, and only if that would be useful.

Fields:
- email
- optional phone for weekly check-ins

Buttons:
- Send me my results
- No thanks

### Moderate risk
Headline:
- Want these next steps sent to you?

Body:
- If it helps, we can send you your result, a few practical next steps, and the tools that match where you are right now.
- Optional. You can also keep going without this.

Fields:
- email
- optional phone for weekly check-ins

Buttons:
- Send me my next steps
- No thanks

### High risk
Headline:
- Want these resources in one place?

Body:
- We can send you the steps on this page so you do not have to remember them later.
- Optional. If you need help right now, use the crisis options above first.

Fields:
- email
- optional phone for gentle check-ins

Buttons:
- Send me these resources
- Continue without sending

### Critical
Headline:
- Want a copy of these crisis resources?

Body:
- If it would help, we can send you this list so you have it with you.
- Only do this after you have used the crisis support options above.

Fields:
- email only

Buttons:
- Email me this list
- Continue

---

## DESIGN GUIDANCE

- use simple, calm colors
- use clear contrast for crisis buttons
- avoid red until high-risk/critical results
- keep text readable at phone size
- use 1 clear action per screen

---

## ANALYTICS EVENTS

Track at minimum:
- landing_page_view
- quiz_started
- quiz_question_answered
- quiz_completed
- result_viewed
- crisis_cta_clicked
- product_cta_clicked
- email_opt_in
- sms_opt_in

---

## QA CHECKLIST

Before launch, verify:
- all 10 questions render correctly
- score totals are correct
- q5 override works
- each score range lands on correct result page
- 988 links work on mobile
- SMS link works on mobile
- result page loads quickly
- email capture saves correctly
- UTMs are preserved end to end
- product buttons only appear where intended

---

## FASTEST GO-LIVE VERSION

If Cody needs the smallest possible build:
- skip pre-quiz email capture entirely
- collect email after results only
- send one immediate email only
- offer Crisis Kit only
- keep therapist directory as outbound link
- launch with organic TikTok traffic only

That version is enough to validate demand quickly.
