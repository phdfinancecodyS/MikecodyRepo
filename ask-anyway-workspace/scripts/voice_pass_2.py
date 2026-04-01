#!/usr/bin/env python3
"""
Voice pass 2: Replace boilerplate openers, 24-hour action plans,
worksheet prompts, and add disclaimer — all 79 topics across all files.
"""
import os, glob, re

ROOTS = [
    "content/topic-guides/audience-slants",
    "content/topic-guides/chapters",
    "content/topic-guides/splits",
    "content/topic-guides/new-topics",
]

# ---------------------------------------------------------------------------
# 1) OPENER HOOKS — replace the boilerplate "This guide helps with X when it
#    keeps showing up..." with a conversational, topic-specific hook.
#    Key = exact title from the # header line.
# ---------------------------------------------------------------------------
OPENER_HOOKS = {
    "Always On: Your High-Alert Brain":
        "If your brain won't stop scanning for danger — even when you're safe on your own couch — this one's for you. Not theory. Just what to actually do about it.",
    "Hypervigilance at Home":
        "You made it home, but your body didn't get the memo. If you're still on high alert in your own living room, here's what's happening and what to do about it.",
    "Anger and Short-Fuse Days":
        "When your fuse is short and everything sets you off — that's not a character flaw. It's your nervous system running hot. Here's how to catch it before it catches you.",
    "Depression and Numbness":
        "When everything feels gray and flat and you can't remember the last time something actually mattered — that's what this is for. Small moves, not big speeches.",
    "Shame Spirals + Self-Loathing":
        "If your brain is running the same three worst moments on loop and telling you that you're the problem — read this. Shame lies, and it's loud. Here's how to turn the volume down.",
    "Memory Slips":
        "Forgetting things you just heard, losing track mid-sentence, walking into a room with no idea why — that's not you losing it. It's stress doing what stress does to memory.",
    "Decision Fatigue":
        "When even small choices feel impossible and your brain just wants someone else to decide — that's decision fatigue. Here's how to get through the day without burning out on breakfast.",
    "Overreacting to Small Stuff":
        "You know the reaction doesn't match the situation. A spilled cup shouldn't ruin your afternoon. But it does. Here's what's actually going on and how to reset.",
    "Chronic Sleep Debt":
        "You're tired in a way that sleep doesn't fix. If you've been running on empty so long it feels normal, this is the guide that meets you there.",
    "Sleep Apnea and Snoring":
        "If you're waking up exhausted, snoring through the night, or your partner says you stop breathing — this isn't just annoying. Here's what to do about it.",
    "Noise, Crowds, Public Spaces":
        "When a grocery store feels like a combat zone and normal noise hits like an assault — that's your nervous system, not weakness. Here's how to get through it.",
    "Vision, Balance, Motion Sensitivity":
        "When your eyes, your balance, or movement itself feels off — and nobody can find a reason — this guide is for that exact frustration.",
    "Home Feels Like a Minefield":
        "When your own home doesn't feel safe — when you're walking on eggshells or the tension never lifts — here's what to do. Not everything. Just the next thing.",
    "Red/Yellow/Green Communication":
        "Most hard conversations fail because both people are in the wrong zone. Red means stop. Yellow means slow down. Green means go. Here's how to read it in real time.",
    "Repair After Damage":
        "You said something. You did something. Now there's damage. This isn't about being perfect — it's about what to do after you weren't.",
    "Parenting on Empty":
        "You're trying to be a good parent while running on fumes. If you feel like you're failing at the thing that matters most, this guide is honest about what helps.",
    "Kids in the Blast Radius":
        "Your kids are absorbing more than you think. This guide helps you see what they're picking up and what to do about it — without the guilt spiral.",
    "Family Life in Transition":
        "Everything's shifting — schedules, roles, expectations — and nobody handed you a playbook. Here's how to keep your family intact while the ground moves.",
    "Emotional Numbness":
        "When you can't feel anything — not sad, not happy, just flat — that's not strength. It's shutdown. Here's what's actually happening and one way back.",
    "Low Desire and Low Drive":
        "When you've lost interest in things that used to matter — including the person next to you — that's worth paying attention to. No pressure, just honesty.",
    "Stress Shuts Down Sex":
        "Stress doesn't just kill your mood. It shuts down your body's ability to connect. If intimacy feels impossible right now, here's what's going on.",
    "Sex and Avoidance After Difficult Experiences":
        "If intimacy triggers something you can't fully name — if you avoid it or just disconnect during it — this guide is written for that exact experience.",
    "Touch Without Pressure":
        "When even a hand on your shoulder feels like too much. This is about rebuilding physical connection at a pace that actually works for you.",
    "Body Image, Scars, Sexual Confidence":
        "If your body doesn't look or feel the way it used to — scars, weight, injury — and that's affecting how you show up in intimacy, this is for you.",
    "Sex After Injury/Health Change":
        "Your body changed. The old playbook doesn't work. This guide is practical, honest, and written for people who want connection but don't know where to start now.",
    "Moral Injury 101":
        "When you did something — or saw something — that violated your own moral code, and it won't stop replaying. That's moral injury. Here's what it is and what helps.",
    "Betrayed by the System":
        "You did the right thing and the system let you down. If you're carrying anger, disillusionment, or a sense that none of it mattered — this is for that.",
    "When You Feel Like the Villain":
        "You keep replaying what you did and you can't shake the feeling that you're the bad guy. This guide doesn't let you off the hook — it helps you carry it honestly.",
    "Faith, God, Big Questions":
        "When you're asking 'where was God in that?' or your faith doesn't hold what it used to — this guide sits with those questions instead of rushing past them.",
    "Between Worlds: Identity After Role":
        "When the thing that defined you ends — the job, the uniform, the role — and you don't know who you are without it. This is about that transition.",
    "Rebuilding Mission and Meaning":
        "You lost the mission. The structure. The purpose. Now what? This guide is about finding something worth getting up for — without pretending the old thing didn't matter.",
    "Loneliness and Loss of Tribe":
        "You had your people. Now you don't. If you're surrounded by others but feel completely alone — that's not dramatic. That's real. Here's what helps.",
    "Lone Wolf to Healthy Team Member":
        "You learned to do everything alone. It kept you alive. But it's costing you now. This guide is about letting people back in without losing yourself.",
    "Blow Up Recovery":
        "You blew up. It happened. Now what? This is the after plan — not a lecture, just how to come back from it and make the repair that actually matters.",
    "Shut Down Reconnect":
        "You went quiet. Checked out. Shut the door. And now you don't know how to come back. Here's how to reconnect without it being a whole thing.",
    "Overthinking Loop":
        "The same thought, on repeat, for hours. You can't stop analyzing, replaying, or planning for things that haven't happened. Here's how to break the loop.",
    "Night Spiral Stopper":
        "It's 2am and your brain just opened every file it has. If the nighttime spiral is stealing your sleep and your sanity, this is the interrupt plan.",
    "Hopelessness First Aid":
        "When nothing feels like it's going to work and you can't see a reason to keep trying — this guide doesn't pretend it's easy. It just gives you the next step.",
    "Crisis Conversation Action":
        "Someone you care about is in crisis. You don't need to be a therapist. You need to know what to say and what to do right now. Here it is.",
    "Tunnel Vision Reset":
        "When your world shrinks to one thing and you can't see anything else — that's tunnel vision. Here's how to widen the lens before you make a decision you'll regret.",
    "Scattered Brain Reset":
        "You can't finish a thought, hold a plan, or follow through on anything. Your brain feels like it's in 47 tabs. Here's how to close a few.",
    "Nightmare Recovery Plan":
        "You woke up shaking, sweating, heart pounding — and now you're afraid to go back to sleep. This is the plan for right now, tonight.",
    "3am Wake Loop Reset":
        "You wake up at 3am every night and your brain immediately goes to work. Here's how to break the cycle without fighting it.",
    "Pain Flare Plan":
        "When the pain spikes and everything else collapses around it — this is the plan. Not for curing it. For getting through today.",
    "Tension Release Plan":
        "Your body is holding everything your brain won't say. Jaw, shoulders, chest, gut. Here's how to let some of it go without needing a reason.",
    "TBI Brain Fog Plan":
        "If your brain feels like it's running through mud — slow processing, lost words, frustration — this guide is built for that exact experience.",
    "Headache Functional Plan":
        "When the headache won't quit and you still have to function — this isn't medical advice. It's a plan for getting through the day.",
    "Alcohol Numbing Interrupt":
        "You're not drinking to celebrate. You're drinking to stop feeling. This isn't a sobriety lecture — it's an honest look at the pattern and one way to interrupt it.",
    "Pill-Cycle Interrupt Plan":
        "The pills help. Then the pills become the problem. If you're caught in that cycle, this guide meets you where you actually are.",
    "Secondary Trauma for Partners":
        "You love someone who carries heavy things. And now you're carrying them too. This guide is for the person beside the person — because you matter in this.",
    "Secondary Trauma for Teams":
        "Your team absorbs hard things together. This is about what happens when the weight hits the group — and what to do before it tears the team apart.",
    "Habit Loop Reset":
        "You keep doing the thing you said you'd stop. Not because you're weak — because the loop is wired. Here's how to rewire it, one cycle at a time.",
    "Shame Loop Repair":
        "Shame did something → felt terrible → hid from it → shame got louder. If that cycle sounds familiar, here's how to break out of it.",
    "Shame and Intimacy Repair":
        "When shame makes intimacy feel impossible — when you can't be seen or let someone close — this is the guide for that stuck place.",
    "Disclosure Repair":
        "You told someone something hard and it didn't go well. Or you're thinking about telling and you're terrified. Either way, this helps.",
    "Work Identity Loss Plan":
        "If your sense of self was built around a job you no longer have — and now you don't know who you are — this guide is for that disorientation.",
    "Overwhelm Stabilization Plan":
        "Everything needs attention and you can't move. Not lazy — overloaded. Here's how to pick one thing and start without needing to fix it all.",
    "Money Avoidance Reset":
        "You're avoiding the bank account, the bills, the conversation. Money stress doesn't get better by not looking. Here's how to start looking without spiraling.",
    "Household Chaos Reset":
        "The house is a wreck and it feels like proof that you're failing. It's not. Here's how to reset the space without needing a full life makeover.",
    "Screen and Scroll Loop Reset":
        "You're doomscrolling and you know it. You can't stop. The phone is the escape and the problem at the same time. Here's the interrupt.",
    "Compulsion Interrupt Plan":
        "The thing you keep doing — checking, counting, cleaning, repeating — isn't random. It's a coping loop. Here's how to interrupt it without white-knuckling.",
    "Panic Attacks in Public: What To Do in 90 Seconds":
        "Your chest is tight, you can't breathe, and you're in a grocery store. This is the 90-second plan. Not later. Right now.",
    "Post-Incident Crash: The Day-After Recovery Guide":
        "Yesterday was bad. Today you feel like you got hit by a truck. This is the day-after plan — because nobody talks about what to do the morning after a hard one.",
    "Grief After Suicide Loss":
        "If someone you loved died by suicide and you're carrying a grief that nobody around you fully understands — this guide was written for exactly you.",
    "Survivor Guilt After Calls Scenes Incidents":
        "You made it out. They didn't. And now you can't stop asking why. Survivor guilt doesn't respond to logic — but it does respond to this.",
    "Court Complaint or Investigation Stress Survival":
        "You're under investigation, facing a complaint, or headed to court. The stress is different from anything else. Here's how to survive the process.",
    "Shift-Work Relationship Survival Plan":
        "Your schedule is destroying your relationship and you both know it. This guide is for couples where the shift comes first whether they want it to or not.",
    "Co-Parenting Under Burnout and Conflict":
        "You're both exhausted, you disagree on everything, and the kids are watching. Here's how to co-parent when you can barely co-exist.",
    "Returning to Work After Mental Health Leave":
        "Going back is harder than leaving. If you're dreading the return — the looks, the questions, the performance pressure — this guide walks you through it.",
    "Peer-Support Conversations for Teammates":
        "Your teammate is struggling and you want to say something but you don't know how. This gives you the words — not clinical ones, real ones.",
    "How To Ask for Help Without Feeling Weak":
        "You know you need help. You can't make yourself ask. This guide is for the gap between knowing and doing — because that gap is where most people get stuck.",
    "Building a Personal Safety Network":
        "You need people you can call at 2am. Not a lot of people — just the right ones. Here's how to build that list and actually use it.",
    "What To Do When Someone Refuses Help":
        "You've tried everything and they won't take the help. This guide is for the helpless feeling of watching someone you love refuse to move.",
    "Digital Overload and Doom-Scroll Recovery":
        "You spent four hours on your phone and feel worse than when you started. This is the recovery plan — because the scroll isn't just wasting time, it's wrecking you.",
    "Caffeine and Sleep Trap Reset for Frontline Schedules":
        "Coffee to function, can't sleep because of the coffee, more coffee tomorrow. If that's your life, here's how to break the cycle without quitting cold turkey.",
    "Eating Patterns Under Stress Reset Guide":
        "You're either not eating or eating everything. Stress rewires your hunger signals. This guide helps you get back to baseline without a diet plan.",
    "Boundaries With Family Who Do Not Understand the Job":
        "They mean well but they don't get it. And explaining feels exhausting. Here's how to set boundaries with family who can't understand what you carry.",
    "Dating While Carrying Trauma and Hypervigilance":
        "You want to date but your nervous system treats every new person like a threat assessment. Here's how to show up without armor — or at least with less of it.",
    "Year-One Transition Guide for Newly Separated or Retired Frontline":
        "The first year out is the hardest. Nobody prepares you for the identity loss, the boredom, and the grief of leaving. This guide walks through it month by month.",
}

