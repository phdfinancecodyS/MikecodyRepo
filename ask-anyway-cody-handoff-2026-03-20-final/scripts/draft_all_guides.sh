#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")/.."

profile_for_title() {
  local t="$1"
  local low="${t:l}"
  if [[ "$low" == *suicid* || "$low" == *crisis* || "$low" == *hopeless* ]]; then
    echo "crisis"
  elif [[ "$low" == *anger* || "$low" == *blow* || "$low" == *short-fuse* || "$low" == *shutdown* || "$low" == *shut*down* ]]; then
    echo "reactivity"
  elif [[ "$low" == *sleep* || "$low" == *night* || "$low" == *3am* || "$low" == *caffeine* ]]; then
    echo "sleep"
  elif [[ "$low" == *relationship* || "$low" == *family* || "$low" == *parent* || "$low" == *communication* || "$low" == *repair* || "$low" == *dating* || "$low" == *co-parenting* ]]; then
    echo "relationship"
  elif [[ "$low" == *moral* || "$low" == *guilt* || "$low" == *shame* || "$low" == *faith* || "$low" == *villain* || "$low" == *betrayed* ]]; then
    echo "moral"
  elif [[ "$low" == *sex* || "$low" == *intimacy* || "$low" == *touch* || "$low" == *desire* || "$low" == *porn* || "$low" == *body*image* ]]; then
    echo "intimacy"
  elif [[ "$low" == *pain* || "$low" == *tbi* || "$low" == *headache* || "$low" == *vision* || "$low" == *balance* || "$low" == *panic* ]]; then
    echo "body"
  elif [[ "$low" == *substance* || "$low" == *alcohol* || "$low" == *pill* || "$low" == *dopamine* || "$low" == *habit* || "$low" == *scroll* || "$low" == *eating* ]]; then
    echo "habit"
  elif [[ "$low" == *work* || "$low" == *identity* || "$low" == *money* || "$low" == *underemployed* || "$low" == *transition* || "$low" == *leave* || "$low" == *investigation* || "$low" == *court* ]]; then
    echo "work"
  elif [[ "$low" == *grief* || "$low" == *survivor* ]]; then
    echo "grief"
  else
    echo "general"
  fi
}

