# API Route Specs

Date: 2026-03-20
Status: Locked route contract for backend implementation

## Purpose

Define the HTTP endpoints Cody should implement for the quiz, recommendation engine, checkout, and fulfillment flow.

## Shared Rules

- All endpoints return JSON.
- All timestamps use ISO 8601 UTC.
- All ids are UUIDs unless otherwise noted.
- Critical-risk users never receive paid offers before crisis resources.
- Validation errors return HTTP 400.
- Not found returns HTTP 404.
- Unexpected backend failures return HTTP 500.

## Endpoint 1: POST /api/quiz/score

### Purpose
Score quiz answers, assign risk level, persist quiz session.

### Request Body
```json
{
  "lead": {
    "id": "optional-existing-lead-uuid",
    "email": "optional@example.com",
    "phone": "optional-phone",
    "firstName": "optional"
  },
  "answersByQuestion": {
    "q1": 2,
    "q2": 1,
    "q3": 0,
    "q4": 3,
    "q5": 1,
    "q6": 2,
    "q7": 1,
    "q8": 0,
    "q9": 1,
    "q10": 2
  },
  "quizVersion": "2026-03-20",
  "landingPath": "/quiz",
  "utm": {
    "source": "tiktok",
    "medium": "organic",
    "campaign": "launch",
    "content": "video-03",
    "term": ""
  }
}
```

### Response Body
```json
{
  "leadId": "uuid",
  "quizSessionId": "uuid",
  "totalScore": 13,
  "riskLevel": "moderate_risk",
  "overrideTriggered": false,
  "resultScreenId": "moderate_risk",
  "allowTopicMatcher": true,
  "allowAudienceMatcher": true,
  "showCrisisResources": true
}
```

### Validation Rules
- Require exactly 10 answers.
- Each answer must be integer `0-3`.
- `q5 = 3` forces `critical`.
- `q5 = 2` forces minimum `high_risk`.

## Endpoint 2: POST /api/quiz/topic-match

### Purpose
Run the topic matcher and persist the match session.

### Request Body
```json
{
  "quizSessionId": "uuid",
  "matcherVersion": "1",
  "answers": {
    "tm_q1": "calm_nervous_system",
    "tm_q2": "cant_sleep_overthink",
    "tm_q3": ["step_by_step_plan", "weekly_accountability"]
  }
}
```

### Response Body
```json
{
  "topicMatchSessionId": "uuid",
  "matchedDomain": "sleep_body_pain_substances",
  "recommendedGuideIds": ["split-10", "ch-13", "new-14"],
  "recommendedOfferType": "kit",
  "whyMatched": [
    "User prioritized calm mind/body support",
    "User selected wired and tired sleep pattern",
    "User asked for a step-by-step plan"
  ]
}
```

### Validation Rules
- `quizSessionId` must exist.
- Topic matcher answers must match `quiz/topic-matcher-flow.json`.
- Maximum `tm_q3` selections: 2.

## Endpoint 3: POST /api/quiz/audience-match

### Purpose
Resolve primary and overlay audience buckets and persist audience session.

### Request Body
```json
{
  "quizSessionId": "uuid",
  "matcherVersion": "1",
  "identityBucketIds": ["first-responder"],
  "contextBucketIds": ["single-parent", "grief-loss"],
  "primaryBucketId": "first-responder"
}
```

### Response Body
```json
{
  "audienceMatchSessionId": "uuid",
  "selectedBucketIds": ["first-responder", "single-parent", "grief-loss"],
  "primaryBucketId": "first-responder",
  "overlayBucketIds": ["single-parent", "grief-loss"],
  "fallbackUsed": false
}
```

### Validation Rules
- Max 2 identity bucket selections.
- Max 2 context bucket selections.
- If total selected buckets > 1, `primaryBucketId` is required.
- If no buckets selected, fallback to `general-mental-health`.

## Endpoint 4: POST /api/quiz/recommendation

