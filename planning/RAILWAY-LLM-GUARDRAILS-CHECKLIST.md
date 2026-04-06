# Railway Deployment Checklist: Full LLM With Safety Guardrails

Date: 2026-04-06
Owner: Ask Anyway
Goal: Deploy from GitHub to Railway while enforcing safety, crisis routing, scope limits, and token controls.

## 1. Railway Setup From GitHub

1. Create a new Railway project from GitHub.
2. Select the correct repository and branch.
3. Set the service root directory to the app that should run in Railway.
4. Confirm build command and start command for that service.
5. Deploy once to a preview environment before production.

Pass criteria:
- Service builds successfully.
- Service starts and responds on health endpoint.
- No missing environment variable errors.

## 2. Required Environment Variables

Set these in Railway project variables for each environment.

Core backend:
- SUPABASE_URL
- SUPABASE_SERVICE_KEY
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- STRIPE_PRICE_IDS

LLM provider and policy controls:
- CCE_LLM_PROVIDER
- CCE_LLM_MODEL
- CCE_LLM_API_KEY
- CCE_LLM_TIMEOUT_MS
- CCE_LLM_DAILY_TOKEN_CAP
- CCE_LLM_DAILY_REQUEST_CAP
- CCE_LLM_MAX_INPUT_TOKENS
- CCE_LLM_MAX_OUTPUT_TOKENS
- CCE_LLM_RETRY_LIMIT
- CCE_LLM_CRITICAL_OUTPUT_MAX_TOKENS
- CCE_LLM_HIGH_OUTPUT_MAX_TOKENS
- CCE_LLM_MODERATE_OUTPUT_MAX_TOKENS
- CCE_LLM_LOW_OUTPUT_MAX_TOKENS

Safety and crisis behavior:
- CCE_SAFETY_MODE
- CCE_REQUIRE_CRISIS_BLOCK
- CCE_BLOCK_PAID_CTA_ON_CRITICAL
- CCE_FAIL_CLOSED_ON_GUARDRAIL_REJECT

Recommended values for first rollout:
- CCE_LLM_TIMEOUT_MS: 8000
- CCE_LLM_RETRY_LIMIT: 1
- CCE_LLM_MAX_INPUT_TOKENS: 2500
- CCE_LLM_MAX_OUTPUT_TOKENS: 700
- CCE_LLM_CRITICAL_OUTPUT_MAX_TOKENS: 350
- CCE_LLM_HIGH_OUTPUT_MAX_TOKENS: 500
- CCE_LLM_MODERATE_OUTPUT_MAX_TOKENS: 650
- CCE_LLM_LOW_OUTPUT_MAX_TOKENS: 700
- CCE_REQUIRE_CRISIS_BLOCK: true
- CCE_BLOCK_PAID_CTA_ON_CRITICAL: true
- CCE_FAIL_CLOSED_ON_GUARDRAIL_REJECT: true

## 3. Non Negotiable Safety Contract

These must always be enforced in server logic before any LLM response reaches users.

1. Risk scoring remains deterministic.
2. Q5 equals 3 always forces critical.
3. Q5 equals 2 sets minimum high risk.
4. Critical path always shows crisis resources first.
5. Critical path cannot show paid products above crisis actions.
6. Contact capture cannot appear before crisis actions on critical path.
7. If guardrail validation fails, return safe fallback response.

## 4. Modality and Scope Matrix

Use this as the policy layer above prompt templates.

Critical:
- Allowed modality: short supportive text only.
- Not allowed: sales language before crisis actions.
- Output style: brief, direct, safety first.
- Output cap: 350 tokens.

High risk:
- Allowed modality: supportive coaching text.
- Allowed offers: only after safety section is present.
- Output style: practical next steps, no diagnosis.
- Output cap: 500 tokens.

Moderate risk:
- Allowed modality: educational plus coaching text.
- Offers: allowed after safety footer.
- Output style: warm, direct, actionable.
- Output cap: 650 tokens.

Low risk:
- Allowed modality: educational and planning text.
- Offers: normal ordering with safety footer.
- Output style: concise, practical, encouraging.
- Output cap: 700 tokens.

Global bans for all bands:
- No method details for self harm.
- No diagnosis language.
- No treatment claims.
- No coercive urgency.

## 5. Runtime Guardrail Pipeline

1. Input validation:
- Validate request schema.
- Resolve risk band and overrides first.
- Inject crisis policy context.

2. LLM call envelope:
- Apply per band token caps.
- Apply timeout and retry rules.
- Add request id for traceability.

3. Output validation:
- Confirm crisis block exists when required.
- Confirm no paid CTA above crisis section for critical.
- Confirm banned content filters pass.
- Confirm token and length limits pass.

4. Failure behavior:
- One strict retry with shorter prompt.
- If still failing, return deterministic safe fallback.

## 6. Budget and Throttle Plan

Stage A: Internal smoke
- Daily org cap: 250000 tokens
- Per user cap: 10 responses per day

Stage B: Private beta
- Daily org cap: 2000000 tokens
- Per user cap: 20 responses per day

Stage C: Soft launch
- Daily org cap: 10000000 tokens
- Per user cap: 30 responses per day

Automatic throttle rule:
- At 80 percent of daily cap, reduce max output tokens by 30 percent.
- At 95 percent of daily cap, switch to compact response mode plus deterministic fallback for non essential routes.

## 7. Observability and Alerts

Track:
- Token input and output by route and risk band
- Guardrail rejection count by reason
- Retry rate and fallback rate
- Timeout and error rates
- Median and P95 latency

Alert immediately on:
- Missing crisis block
- Critical path ordering violation
- Daily cap over 90 percent
- Spike in fallback rate

## 8. Release Gates

Do not move to next stage unless all are true for 7 days:
1. Guardrail violation rate under 0.5 percent
2. Timeout plus error rate under 1 percent
3. P95 latency within target
4. Daily spend inside budget band
5. No critical path safety regressions

## 9. Manual Test Script Before Production

1. Submit low risk quiz flow and confirm expected recommendation behavior.
2. Submit moderate and high flows and confirm safety plus offer ordering.
3. Submit critical flow with Q5 equals 3 and verify crisis first behavior.
4. Verify no contact capture appears before crisis actions on critical.
5. Verify webhook and purchase flow still works.
6. Verify analytics events continue to persist.
7. Verify rollback can be triggered quickly.

## 10. Handoff Instructions For Teammate

1. Deploy from GitHub into Railway preview first.
2. Add all required variables in Railway, not from local machine.
3. Validate health and one test flow per risk band.
4. Promote to production only after release gates pass.
5. Keep guardrail switches enabled in all environments.