# ---------------------------------------------------------------------------
# 2) 24-HOUR ACTION PLANS — topic-specific homework.
#    Replace the generic three-liner with something that feels like you
#    actually assigned it in session.
# ---------------------------------------------------------------------------
ACTION_PLANS = {
    "Always On: Your High-Alert Brain":
        "- Right now: pick one grounding move (5-4-3-2-1, cold water on your wrists, feet flat on the floor) and do it once today. Just once.\n- Before bed tonight: write down three moments your brain sounded the alarm and nothing was actually wrong.\n- Tomorrow: set one anchor check-in during the day — pause, ask yourself \"am I actually in danger right now?\" and answer honestly.",
    "Hypervigilance at Home":
        "- Right now: walk through your home and notice one thing that's safe. Say it out loud.\n- Before bed tonight: pick one room and intentionally relax your shoulders while standing in it for 60 seconds.\n- Tomorrow: when you catch yourself scanning at home, name it — \"that's my work brain, not my home brain\" — and redirect.",
    "Anger and Short-Fuse Days":
        "- Right now: name the earliest body signal you get before anger takes over (jaw, chest, heat, fists). Write it on your phone.\n- Before bed tonight: think about the last time you blew up and write one sentence about what was underneath the anger.\n- Tomorrow: the moment you feel that body signal, take a 90-second reset before you say anything. Cold water, walk outside, breathe.",
    "Depression and Numbness":
        "- Right now: do one thing that moves your body — a walk around the block, ten pushups, stretching for two minutes. Don't think about it, just move.\n- Before bed tonight: eat one real meal, even if you're not hungry.\n- Tomorrow: text one person you trust and say \"I'm in a low place today.\" That's it. You don't have to explain.",
    "Shame Spirals + Self-Loathing":
        "- Right now: write down the three shame memories your brain keeps looping. Get them out of your head and onto paper.\n- Before bed tonight: for each one, write what someone who loves you would actually say about what happened.\n- Tomorrow: when the loop starts, say out loud: \"That's shame talking, not fact.\" Then text one person and tell them one true thing.",
    "Memory Slips":
        "- Right now: set one external reminder for the most important thing you need to do today. Don't trust your brain on this one.\n- Before bed tonight: write tomorrow's top three priorities on paper, not your phone.\n- Tomorrow: when you forget something mid-task, pause and ask \"am I overloaded or distracted?\" — the answer changes the fix.",
    "Decision Fatigue":
        "- Right now: make one decision that's been sitting and do it in the next 10 minutes. It doesn't matter if it's perfect.\n- Before bed tonight: pre-decide three things for tomorrow (what to eat, what to wear, what to start with).\n- Tomorrow: limit yourself to two real decisions before noon. Everything else is autopilot.",
    "Overreacting to Small Stuff":
        "- Right now: think about the last time you overreacted. Write down what happened and what you were actually upset about underneath it.\n- Before bed tonight: name one stressor you've been ignoring that might be fueling the short fuse.\n- Tomorrow: when a small thing triggers a big reaction, pause and ask \"is this about the cup, or is this about everything else?\"",
    "Chronic Sleep Debt":
        "- Right now: set a hard stop time for screens tonight — one hour before you want to be asleep.\n- Before bed tonight: do one boring thing for 15 minutes (fold laundry, read something dull). Let your brain wind down.\n- Tomorrow: move your wake-up time 15 minutes earlier and resist the snooze. Start small.",
    "Sleep Apnea and Snoring":
        "- Right now: if you've been putting off a sleep study, call and schedule it today. Just the call.\n- Before bed tonight: sleep on your side instead of your back. Use a pillow barrier if you need to.\n- Tomorrow: track how many times you woke up gasping or how tired you feel at noon. Start building the data.",
    "Noise, Crowds, Public Spaces":
        "- Right now: identify one sensory tool that helps (earplugs, sunglasses, a grounding object in your pocket).\n- Before bed tonight: plan one outing for tomorrow with a time limit and an exit plan.\n- Tomorrow: go, use the tool, leave when you hit your limit — no guilt. Endurance comes later.",
    "Vision, Balance, Motion Sensitivity":
        "- Right now: limit one visual trigger today (dim a screen, reduce scrolling, take off fluorescent lighting).\n- Before bed tonight: do 60 seconds of fixed-point focus — stare at one still object and breathe.\n- Tomorrow: track when the symptoms spike and what you were doing — start building the pattern.",
    "Home Feels Like a Minefield":
        "- Right now: identify one room or corner that feels safest and spend 10 minutes there doing nothing.\n- Before bed tonight: write down the three biggest tension points in the house right now. Just name them.\n- Tomorrow: pick one tension point and address it — not all of it, just the first sentence of the conversation.",
    "Red/Yellow/Green Communication":
        "- Right now: honestly assess your color right now. Red, yellow, or green? Write it down.\n- Before bed tonight: think about the last hard conversation that went wrong. What color were you in? What color were they?\n- Tomorrow: before starting any important conversation, check both colors first. If either person is red, don't start.",
    "Repair After Damage":
        "- Right now: name the impact of what happened — not your intent, the actual impact on the other person.\n- Before bed tonight: write one honest sentence you could say to them that takes ownership without defending.\n- Tomorrow: say it. Not perfectly, not in a speech. Just the sentence.",
    "Parenting on Empty":
        "- Right now: give yourself one 15-minute break today. Not when the kids are asleep — before that. Let something be messy.\n- Before bed tonight: name one thing you did right as a parent today, even if it was small.\n- Tomorrow: ask for one specific help from one specific person. Not \"I need help\" — \"can you take them for an hour?\"",
    "Kids in the Blast Radius":
        "- Right now: watch your kids for five minutes without fixing anything. Just notice what they're doing and how they seem.\n- Before bed tonight: think about what your kids have been exposed to in the last month and write down what they might be carrying.\n- Tomorrow: ask one child one real question and listen without redirecting. \"How are you doing with all of this?\"",
    "Family Life in Transition":
        "- Right now: name the one thing that changed most recently and how it's affecting the family — be specific.\n- Before bed tonight: talk to one family member about the transition. Not to fix it, just to name it together.\n- Tomorrow: pick one new routine or anchor point that gives the family something predictable to land on.",
    "Emotional Numbness":
        "- Right now: put on a song that used to make you feel something. Listen to the whole thing.\n- Before bed tonight: write down five things you used to enjoy and circle the one that feels least impossible.\n- Tomorrow: do that one thing for 10 minutes. Not because you want to — because you're testing whether the wiring is still there.",
    "Low Desire and Low Drive":
        "- Right now: name one thing that used to interest you and notice what comes up when you think about it.\n- Before bed tonight: be honest with yourself about whether this is stress, disconnection, or something medical. Write it down.\n- Tomorrow: take one small step toward connection — doesn't have to be physical. A conversation, a shared meal, a walk together.",
    "Stress Shuts Down Sex":
        "- Right now: identify the biggest stressor that's between you and your partner. Name it to yourself.\n- Before bed tonight: tell your partner one true thing about how stress is affecting you — without making it about them.\n- Tomorrow: plan one moment of physical closeness that has zero pressure attached. Hand-holding, a long hug. That's it.",
    "Sex and Avoidance After Difficult Experiences":
        "- Right now: without forcing anything, notice what you feel in your body right now. Just notice.\n- Before bed tonight: write down what avoidance looks like for you — the signals, the excuses, the shutdowns.\n- Tomorrow: if you're ready, tell one safe person one honest thing about this. If you're not, that's okay — write it instead.",
    "Touch Without Pressure":
        "- Right now: put your own hand on your chest or arm and notice what it feels like. Safe? Neutral? Uncomfortable?\n- Before bed tonight: think about the kind of touch that feels okay right now — and the kind that doesn't. Write both down.\n- Tomorrow: communicate one boundary about touch to someone you trust. Not a big talk — one sentence.",
    "Body Image, Scars, Sexual Confidence":
        "- Right now: look at yourself in a mirror for 30 seconds without narrating what's wrong. Just look.\n- Before bed tonight: write down one thing your body has done for you that has nothing to do with how it looks.\n- Tomorrow: wear something that makes you feel like you — not someone else's version of okay.",
    "Sex After Injury/Health Change":
        "- Right now: name what's different about your body and what that means for intimacy. Be specific.\n- Before bed tonight: write down one thing you'd want your partner to know that you haven't said.\n- Tomorrow: say it. Or hand them what you wrote. Either way, let the truth into the room.",
    "Moral Injury 101":
        "- Right now: name the event that violated your moral code. You don't have to explain it — just name it.\n- Before bed tonight: write down what you believed before it happened and what you believe now.\n- Tomorrow: talk to one person who was there or who understands the context. Not for advice — for witness.",
    "Betrayed by the System":
        "- Right now: let yourself be angry about it for five minutes. Seriously. Set a timer and let it out.\n- Before bed tonight: write down what you expected the system to do and what it actually did.\n- Tomorrow: separate what you can control from what you can't. Pick one thing in the \"can\" column and act on it.",
    "When You Feel Like the Villain":
        "- Right now: write down the worst version of the story your brain keeps telling you. Get it all out.\n- Before bed tonight: write down what actually happened — not the shame version, the factual version.\n- Tomorrow: tell one trusted person both versions. Let them help you hold the difference.",
    "Faith, God, Big Questions":
        "- Right now: say the question you've been afraid to ask out loud. Even if it's angry. Especially if it's angry.\n- Before bed tonight: sit with the question for five minutes without trying to answer it.\n- Tomorrow: find one person — a friend, a spiritual leader, a counselor — and tell them where your faith is right now.",
    "Between Worlds: Identity After Role":
        "- Right now: finish this sentence: \"Before, I was ______. Now I'm ______.\" Write it down.\n- Before bed tonight: list three things about yourself that have nothing to do with the old role.\n- Tomorrow: do one thing that belongs to the new version of you. Not the old role. Not someone else's expectations. Yours.",
    "Rebuilding Mission and Meaning":
        "- Right now: write down what used to give you purpose. Don't edit it — just get it on paper.\n- Before bed tonight: ask yourself: \"what would make tomorrow worth getting through?\" Write whatever comes.\n- Tomorrow: do one thing — even a small one — that moves toward something that matters to you now.",
    "Loneliness and Loss of Tribe":
        "- Right now: text one person you haven't talked to in a while. Keep it short. \"Thinking about you.\"\n- Before bed tonight: write down three people who feel safe — not who should feel safe, who actually does.\n- Tomorrow: reach out to one of them. Not to catch up. Just to make contact.",
    "Lone Wolf to Healthy Team Member":
        "- Right now: think about the last time someone offered help and you said no. What would've happened if you'd said yes?\n- Before bed tonight: name one thing you're carrying alone that you don't actually have to.\n- Tomorrow: ask one person for one specific thing. \"Can you handle this today?\" — and let them.",
    "Blow Up Recovery":
        "- Right now: take 90 seconds and cool your body down. Cold water on your wrists, walk outside, deep breath.\n- Before bed tonight: write one sentence that takes ownership for the impact without defending your intent.\n- Tomorrow: say that sentence to the person it was aimed at. Then ask what they need.",
    "Shut Down Reconnect":
        "- Right now: notice that you've checked out and name it. \"I'm shut down right now.\"\n- Before bed tonight: text one person and say: \"I went quiet. I'm still here.\"\n- Tomorrow: re-enter one conversation or relationship you pulled away from. You don't need a reason — just show back up.",
    "Overthinking Loop":
        "- Right now: set a timer for 5 minutes. Think about the thing on loop as hard as you can. When the timer goes off, move your body.\n- Before bed tonight: write the thought loop down word for word. Seeing it on paper shrinks it.\n- Tomorrow: when the loop starts, name it — \"there's the loop\" — and redirect to one physical task.",
    "Night Spiral Stopper":
        "- Right now: put a pen and paper next to your bed. When the spiral starts tonight, write the thoughts down instead of chasing them.\n- Before bed tonight: set a hard screen cutoff 60 minutes before sleep.\n- Tomorrow: review what you wrote. Most of it won't look as urgent in daylight — and that's the point.",
    "Hopelessness First Aid":
        "- Right now: do one thing — any thing — in the next hour. Brush your teeth. Make the bed. Drink water. Just prove that you can still act.\n- Before bed tonight: text one person: \"Today was hard.\" You don't have to explain.\n- Tomorrow: do it again. One action, one contact. That's the whole plan until it gets easier.",
    "Crisis Conversation Action":
        "- Right now: identify the person you're worried about and decide: am I going to ask today or not?\n- Before bed tonight: practice your opening sentence out loud. \"I care about you. Can I ask you something real?\"\n- Tomorrow: ask. Not perfectly. Not with a script. Just ask.",
    "Tunnel Vision Reset":
        "- Right now: name the one thing your brain is stuck on. Write it down.\n- Before bed tonight: list three other things that are also true right now — things your brain is ignoring.\n- Tomorrow: make one decision that accounts for all four things, not just the one your brain is screaming about.",
    "Scattered Brain Reset":
        "- Right now: close every tab, app, and notification that isn't the one thing you need to do next.\n- Before bed tonight: write down the three most important things for tomorrow. Nothing else makes the list.\n- Tomorrow: do the first thing on the list before you check your phone.",
    "Nightmare Recovery Plan":
        "- Right now: if you just woke up from one — lights on, feet on the floor, cold water on your face. Orient to the room.\n- Before bed tonight: write down one safe image you can redirect to when you wake from a nightmare. Practice visualizing it.\n- Tomorrow: tell one person what's happening at night. Nightmares lose power when they're spoken.",
    "3am Wake Loop Reset":
        "- Right now: set a notepad by the bed. When you wake at 3am, write the thought down instead of solving it.\n- Before bed tonight: avoid screens after 10pm and do one boring thing for 20 minutes.\n- Tomorrow: review the 3am notes. Handle the real ones during the day. Let the rest go.",
    "Pain Flare Plan":
        "- Right now: do one thing to manage the flare — ice, heat, position change, medication if prescribed. Don't wait for it to get worse.\n- Before bed tonight: cancel or reschedule one thing tomorrow that you can't realistically do in pain. Give yourself the margin.\n- Tomorrow: do the minimum functional tasks. Everything else waits. Pain days aren't lazy days — they're survival days.",
    "Tension Release Plan":
        "- Right now: scan from your jaw to your feet. Where are you holding tension? Drop your shoulders. Unclench your jaw. Relax your fists.\n- Before bed tonight: do 60 seconds of progressive muscle relaxation — tense and release each group.\n- Tomorrow: set three check-in alarms throughout the day. Each one: scan, release, breathe.",
    "TBI Brain Fog Plan":
        "- Right now: simplify. Pick one task. Set a timer for 20 minutes. Do that task and nothing else.\n- Before bed tonight: write tomorrow's schedule with as much detail as you need — times, steps, locations. Don't rely on memory.\n- Tomorrow: take breaks between cognitive tasks. Your brain needs recovery windows — respect them.",
    "Headache Functional Plan":
        "- Right now: lower the lights, drink a full glass of water, and take any prescribed medication. Don't power through — manage.\n- Before bed tonight: eat something and set a consistent sleep time.\n- Tomorrow: if it's still there, track what's different today — hydration, sleep, stress, caffeine — and start building the pattern.",
    "Alcohol Numbing Interrupt":
        "- Right now: pour the first one and pause. Ask yourself: am I drinking to enjoy this or to stop feeling something?\n- Before bed tonight: write down what you were trying to numb. Be honest.\n- Tomorrow: replace the numbing time with one other activity — a walk, a call, anything that isn't the bottle.",
    "Pill-Cycle Interrupt Plan":
        "- Right now: take your medication exactly as prescribed. Not more and not less.\n- Before bed tonight: write down the last time you took more than prescribed and what was going on that day.\n- Tomorrow: tell one person — your doctor, a sponsor, a trusted friend — what the pattern looks like right now.",
    "Secondary Trauma for Partners":
        "- Right now: check in with yourself. Not them — you. How are you actually doing right now?\n- Before bed tonight: name one thing you've been absorbing from your partner's stress that isn't yours to carry.\n- Tomorrow: do one thing that's exclusively for you. Not for them, not for the family. Just you.",
    "Secondary Trauma for Teams":
        "- Right now: check in with one teammate — not about work, about them. \"How are you actually doing?\"\n- Before bed tonight: think about what the team has absorbed recently and whether anyone has said it out loud.\n- Tomorrow: create one space — even five minutes — for the team to name what they're carrying. No fixing. Just naming.",
    "Habit Loop Reset":
        "- Right now: identify the cue that starts the loop. What happens right before the habit kicks in?\n- Before bed tonight: write down: cue → routine → reward. Once you see the loop, you can break it.\n- Tomorrow: when the cue hits, replace the routine with one different action. Same cue, new response.",
    "Shame Loop Repair":
        "- Right now: say the shame thought out loud. Hear how it sounds outside your head.\n- Before bed tonight: write down one thing you're proud of from this week. Even if it feels small.\n- Tomorrow: tell one person one thing you've been ashamed about. Shame loses power when it's shared.",
    "Shame and Intimacy Repair":
        "- Right now: notice where shame lives in your body when you think about intimacy. Name the sensation.\n- Before bed tonight: write down what you need from your partner that you haven't asked for.\n- Tomorrow: start with one sentence. \"I need you to know that...\" You don't have to finish the whole conversation.",
    "Disclosure Repair":
        "- Right now: write down what you want them to know and why it matters.\n- Before bed tonight: decide who you want to tell and what you need from them when you do.\n- Tomorrow: if you're ready, say it. If you're not, that's okay — bring it to your next session or write them a letter.",
    "Work Identity Loss Plan":
        "- Right now: write down three things you're good at that have nothing to do with your old job.\n- Before bed tonight: ask yourself what you miss most — the work, the people, or the identity? They're different.\n- Tomorrow: do one thing that builds toward whatever comes next. Not the perfect thing. Just a step.",
    "Overwhelm Stabilization Plan":
        "- Right now: pick one thing from the pile. Just one. Do it, then stop.\n- Before bed tonight: write the three things that feel most urgent. Cross out the one that can actually wait.\n- Tomorrow: do the remaining two. One before noon, one after. That's the whole day.",
    "Money Avoidance Reset":
        "- Right now: open your bank account or your bills. Just look. You don't have to fix anything yet.\n- Before bed tonight: write down the number you're most afraid to see and the number that's actually there.\n- Tomorrow: make one call, send one email, or pay one bill. One step out of avoidance.",
    "Household Chaos Reset":
        "- Right now: pick one surface — a counter, a table, a desk — and clear it. That's it.\n- Before bed tonight: put three things back where they belong. Not a deep clean — just three things.\n- Tomorrow: do one room for 15 minutes. Timer on, timer off. Stop when it rings.",
    "Screen and Scroll Loop Reset":
        "- Right now: put your phone in another room for 30 minutes. Set a timer if you need to.\n- Before bed tonight: turn off non-essential notifications. Not all of them — just the ones that pull you back in.\n- Tomorrow: before you pick up your phone, do one thing first. Brush your teeth, make coffee, step outside. Break the first-touch habit.",
    "Compulsion Interrupt Plan":
        "- Right now: notice the urge without acting on it. Set a timer for two minutes and wait.\n- Before bed tonight: write down the compulsion cycle: trigger → urge → action → temporary relief → guilt. See the loop.\n- Tomorrow: when the urge comes, replace the action with a 90-second redirect — walk, breathe, text someone. The urge will still pass.",
    "Panic Attacks in Public: What To Do in 90 Seconds":
        "- Right now: practice the 90-second plan — feet flat, cold object in your hand, breathe in for 4 out for 6 — in a safe space so it's ready when you need it.\n- Before bed tonight: write a one-sentence card for your wallet: \"This is a panic attack. It will pass. Feet, cold, breathe.\"\n- Tomorrow: go somewhere mildly uncomfortable with an exit plan. Practice being in it and leaving when you need to.",
    "Post-Incident Crash: The Day-After Recovery Guide":
        "- Right now: hydrate, eat something, and do the minimum. Today is a recovery day, not a performance day.\n- Before bed tonight: tell one person what happened yesterday — not the whole story, just enough to break the silence.\n- Tomorrow: check in with yourself. If you're still in the crash, that's okay. If you're surfacing, pick up one thing.",
    "Grief After Suicide Loss":
        "- Right now: let yourself feel whatever you're feeling without judging it. There's no right way to grieve this.\n- Before bed tonight: say their name out loud. To yourself, to someone, to the room. They existed.\n- Tomorrow: connect with one person who understands this kind of loss — a support group, a counselor, someone who's been here.",
    "Survivor Guilt After Calls Scenes Incidents":
        "- Right now: notice the \"why them and not me\" thought and name it as survivor guilt — not truth.\n- Before bed tonight: write down what you did during the event that you can stand behind. You didn't do nothing.\n- Tomorrow: talk to someone who was there, or someone who gets it. Let the weight be shared.",
    "Court Complaint or Investigation Stress Survival":
        "- Right now: separate today from the outcome. You can't control the result. You can control how you get through today.\n- Before bed tonight: write down what you're most afraid of. Getting it out of your head takes power away from it.\n- Tomorrow: talk to your rep, your attorney, or a trusted supporter. Don't carry the legal stress alone.",
    "Shift-Work Relationship Survival Plan":
        "- Right now: text your partner something that isn't about logistics. \"Thinking about you\" is enough.\n- Before bed tonight: look at next week's schedule together and protect one shared time block. Guard it.\n- Tomorrow: use your commute or first break to send a real check-in. Not \"what's for dinner\" — \"how are you today?\"",
    "Co-Parenting Under Burnout and Conflict":
        "- Right now: decide one thing you and your co-parent can agree on this week. Just one.\n- Before bed tonight: write down what the kids need most from both of you right now — not from the best version, the actual version.\n- Tomorrow: have one conversation with your co-parent about the kids that stays on the kids. Not the past. The kids.",
    "Returning to Work After Mental Health Leave":
        "- Right now: write down your three biggest fears about going back. Name them.\n- Before bed tonight: identify one person at work you trust and decide to check in with them first.\n- Tomorrow: plan your first day with margins — don't stack meetings, don't overperform, don't try to prove you're fine.",
    "Peer-Support Conversations for Teammates":
        "- Right now: think about the teammate you're worried about. Decide if you're going to approach them today.\n- Before bed tonight: practice your opener: \"I've noticed something and I want to check on you. Can we talk?\"\n- Tomorrow: find a private moment and ask. You're not their therapist — you're their teammate showing up.",
    "How To Ask for Help Without Feeling Weak":
        "- Right now: name the one thing you need help with most. Be specific.\n- Before bed tonight: pick one person who's said yes to you before. They're your ask.\n- Tomorrow: ask. Say exactly what you need and give them an out if they can't. Clarity is the antidote to awkwardness.",
    "Building a Personal Safety Network":
        "- Right now: write down three people you could call at 2am if you needed to. If you can't name three, that's important information.\n- Before bed tonight: text one of them and say: \"You're someone I trust. I want you to know that.\"\n- Tomorrow: add 988 and Crisis Text Line (text HOME to 741741) to your phone contacts. Build the net before you need it.",
    "What To Do When Someone Refuses Help":
        "- Right now: accept that you can't force someone to accept help. Write down what that feels like.\n- Before bed tonight: identify the one thing you can still do — staying present, keeping the door open, taking care of yourself.\n- Tomorrow: reach out to your own support. Caring for someone who won't receive it is exhausting, and you need backup too.",
    "Digital Overload and Doom-Scroll Recovery":
        "- Right now: set your most-used app to a 30-minute daily limit. Just one app.\n- Before bed tonight: charge your phone outside the bedroom tonight. Not next to the bed — another room.\n- Tomorrow: replace your first 15 minutes of scrolling with something that uses your hands — coffee, stretching, cooking. Retrain the morning.",
    "Caffeine and Sleep Trap Reset for Frontline Schedules":
        "- Right now: note what time it is. If it's after 2pm, switch to water. Start there.\n- Before bed tonight: write down how many caffeine servings you had today and when the last one was.\n- Tomorrow: push your last caffeine 30 minutes earlier than today. Not cold turkey — just 30 minutes.",
    "Eating Patterns Under Stress Reset Guide":
        "- Right now: eat one real thing in the next hour. Not perfect, just real food.\n- Before bed tonight: notice whether you over-ate or under-ate today. No judgment — just notice.\n- Tomorrow: set three meal alarms. Eat when they go off whether you're hungry or not. Your hunger signals are offline — override them.",
    "Boundaries With Family Who Do Not Understand the Job":
        "- Right now: identify the one family conversation that drains you most. Name it.\n- Before bed tonight: draft one sentence you could use to set a boundary. \"I love you but I'm not going to discuss that.\"\n- Tomorrow: use it. The first time is the hardest. It gets easier.",
    "Dating While Carrying Trauma and Hypervigilance":
        "- Right now: notice how your body feels when you think about dating. Where's the tension?\n- Before bed tonight: write down what you want from a partner — not what you should want, what you actually want.\n- Tomorrow: do one brave thing. Respond to the message. Go on the date. Say one honest thing.",
    "Year-One Transition Guide for Newly Separated or Retired Frontline":
        "- Right now: write down three things you miss about the old life and three things you'd like to build in the new one.\n- Before bed tonight: connect with one person who's been through this transition ahead of you.\n- Tomorrow: do one thing that belongs to the new chapter. Sign up for something, explore something, start something small.",
}