### Purpose
Resolve final guide, audience-specific asset path, and offer lane.

### Request Body
```json
{
  "quizSessionId": "uuid",
  "topicMatchSessionId": "uuid",
  "audienceMatchSessionId": "uuid"
}
```

### Response Body
```json
{
  "guideRecommendationId": "uuid",
  "baseGuideId": "split-10",
  "baseGuideTitle": "3am Wake Loop Reset",
  "audienceBucketId": "first-responder",
  "audienceVariantPath": "content/topic-guides/audience-slants/first-responder/split-10-3am-wake-loop-reset.md",
  "primaryOfferId": "kit",
  "secondaryOfferId": "sms",
  "bundleRole": "regulation_stack",
  "showCrisisResources": true,
  "whyMatched": {
    "riskLevel": "moderate_risk",
    "topic": ["wired and tired", "sleep disruption"],
    "audience": ["first-responder"],
    "offer": ["step-by-step plan"]
  }
}
```

### Validation Rules
- If `riskLevel = critical`, no topic or audience matcher should be required.
- If audience match is missing, use `general-mental-health` asset path.
- Final offer must comply with `quiz/recommendation-routing-config.json`.

## Endpoint 5: POST /api/checkout/session

### Purpose
Create Stripe checkout session and persist purchase intent context.

### Request Body
```json
{
  "leadId": "uuid",
  "quizSessionId": "uuid",
  "guideRecommendationId": "uuid",
  "productId": "kit",
  "guideId": "split-10",
  "audienceBucketId": "first-responder",
  "successUrl": "https://example.com/checkout/success",
  "cancelUrl": "https://example.com/checkout/cancel"
}
```

### Response Body
```json
{
  "purchaseIntentId": "uuid",
  "stripeCheckoutUrl": "https://checkout.stripe.com/..."
}
```

### Validation Rules
- Product id must exist in `quiz/product-catalog.json`.
- If `productId = free_crisis_resources`, do not create Stripe session.
- Require `guideRecommendationId` for paid offers.

## Endpoint 6: POST /api/webhooks/stripe

### Purpose
Handle successful checkout and trigger fulfillment.

### Behavior
- Verify Stripe signature.
- Resolve purchase by `stripe_session_id` or `stripe_payment_intent_id`.
- Mark `purchases.fulfillment_status = processing`.
- Create fulfillment events for:
  - guide delivery
  - kit delivery
  - sms enrollment
  - bundle delivery
- Mark purchase as `fulfilled` or `failed`.

### Expected Side Effects
- Insert into `fulfillment_events`.
- Trigger email delivery if digital asset is attached.
- Trigger SMS enrollment only if opt-in and compliance checks pass.

## Endpoint 7: POST /api/analytics/event

### Purpose
Persist analytics events that are not already captured by core workflow writes.

### Request Body
```json
{
  "sessionId": "uuid",
  "eventName": "product_cta_clicked",
  "payload": {
    "riskLevel": "moderate_risk",
    "guideId": "split-10",
    "productId": "kit",
    "primaryAudienceBucketId": "first-responder"
  },
  "timestamp": "2026-03-20T15:30:00Z"
}
```

### Response Body
```json
{
  "accepted": true
}
```

## Implementation Order

1. `/api/quiz/score`
2. `/api/quiz/topic-match`
3. `/api/quiz/audience-match`
4. `/api/quiz/recommendation`
5. `/api/checkout/session`
6. `/api/webhooks/stripe`
7. `/api/analytics/event`

## Source Files To Respect

- `quiz/topic-matcher-flow.json`
- `quiz/audience-bucket-flow.json`
- `quiz/recommendation-routing-config.json`
- `quiz/base-guide-catalog.json`
- `quiz/product-catalog.json`
- `planning/GUIDE-OFFER-MAPPING.csv`
- `planning/AUDIENCE-SLANT-MANIFEST.csv`
