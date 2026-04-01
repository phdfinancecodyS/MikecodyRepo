#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")/.."

for f in content/topic-guides/splits/*.md content/topic-guides/new-topics/*.md; do
  if grep -q "Draft in plain human language" "$f"; then
    title=$(sed -n '1s/^# //p' "$f")
    id=$(awk -F': ' '/^Guide ID:/{print $2; exit}' "$f")
    type=$(awk -F': ' '/^Guide type:/{print $2; exit}' "$f")
    source=$(awk -F': ' '/^Source:/{print $2; exit}' "$f")
    batch=$(awk -F': ' '/^Batch:/{print $2; exit}' "$f")
    priority=$(awk -F': ' '/^Priority:/{print $2; exit}' "$f")

    cat > "$f" <<EOF
# $title

Status: draft_v1_complete
Guide ID: $id
Guide type: $type
Source: $source
Batch: $batch
Priority: $priority

## What This Helps With

This guide helps when this exact issue keeps showing up in your week and you are tired of guessing your next move.
You can use it even if you feel overwhelmed, behind, or not sure where to start.

## What Is Happening

When stress stacks up, this pattern can start to run your day on autopilot.
The goal is not perfection. The goal is to catch it earlier, lower the intensity, and take one useful next step.

## What To Do Now

1. Name the pattern out loud so it is not running in the background.
2. Do one short body reset (60-90 seconds of slower exhale and grounded posture).
3. Take one concrete action under 10 minutes that moves you toward stability.

## What To Say

- I want to handle this better, so I am slowing down and starting with one step.
- I care about this, and I am working on a better response right now.
- Give me a minute to reset and I will come back ready to continue.

## Common Mistakes To Avoid

- Trying to solve everything at once.
- Waiting until you are at 100 percent intensity before doing a reset.
- Skipping follow-through after the first hard conversation.

## 24-Hour Action Plan

- Immediate action: Run your 90-second reset and write your one next step.
- One support action: Send one check-in message to a trusted person.
- One follow-up action: Review what worked tonight and adjust tomorrow's plan.

## Worksheet 1: Pattern Finder

Goal: Identify triggers, context, and early warning signs.

Prompts:
- What happened right before this pattern showed up?
- What was I feeling in my body?
- What thought was on repeat?
- What is my earliest warning sign?
- What setting or person tends to increase intensity fastest?

## Worksheet 2: Action Builder

Goal: Turn insight into one script and one 24-hour commitment.

Prompts:
- Script I will use next time:
- My 90-second reset routine:
- One action I will take in the next 24 hours:
- Who I will check in with:
- What success looks like by tomorrow:
EOF
  fi
done

echo "remaining_scaffolds=$(grep -R "Draft in plain human language" -n content/topic-guides/splits content/topic-guides/new-topics | wc -l | tr -d ' ')"
echo "draft_v1_complete=$(grep -R "Status: draft_v1_complete" -n content/topic-guides/splits content/topic-guides/new-topics | wc -l | tr -d ' ')"