# ---------------------------------------------------------------------------
# 3) WORKSHEET PROMPTS — topic-specific, replacing the generic five.
#    Each key maps to (worksheet1_prompts, worksheet2_prompts).
# ---------------------------------------------------------------------------
WORKSHEET_PROMPTS = {
    "Always On: Your High-Alert Brain": (
        "- What time of day does the scanning get loudest?\n- What's the last false alarm your brain triggered? What actually happened?\n- Where do you feel the hyperarousal first — head, chest, gut, hands?\n- What were you doing when you last felt genuinely safe?\n- What's one thing that helps your body believe the danger is over?",
        "- The grounding move I'll use when I catch myself scanning:\n- The sentence I'll say to myself when my brain says I'm in danger and I'm not:\n- One daily anchor check-in I'll build into my routine:\n- The person I'll tell about this pattern:\n- By tomorrow night, I'll know this worked if:"
    ),
    "Hypervigilance at Home": (
        "- Which room at home feels safest? Which feels most activating?\n- What sound, movement, or event triggers the scanning at home?\n- How does your partner or family react when they can tell you're on alert?\n- What's different about how your body feels at work vs. at home?\n- When's the last time you fully relaxed at home?",
        "- One thing I'll do to signal \"off duty\" when I get home:\n- The room or spot I'll use as my decompression zone:\n- What I'll say to my partner when I notice I'm scanning:\n- One physical cue I'll use to tell my body the threat level is low:\n- By tomorrow night, I'll know this worked if:"
    ),
    "Anger and Short-Fuse Days": (
        "- What was the last thing that set you off? What was actually underneath it?\n- What's the earliest body signal before the anger takes over?\n- Who usually gets the worst of it? What do they look like when it happens?\n- How long does it take you to come down after you blow up?\n- What have you tried before and why didn't it stick?",
        "- My earliest warning signal is:\n- My 90-second reset move when I feel it:\n- The sentence I'll use when I need to step away: \"I need ______\"\n- The repair I'll make to ______ in the next 24 hours:\n- By tomorrow night, I'll know this worked if:"
    ),
    "Depression and Numbness": (
        "- When did the flatness start? Was it gradual or sudden?\n- What's the last thing that made you feel something — anything?\n- What does your body feel like right now? Heavy? Empty? Both?\n- Who have you been pushing away or hiding from?\n- What would you do today if motivation wasn't part of the equation?",
        "- One body movement I'll do today even though I don't feel like it:\n- One person I'll text today with one honest sentence:\n- The meal I'll eat whether I'm hungry or not:\n- One thing I'll do tomorrow that used to matter to me:\n- By tomorrow night, I'll know this worked if:"
    ),
    "Shame Spirals + Self-Loathing": (
        "- What are the three memories your brain loops most when shame takes over?\n- What does shame tell you about yourself? Write it word for word.\n- Who do you avoid when you're in the spiral?\n- What's the difference between guilt (I did a bad thing) and shame (I am bad) in your head?\n- When's the last time you told someone the truth about what you're carrying?",
        "- The shame story I'll challenge today:\n- What someone who loves me would actually say about this:\n- The sentence I'll say out loud when the loop starts:\n- The person I'll share one true thing with this week:\n- By tomorrow night, I'll know this worked if:"
    ),
    "Memory Slips": (
        "- What kind of memory is failing — short-term, names, tasks, conversations?\n- When do the slips get worse — stress, fatigue, overwhelm, or all of those?\n- How does it make you feel when you forget something important?\n- What workaround have you tried that actually helps?\n- Is there a medical component here (TBI, medication, sleep) worth checking?",
        "- One external memory tool I'll start using today:\n- The three priorities I'll write down tonight for tomorrow:\n- One thing I'll take off my plate to reduce cognitive load:\n- The person I'll tell about the memory issues so they can help:\n- By tomorrow night, I'll know this worked if:"
    ),
    "Decision Fatigue": (
        "- What type of decisions drain you most — big ones, small ones, or all of them?\n- What do you do when you can't decide? Freeze, avoid, or let someone else choose?\n- How many decisions do you estimate you make before noon?\n- What's one decision you've been avoiding that's taking up mental space?\n- When decision-making was easier, what was different about your life?",
        "- Three things I'll pre-decide tonight for tomorrow:\n- One decision I'll make in the next 10 minutes:\n- The part of my day I'll put on autopilot:\n- One thing I'll delegate or drop entirely:\n- By tomorrow night, I'll know this worked if:"
    ),
    "Overreacting to Small Stuff": (
        "- What was the last small thing that triggered a big reaction?\n- What were you actually upset about underneath it?\n- What stressors have you been ignoring or pushing aside?\n- How does the other person react when you blow up over something small?\n- What does it feel like right before the overreaction — physically?",
        "- The question I'll ask myself when a small thing triggers a big reaction: \"Is this about ______ or about ______?\"\n- The pause I'll take before responding:\n- One underlying stressor I'll address this week:\n- The repair I'll make when I overreact:\n- By tomorrow night, I'll know this worked if:"
    ),
}

