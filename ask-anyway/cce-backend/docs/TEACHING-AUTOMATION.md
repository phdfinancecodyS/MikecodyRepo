# Teaching Automation

## What is automated now
- The responder auto-loads persistent guidance from `docs/LLM-PERSISTENT-GUIDANCE.md`.
- It auto-reloads the file when changed, on a timed interval.
- No backend restart is required for guidance updates.

## Config
- `CCE_LLM_PERSISTENT_GUIDANCE_FILE`
- `CCE_LLM_PERSISTENT_GUIDANCE_RELOAD_S` (default 15 seconds)

## Safe automation loop (recommended)
1. Review conversation samples and tag failure patterns.
2. Add one concrete teaching bullet to `docs/LLM-PERSISTENT-GUIDANCE.md`.
3. Wait one reload interval, then test sample prompts.
4. Keep or revert the bullet based on measured outcomes.

## Do not automate without approval
- Do not auto-write guidance directly from raw user conversations.
- Do not let the model rewrite its own core policy instructions.
- Keep a human approval gate before guidance changes land.

## Why this is safer than self-training
- Fast updates with version control.
- Easy rollback with git.
- No model drift from unreviewed data.
- Keeps safety constraints explicit and stable.
