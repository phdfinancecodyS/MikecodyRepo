# Cody Handoff: Plug-and-Play Conversation Branches

Date: 2026-03-20
Primary file: quiz/conversation-branch-flow.json

## Goal

Add a post-result script branch module for low and moderate risk users.

This module should:
- show 2 teaser conversation starters
- ask what happened after they used one
- branch to exact follow-up scripts
- keep crisis pathways immediately available
- offer optional capture for full scripts/check-in plan

## Where It Hooks In

Attach to results page only when:
- risk_level == low_risk OR moderate_risk

Do not auto-show for:
- high_risk
- critical

For high/critical, keep existing crisis-first results behavior.

## UI Contract

Entry card:
- title: Try one direct line
- show both teaser starters
- single question: What happened when you asked?
- 3 buttons:
  1) They said yes
  2) They denied it or got defensive
  3) They changed the subject or avoided

Branch cards:
- render section headings + lines exactly from JSON
- render primary action buttons in defined order
- render optional capture block after primary actions

## Safety Contract

For branch_affirmative:
- Always render 988/741741/911 buttons first.
- No paid CTA above crisis actions.
- No capture prompt above crisis actions.

For all branches:
- Keep a persistent "Need urgent help now?" mini-footer with 988/741741.

## Event Wiring

Emit events from JSON analytics.events using these triggers:
- script_tease_viewed: entry card visible
- script_branch_selected: user selects one of 3 outcomes
- script_branch_viewed: branch screen displayed
- script_copy_saved: save button tapped
- script_capture_started: user taps email/text full scripts
- script_capture_submitted: capture form submitted
- crisis_cta_clicked: 988/741741/911 tapped

Required payload keys:
- risk_level
- branch_id
- selected_option_id
- utm_source
- utm_medium
- utm_campaign
- timestamp

## Persistence Keys

Add these optional fields to post-result session record:
- script_branch_selected
- script_capture_channel (email|sms|none)
- script_capture_submitted (boolean)
- crisis_cta_clicked_from_branch (boolean)

## Fast Build Steps

1. Parse quiz/conversation-branch-flow.json at app boot.
2. Add branch module component on low/moderate results page.
3. Wire button actions to existing click-tracking.
4. Reuse existing capture modal/form for email/SMS.
5. Apply safety ordering guard in UI renderer for branch_affirmative.
6. Ship behind feature flag: enable_conversation_branch_module.

## QA Checklist

1. Module only appears for low/moderate results.
2. All 3 branch buttons route correctly.
3. Branch affirmative always shows crisis actions first.
4. Capture prompt appears after primary actions.
5. Events fire with required payload fields.
6. Mobile tap targets are thumb-friendly.
7. Copy matches JSON exactly.