# For topics not in the dict above, generate contextual prompts from the title
def default_worksheet_prompts(title):
    w1 = (
        f"- When did \"{title}\" last show up for you? What was the situation?\n"
        f"- What did you notice first — in your body, your thoughts, or your behavior?\n"
        f"- What makes this pattern worse? What conditions or stressors fuel it?\n"
        f"- What have you tried before, and what actually helped (even a little)?\n"
        f"- Who in your life knows about this? Who doesn't — and why?"
    )
    w2 = (
        f"- One specific action I'll take in the next 24 hours:\n"
        f"- The sentence I'll use when I notice this pattern starting:\n"
        f"- The person I'll reach out to this week:\n"
        f"- What I'll do differently next time instead of the old response:\n"
        f"- By tomorrow night, I'll know this worked if:"
    )
    return (w1, w2)

# ---------------------------------------------------------------------------
# DISCLAIMER — appended to the end of every guide
# ---------------------------------------------------------------------------
DISCLAIMER = """
---

**A quick note:** This guide is educational — it's not therapy, it's not a diagnosis, and reading it doesn't create a clinical relationship between us. It's built to help you take the next step, not replace professional support. If you're in crisis, contact 988 (Suicide & Crisis Lifeline), text HOME to 741741 (Crisis Text Line), or call 911.
"""

