# LLM Launch Plan That Does Not Burn Tokens

## Goal
Use LLM only where it creates real value, while hard-capping token usage so traffic spikes cannot drain quota.

## 1) Tiered launch profiles

### pilot
- `CCE_TRAFFIC_TIER=pilot`
- `CCE_LLM_ENABLED_STEPS_PILOT=negative_probe,deepening,goal_clarify`
- `CCE_LLM_RESPONDER_MAX_TOKENS=80`
- Use for early quality tuning and transcript review.

### core
- `CCE_TRAFFIC_TIER=core`
- `CCE_LLM_ENABLED_STEPS_CORE=deepening`
- `CCE_LLM_RESPONDER_MAX_TOKENS=64`
- Default production profile. LLM only on the highest-value turn.

### peak
- `CCE_TRAFFIC_TIER=peak`
- `CCE_LLM_ENABLED_STEPS_PEAK=`
- `CCE_LLM_RESPONDER_MAX_TOKENS=48`
- Template-only mode during heavy traffic or quota pressure.

## 2) Provider failover chain
- `CCE_LLM_PROVIDER_CHAIN=groq,openai,anthropic`
- Per-provider keys and models:
  - `CCE_LLM_API_KEY_GROQ`, `CCE_LLM_MODEL_GROQ`
  - `CCE_LLM_API_KEY_OPENAI`, `CCE_LLM_MODEL_OPENAI`
  - `CCE_LLM_API_KEY_ANTHROPIC`, `CCE_LLM_MODEL_ANTHROPIC`
- On 429/rate-limit, responder cools down that provider and tries the next.

## 3) Hard token budgets (new)
Budget guards in responder enforce absolute caps before any provider call.

- `CCE_LLM_BUDGET_TOKENS_PER_MINUTE`
- `CCE_LLM_BUDGET_TOKENS_PER_HOUR`
- `CCE_LLM_BUDGET_TOKENS_PER_DAY`
- `CCE_LLM_BUDGET_BLOCK_COOLDOWN_S` (default 180)

Behavior:
- If projected call would exceed any cap, LLM call is blocked.
- Flow falls back to deterministic templates.
- Budget block is logged and cooldown prevents hot-loop retries.

## 4) Recommended starting values
For national launch with free-tier Groq plus fallback providers:

- `CCE_LLM_BUDGET_TOKENS_PER_MINUTE=6000`
- `CCE_LLM_BUDGET_TOKENS_PER_HOUR=180000`
- `CCE_LLM_BUDGET_TOKENS_PER_DAY=1200000`
- `CCE_LLM_BUDGET_BLOCK_COOLDOWN_S=180`
- `CCE_LLM_GUIDANCE_MODE=compact`
- `CCE_LLM_RESPONDER_MAX_TOKENS=64`
- `CCE_TRAFFIC_TIER=core`

Then tune up or down using observed usage from `/admin/llm-usage`.

## 5) Operational runbook
1. Watch `/admin/llm-usage` every 15 to 30 minutes during launch windows.
2. Watch `/admin/llm-headroom` for warning levels and recommended actions.
3. Use `/admin/llm-alerts` for monitoring integrations that only need actionable alerts.
4. Send alert texts with `POST /admin/llm-alerts/sms` for on-call notifications.
5. If hourly usage is over 75 percent of budget, switch to `peak`.
6. If quality drops or conversion drops materially, temporarily switch to `pilot` for a sampled cohort only.
7. Keep crisis and high-risk safety pathways deterministic and always available.

## 9) SMS on-call alerts (Twilio)

Set environment variables:

- `CCE_ALERT_SMS_ENABLED=1`
- `CCE_ALERT_SMS_TO=+1...`
- `CCE_ALERT_SMS_DEDUP_SECONDS=900`
- `CCE_ALERT_SMS_AUTOSEND_ENABLED=1`
- `CCE_ALERT_SMS_INTERVAL_HOURS=48`
- `CCE_ALERT_SMS_AUTOSEND_MIN_LEVEL=warning`
- `TWILIO_ACCOUNT_SID=...`
- `TWILIO_AUTH_TOKEN=...`
- `TWILIO_FROM_NUMBER=+1...`

Trigger alert text manually or from cron/automation:

```bash
curl -s -X POST "http://localhost:8000/admin/llm-alerts/sms?min_level=warning" \
  -H "Authorization: Bearer $CCE_ADMIN_KEY"
```

Notes:
- SMS is only sent when `/admin/llm-alerts` currently has alerts.
- Duplicate alert bodies are suppressed during dedupe window unless `force=true`.
- When autosend is enabled, the backend checks every 48 hours by default and sends only when alerts exist.

## 6) Fast emergency levers
- Disable LLM immediately: set `CCE_LLM_ENABLED_STEPS=`
- Reduce response size: lower `CCE_LLM_RESPONDER_MAX_TOKENS`
- Force hard low-cost mode: set `CCE_TRAFFIC_TIER=peak`

## 7) Validation checklist
- Verify `/admin/llm-usage` totals increase during LLM calls.
- Verify `/admin/llm-headroom` shows `watch` or `warning` as limits are approached.
- Verify `/admin/llm-alerts` returns `has_alerts=true` when thresholds are exceeded.
- Verify cache hits appear with source `cache`.
- Simulate 429 and confirm fallback provider is used.
- Simulate budget limit and confirm template fallback with no hard failure.

## 8) Persistent teaching model
The provider model itself is not being fine-tuned in production. Instead, persistent teaching is handled by a versioned instruction file loaded into the responder system prompt at startup.

- File: `docs/LLM-PERSISTENT-GUIDANCE.md`
- Env: `CCE_LLM_PERSISTENT_GUIDANCE_FILE`

Workflow:
1. Add one concrete instruction to the guidance file.
2. Restart backend so responder reloads prompt context.
3. Validate quality on sampled transcripts.
4. Keep, revise, or remove the instruction based on outcomes.