fill_file() {
  local f="$1"
  local title id type source batch priority profile
  title=$(sed -n '1s/^# //p' "$f")
  id=$(awk -F': ' '/^Guide ID:/{print $2; exit}' "$f")
  type=$(awk -F': ' '/^Guide type:/{print $2; exit}' "$f")
  source=$(awk -F': ' '/^Source:/{print $2; exit}' "$f")
  batch=$(awk -F': ' '/^Batch:/{print $2; exit}' "$f")
  priority=$(awk -F': ' '/^Priority:/{print $2; exit}' "$f")
  profile=$(profile_for_title "$title")

  local happening_a happening_b happening_c step1 step2 step3 say1 say2 say3 avoid1 avoid2 avoid3

  case "$profile" in
    crisis)
      happening_a="This topic sits in the safety-first lane: when pain gets loud, your first job is connection and immediate support."
      happening_b="People often wait for certainty before acting. In this lane, you act early and keep someone connected."
      happening_c="You are not trying to be perfect. You are trying to keep the next hour safer."
      step1="Name what you are noticing with direct and calm language."
      step2="Ask one clear safety question and stay present for the answer."
      step3="Connect to crisis support now (988/741741/911 as needed) and do not leave them isolated."
      say1="I care about you, and I want to ask something directly so we can keep you safe."
      say2="Are you thinking about suicide right now?"
      say3="We can take one step together right now. I am staying with you while we reach support."
      avoid1="Waiting for the perfect wording while risk rises."
      avoid2="Debating whether pain is serious enough before offering support."
      avoid3="Putting paid resources ahead of immediate safety actions."
      ;;
    reactivity)
      happening_a="This pattern usually starts in your body before it shows up in your words."
      happening_b="When intensity jumps fast, your best move is early interruption, not long explanation."
      happening_c="Repair is part of the plan, not a side note."
      step1="Catch the earliest body cue and call a short reset."
      step2="Use one grounding action for 60-90 seconds."
      step3="Return with one repair sentence and one clear next step."
      say1="I am getting overloaded and I do not want to make this worse."
      say2="Give me a short reset and I will come back ready to continue."
      say3="I care about this conversation, and I am ready to restart better."
      avoid1="Explaining behavior before owning impact."
      avoid2="Taking distance with no return time."
      avoid3="Skipping repair because things feel awkward."
      ;;
    sleep)
      happening_a="Sleep disruption turns up reactivity, worry, and decision fatigue fast."
      happening_b="Most people chase a perfect night. The better move is a repeatable wind-down pattern."
      happening_c="Small consistency beats occasional heroic fixes."
      step1="Pick one fixed anchor time for wind-down or wake-up."
      step2="Run a 20-minute downshift routine without screens."
      step3="Write tomorrow's first task so your brain has a landing point."
      say1="I am running on low sleep and I need to simplify tonight."
      say2="I am doing my reset routine now so tomorrow is easier."
      say3="I am not fixing everything tonight; I am building one better night."
      avoid1="Using late-night scrolling as your off switch."
      avoid2="Changing your whole routine every day."
      avoid3="Ignoring caffeine timing when sleep is unstable."
      ;;
    relationship)
      happening_a="Relationship strain grows when stress responses replace clear communication."
      happening_b="You do not need perfect communication, just safer starts and cleaner repairs."
      happening_c="One better conversation can change the next week."
      step1="Name the goal of the conversation before details."
      step2="Use one direct feeling-and-need sentence."
      step3="Close with one concrete agreement and follow-up time."
      say1="I care about us, and I want to handle this without making it worse."
      say2="Can we slow this down and stay on one issue at a time?"
      say3="Here is one thing I can own and one thing I am asking for."
      avoid1="Bringing five old fights into one conversation."
      avoid2="Trying to win instead of repair."
      avoid3="Ending without a clear next step."
      ;;
    moral)
      happening_a="Moral pain often sounds like: I should have done more, I failed, or I am not who I thought I was."
      happening_b="Shame gets stronger in silence and softer in structured reflection."
      happening_c="The goal is not erasing pain; it is rebuilding integrity one action at a time."
      step1="Name the event and the value that feels violated."
      step2="Separate facts from self-condemnation story lines."
      step3="Choose one repair action aligned with your values this week."
      say1="I am carrying something heavy and I need to say it out loud."
      say2="Part of me is stuck in blame, and I am trying to move toward repair."
      say3="I want to take one concrete step that matches who I want to be now."
      avoid1="Treating shame as proof instead of a signal."
      avoid2="Using isolation as your main coping strategy."
      avoid3="Expecting one conversation to erase deep pain."
      ;;
    intimacy)
      happening_a="Intimacy strain often rises when stress, fear, and pressure replace safety and clarity."
      happening_b="Connection returns faster when you reduce pressure and increase honesty."
      happening_c="You are building trust in small reps, not one big reset."
      step1="Name pressure early and agree on a no-pressure reset."
      step2="Use one clear consent/check-in question."
      step3="Pick one low-stakes closeness action for today."
      say1="I want us to feel close without pressure right now."
      say2="Can we check in on what feels safe and what does not today?"
      say3="I am committed to rebuilding trust one step at a time."
      avoid1="Pushing intensity when safety is low."
      avoid2="Using silence instead of direct check-ins."
      avoid3="Assuming your partner can read your needs."
      ;;
    body)
      happening_a="Body-based symptoms can feel scary and make decision-making harder in the moment."
      happening_b="A short protocol helps you move from alarm to control."
      happening_c="You are aiming for steady function, not instant perfection."
      step1="Name the symptom pattern and rate intensity from 1-10."
      step2="Run one grounding or pacing protocol for 90 seconds."
      step3="Choose one practical adjustment for the next hour."
      say1="My system is spiking right now, and I am using my reset plan."
      say2="I need two minutes to stabilize and then I can continue."
      say3="I am not in danger right now; I am in a surge and taking control steps."
      avoid1="Ignoring early symptoms until they become overwhelming."
      avoid2="Making big decisions during peak body alarm."
      avoid3="Skipping follow-up care when patterns repeat."
      ;;
    habit)
      happening_a="Habit loops feel automatic because cue, relief, and repeat happen fast."
      happening_b="The break point is usually right after the trigger, before the old routine starts."
      happening_c="Replacement routines work better than pure willpower."
      step1="Name the cue and where it usually hits."
      step2="Insert one replacement action for 5-10 minutes."
      step3="Track one win and one miss without shame."
      say1="I can feel the old loop starting, so I am switching routines now."
      say2="I am choosing a smaller, safer action for the next ten minutes."
      say3="Progress is reps, not perfection."
      avoid1="Trying to quit a loop with no replacement routine."
      avoid2="Using shame as motivation."
      avoid3="Treating one slip like total failure."
      ;;
    work)
      happening_a="Work and identity stress often blends pressure, uncertainty, and loss of control."
      happening_b="Clarity improves when you separate what is urgent, what is important, and what can wait."
      happening_c="Small structure beats constant rumination."
      step1="Write the top three stress points in plain words."
      step2="Pick one controllable action for today."
      step3="Set one boundary that protects energy this week."
      say1="I am under strain and I want to handle this with a clear plan."
      say2="Here is the one piece I can control today."
      say3="I am setting this boundary so I can stay functional and reliable."
      avoid1="Treating every problem like it must be solved tonight."
      avoid2="Avoiding the issue until it gets bigger."
      avoid3="Trying to carry this alone without one support check-in."
      ;;
    grief)
      happening_a="Grief can hit in waves: numb one hour, raw the next."
      happening_b="You do not have to process everything at once to move forward."
      happening_c="Steady rituals and honest check-ins reduce isolation."
      step1="Name what hurts most right now in one sentence."
      step2="Do one grounding ritual that reconnects you to the present."
      step3="Reach one safe person and ask for specific support."
      say1="I am having a heavy grief wave right now and I need support."
      say2="I do not need fixing, I need company and steadiness."
      say3="Can you check on me again tomorrow?"
      avoid1="Expecting yourself to be over it on a timeline."
      avoid2="Isolating because you do not want to burden others."
      avoid3="Judging your grief response as weakness."
      ;;
    *)
      happening_a="This topic gets easier when you catch it earlier and work one small step at a time."
      happening_b="You do not need a perfect plan to start."
      happening_c="Consistent reps beat one-time intensity."
      step1="Name the pattern clearly."
      step2="Run a short reset."
      step3="Take one useful next action."
      say1="I am slowing this down so I can respond better."
      say2="I care about this, and I am taking one step now."
      say3="I will follow up after I reset."
      avoid1="Doing nothing while waiting to feel perfect."
      avoid2="Trying to fix everything in one conversation."
      avoid3="Skipping follow-up after the first step."
      ;;
  esac

  cat > "$f" <<EOF