# ---------------------------------------------------------------------------
# PROCESSING
# ---------------------------------------------------------------------------

def get_title(content):
    """Extract the # title from the first line."""
    first_line = content.split("\n")[0]
    if first_line.startswith("# "):
        return first_line[2:].strip()
    return None

def replace_opener(content, title):
    """Replace the boilerplate two-line opener with a topic-specific hook."""
    hook = OPENER_HOOKS.get(title)
    if not hook:
        return content

    # The boilerplate pattern:
    old1 = f'This guide helps with "{title}" when it keeps showing up in your week and you need a practical response.'
    old2 = "Use this when you want clear words and a clear next step, not theory."

    # The contractions pass may have altered the title inside the boilerplate
    # (e.g. "Do Not" → "Don't") while the # header was skipped.
    contracted_title = title.replace("Do Not", "Don't").replace("do not", "don't")
    old1_alt = f'This guide helps with "{contracted_title}" when it keeps showing up in your week and you need a practical response.'

    target = None
    if old1 in content:
        target = old1
    elif old1_alt in content:
        target = old1_alt

    if target:
        content = content.replace(target, hook, 1)
        if old2 in content:
            content = content.replace(old2, "", 1)
        # Clean up triple+ blank lines to double
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")

    return content

def replace_action_plan(content, title):
    """Replace the generic 24-hour action plan with topic-specific homework."""
    plan = ACTION_PLANS.get(title)
    if not plan:
        return content

    # Generic patterns
    old_block_markers = [
        "- Immediate action: choose one step above and do it in the next hour.",
        "- One support action: send one check-in text to someone safe.",
        "- One follow-up action: write what worked and what to change tomorrow.",
    ]

    if old_block_markers[0] not in content:
        return content

    # Find start of the generic block
    idx = content.index(old_block_markers[0])
    # Find end (after the third generic line)
    end_idx = idx
    for marker in old_block_markers:
        if marker in content:
            mpos = content.index(marker)
            mend = mpos + len(marker)
            if mend > end_idx:
                end_idx = mend

    remaining = content[end_idx:]

    # Find the next section header
    next_section = remaining.find("\n## ")
    if next_section == -1:
        next_section = len(remaining)

    between = remaining[:next_section]

    # Collect audience-specific lines between generic block and next section
    stripped_markers = [m.strip() for m in old_block_markers]
    audience_lines = []
    for line in between.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- ") and stripped not in stripped_markers and stripped:
            audience_lines.append(line)

    # Build replacement
    replacement = plan
    if audience_lines:
        replacement += "\n" + "\n".join(audience_lines)

    # Ensure blank line before next section
    after = remaining[next_section:].lstrip("\n")
    content = content[:idx] + replacement + "\n\n" + after

    return content

