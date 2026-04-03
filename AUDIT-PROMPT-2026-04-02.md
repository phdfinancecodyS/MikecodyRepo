# Ask Anyway Audit Prompt (2026-04-02)

Use this prompt to run a full implementation and safety audit for this repository.

## Prompt

You are auditing the Ask Anyway repository for production readiness.

Audit scope:
1. API correctness for the CCE backend and deployed chat flow integration.
2. Quiz safety contract compliance (scoring bands, Q5 overrides, critical handling order).
3. Conversation safety handling for crisis and critical override language.
4. Content integrity and safety checks via scripts/full_workspace_audit.py in the parent workspace.
5. Docs alignment: flag stale TODO wording that conflicts with implemented code.

Execute these commands:
1. `/Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health/.venv/bin/python /Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health/scripts/full_workspace_audit.py`
2. `cd /Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health/ask-anyway && git status --short`

Then report using:
- Result: pass or fail
- Critical Findings
- Warnings
- Info
- Verified Paths
- Next Actions

Pass criteria:
- Workspace audit returns 0 CRITICAL and 0 WARNING.
- Crisis handling and recommendation wiring are implemented in cce-backend and ask-anyway-deploy.
- No contradictory TODO claims in active docs for changed flows.