# $title

Status: draft_v1_complete
Guide ID: $id
Guide type: $type
Source: $source
Batch: $batch
Priority: $priority

## What This Helps With

This guide helps with "$title" when it keeps showing up in your week and you need a practical response.
Use this when you want clear words and a clear next step, not theory.

## What Is Happening

$happening_a
$happening_b
$happening_c

## What To Do Now

1. $step1
2. $step2
3. $step3

## What To Say

- $say1
- $say2
- $say3

## Common Mistakes To Avoid

- $avoid1
- $avoid2
- $avoid3

## 24-Hour Action Plan

- Immediate action: choose one step above and do it in the next hour.
- One support action: send one check-in text to someone safe.
- One follow-up action: write what worked and what to change tomorrow.

## Worksheet 1: Pattern Finder

Goal: Identify triggers, context, and early warning signs.

Prompts:
- In the last 7 days, when did "$title" show up most?
- What happened right before it started?
- What did I notice first in my body?
- What thought pattern showed up at the same time?
- Earliest warning sign I can catch next time:

## Worksheet 2: Action Builder

Goal: Turn insight into one script and one 24-hour commitment.

Prompts:
- Script I will use word-for-word next time:
- My 90-second reset routine:
- One action I will take in the next 24 hours:
- The person I will check in with:
- How I will measure success by tomorrow night:
EOF
}

for f in content/topic-guides/splits/*.md content/topic-guides/new-topics/*.md; do
  fill_file "$f"
done

echo "draft_v1_complete=$(grep -R "Status: draft_v1_complete" -n content/topic-guides/splits content/topic-guides/new-topics | wc -l | tr -d ' ')"
echo "queued=$(grep -R "Status: queued for build" -n content/topic-guides/splits content/topic-guides/new-topics | wc -l | tr -d ' ')"