def replace_worksheet_prompts(content, title):
    """Replace generic worksheet prompts with topic-specific ones."""
    if title in WORKSHEET_PROMPTS:
        w1, w2 = WORKSHEET_PROMPTS[title]
    else:
        w1, w2 = default_worksheet_prompts(title)

    w1_header = "## Worksheet 1: Pattern Finder"
    w2_header = "## Worksheet 2: Action Builder"

    if w1_header not in content or w2_header not in content:
        return content

    w1_start = content.index(w1_header)
    w2_start = content.index(w2_header)

    # New worksheet 1 section
    w1_section = f"""{w1_header}

Goal: Spot the pattern — when it shows up, what triggers it, and what you notice first.

Prompts:
{w1}
"""

    # New worksheet 2 section
    w2_section = f"""{w2_header}

Goal: Turn what you noticed into one action and one commitment.

Prompts:
{w2}
"""

    # Find what comes after worksheet 2
    after_w2_content = content[w2_start + len(w2_header):]
    next_section = after_w2_content.find("\n## ")
    next_divider = after_w2_content.find("\n---")

    # Pick whichever comes first (section header or divider), or end of file
    end_candidates = []
    if next_section != -1:
        end_candidates.append(next_section)
    if next_divider != -1:
        end_candidates.append(next_divider)

    if end_candidates:
        end_offset = min(end_candidates)
        end_w2 = w2_start + len(w2_header) + end_offset
        after = content[end_w2:]
    else:
        after = ""

    # Reconstruct: everything before w1 + new w1 + new w2 + whatever was after w2
    content = content[:w1_start] + w1_section + "\n" + w2_section + after

    return content

