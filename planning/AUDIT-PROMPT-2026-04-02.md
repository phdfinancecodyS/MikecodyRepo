# Ask Anyway Audit Prompt (2026-04-02)

Use this prompt to run a full implementation and safety audit for this workspace.

## Prompt

You are auditing the Ask Anyway workspace for production readiness.

Audit scope:
1. API correctness for the 7 required endpoints in web/api and web/app/api wrappers.
2. Quiz safety contract compliance (scoring bands, Q5 overrides, critical handling order).
3. Frontend build and type integrity in web/.
4. Content integrity and safety checks via scripts/full_workspace_audit.py.
5. Docs alignment: identify stale TODO wording that conflicts with implemented code.

Execute these commands exactly:
1. `export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && cd /Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health/web && npm run build`
2. `cd /Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health && /Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health/.venv/bin/python scripts/full_workspace_audit.py`

Then produce a report with this format:
- `Result:` pass or fail
- `Critical Findings:` list only blocking issues
- `Warnings:` non-blocking risks
- `Info:` notable non-actionable observations
- `Verified Paths:` files/routes that were verified
- `Next Actions:` exact follow-up tasks

Pass criteria:
- Next.js build succeeds.
- Workspace audit returns 0 critical and 0 warnings.
- No contradictions between docs and implemented route status.

If any criterion fails, mark `Result: fail` and include exact failing command output excerpt.
