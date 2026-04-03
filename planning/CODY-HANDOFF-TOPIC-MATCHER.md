# Cody Handoff: Topic Matcher Funnel (Plug-and-Play)

Date: 2026-03-20
Primary files:
- quiz/topic-matcher-flow.json
- quiz/topic-catalog.json

## What This Adds

After quiz completion, users can take a short "What Topic Do I Need?" matcher.
The matcher recommends topic-specific products using the existing pricing model.

## Why This Matters

- You now have 47 loaded topic chapters (48 if/when chapter 48 is added).
- Quiz gives risk level; matcher gives product-topic fit.
- This bridges awareness to purchase without forcing one generic offer.

## Entry Logic

Show matcher for:
- low_risk
- moderate_risk
- high_risk (after crisis resources block)

Skip matcher for:
- critical (crisis flow only)

## Runtime Inputs

From quiz session:
- risk_level
- total_score
- utm_source
- utm_medium
- utm_campaign

From matcher files:
- topic catalog from quiz/topic-catalog.json
- question flow + pricing profile from quiz/topic-matcher-flow.json

## Output Contract

Return payload for recommendation page:
- selected_domain
- recommended_topic_ids (top 3)
- recommended_offer_type (guide|kit|sms|bundle)
- recommendation_reason_lines

## Pricing Profile Handling

There are two pricing profiles in the flow file:
1. hub_spoke_default ($2 guide, $5 kit, $5/mo SMS, $10 bundle)
2. legacy_quiz_launch ($10 guide, $5 kit, $4.99/mo SMS)

Implementation rule:
- Read activePricingProfile from flow JSON.
- Render prices dynamically from that profile.
- Do not hardcode prices in component code.

## Recommendation Rendering

Card per topic recommendation (3 cards):
- topic title
- short "why this matches" line
- domain label
- primary CTA from mapped offer

Offer block below cards:
- single recommended offer based on tm_q3 offerBias
- optional secondary offer link

## High-Risk Safety Rule

If risk_level == high_risk:
- prepend crisis actions (988/741741/911) before matcher content
- keep crisis actions visible while scrolling matcher results

## Analytics Events

Fire events listed in topic-matcher-flow.json:
- topic_matcher_started
- topic_matcher_question_answered
- topic_matcher_completed
- topic_recommendation_viewed
- topic_offer_clicked
- topic_offer_purchased

## QA Checklist

1. Matcher appears only on allowed risk levels.
2. Critical users skip matcher and remain crisis-first.
3. Exactly 3 recommended topics returned.
4. Offer prices follow activePricingProfile.
5. UTM and risk payload attached to matcher events.
6. Topic IDs in results exist in quiz/topic-catalog.json.