def add_disclaimer(content):
    """Add disclaimer to end of file if not already present."""
    if "This guide is educational" in content:
        return content
    # Strip trailing whitespace/newlines and add disclaimer
    content = content.rstrip() + "\n" + DISCLAIMER
    return content

def process_file(fpath):
    with open(fpath, "r") as f:
        content = f.read()

    original = content
    title = get_title(content)
    if not title:
        return False

    content = replace_opener(content, title)
    content = replace_action_plan(content, title)
    content = replace_worksheet_prompts(content, title)
    content = add_disclaimer(content)

    if content != original:
        with open(fpath, "w") as f:
            f.write(content)
        return True
    return False

def main():
    changed = 0
    total = 0
    for root in ROOTS:
        for fpath in glob.glob(os.path.join(root, "**", "*.md"), recursive=True):
            total += 1
            if process_file(fpath):
                changed += 1

    print(f"Done. {changed}/{total} files updated.")
    print(f"  - Openers replaced: {len(OPENER_HOOKS)} unique hooks available")
    print(f"  - Action plans replaced: {len(ACTION_PLANS)} unique plans available")
    print(f"  - Worksheet prompts replaced: {len(WORKSHEET_PROMPTS)} custom + defaults for remainder")
    print(f"  - Disclaimer added to all files")

if __name__ == "__main__":
    main()
