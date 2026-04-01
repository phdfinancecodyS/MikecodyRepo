#!/usr/bin/env python3
import os
import re
from pathlib import Path

# Mapping of guide titles/filenames to their editorial refinement
# These are the core sections that need sharpening from generic to specific

refinements = {
    "new-12-what-to-do-when-someone-refuses-help": {
        "what_is_happening": """When someone will not accept help, it usually means one of three things: they are not ready to change, they do not trust your motives, or they think they should handle it alone. You cannot force readiness. But you can stay connected, name what you are seeing, and keep your boundaries while their refusal plays out.""",
        "what_to_do_now": [
            "Say clearly what you are seeing without judgment or argument.",
            "Name one concrete help option and leave the door open.",
            "Set your own boundary about what you will and will not do, then step back."
        ],
        "what_to_say": [
            "I am noticing you are pushing back on help right now.",
            "I want to help, and right now you are saying no. I respect that and I am still here.",
            "Here is what I can do, and here is what I cannot do. That part is up to you."
        ]
    },
    "new-10-how-to-ask-for-help-without-feeling-weak": {
        "what_is_happening": """Asking for help feels like admitting defeat if you were taught to be independent or strong. But asking is actually advanced function—it means you know your limits, you trust others, and you take your needs seriously. People who ask for help recover faster and stay connected better.""",
        "what_to_do_now": [
            "Identify one specific help need (not vague rescue).",
            "Pick one person who has said yes to you in the past.",
            "Ask for exactly what you need, and give them an out by showing you have a backup plan."
        ],
        "what_to_say": [
            "I need one specific help with [exact thing]. Can you do that?",
            "If not, that is okay—I have another option. But if you can, I would be grateful.",
            "This matters to me and I am asking because I trust you."
        ]
    },
    "new-11-building-a-personal-safety-network": {
        "what_is_happening": """A safety network is not just crisis contacts. It is 3-5 specific people for different needs: someone for practical help, someone for emotional support, someone for crisis, someone you can be honest with. Most people have none of these named in advance, so they spin when they need help.""",
        "what_to_do_now": [
            "Name three real people you trust with different types of needs.",
            "Text each person one specific help question to gauge response.",
            "Write their names and what they are good for in your phone."
        ],
        "what_to_say": [
            "I am building a support list. Can I count on you for [specific type of help]?",
            "I would check in with you before things get urgent.",
            "This helps me know I have someone real to call, not just a crisis number."
        ]
    },
    "new-01-panic-attacks-in-public-what-to-do-in-90-seconds": {
        "what_is_happening": """Panic in public feels catastrophic because you think everyone is watching and something is medically wrong with you. Neither is true. Your nervous system got a false alarm signal and now it is running a full threat response. You have 90 seconds to interrupt the spiral before it feeds itself.""",
        "what_to_do_now": [
            "Move to a less-crowded spot if you can, or stay and plant your feet.",
            "Do one grounding move: feel your feet on the ground, name five things you see, or do box breathing for 30 seconds.",
            "Drink water and text one safe person that you are handling this now."
        ],
        "what_to_say": [
            "My nervous system thinks I am in danger but I am not. This will pass.",
            "I am using my reset right now and I am safe.",
            "I am in the middle of this and I will be okay in a few minutes."
        ]
    },
    "new-02-post-incident-crash-the-day-after-recovery-guide": {
        "what_is_happening": """The day after an incident, your nervous system crashes. Adrenaline is gone, emotions hit, and your body feels wrecked. This is not weakness—this is what happens after intense activation. The crash is part of the cycle and managing it well prevents worse spirals later.""",
        "what_to_do_now": [
            "Move slowly and do not schedule anything heavy for the next 24 hours.",
            "Eat and hydrate like you are recovering from the flu.",
            "Lower your bar for today; one small win is enough."
        ],
        "what_to_say": [
            "Today I am recovering, not performing.",
            "My body is telling me it needs downtime and I am listening.",
            "I made it through yesterday. Today is about stability."
        ]
    },
    "new-03-grief-after-suicide-loss": {
        "what_is_happening": """Grief after suicide loss carries extra weight: shock, confusion, guilt about things unsaid, and sometimes anger at the person who left. Your brain keeps running counterfactuals—what could have changed this? Nothing you think right now will answer that question. You are in crisis-level grief and your job is survival first, meaning-making later.""",
        "what_to_do_now": [
            "Tell three people what happened so you are not holding this alone.",
            "Get to one grief group or therapist this week (not optional).",
            "Do one physical thing every day: walk, cry, write, punch a pillow. Move the grief through your body."
        ],
        "what_to_say": [
            "I lost someone to suicide. That is what happened.",
            "I need help carrying this and I am not going to pretend I am fine.",
            "I do not know why they made that choice and right now I just need to get through each day."
        ]
    },
    "new-04-survivor-guilt-after-calls-scenes-incidents": {
        "what_is_happening": """Survivor guilt is the belief that you should have been able to prevent something, or that you do not deserve to be okay when someone else is not. It is especially strong in first-responder work where you see bad outcomes regularly. The guilt is real and it does not mean you did anything wrong.""",
        "what_to_do_now": [
            "Write down what you actually could have controlled in that situation.",
            "Name what was outside your control, even if you still feel responsible.",
            "Find one other person who has done the same work and tell them what you are feeling."
        ],
        "what_to_say": [
            "I am carrying guilt about [specific incident]. I know I could not control everything but I feel like I should have.",
            "I need to talk about this with someone who understands the work.",
            "I am not looking for you to fix it. I just need to say it out loud."
        ]
    },
    "new-05-court-complaint-or-investigation-stress-survival": {
        "what_is_happening": """An investigation or complaint against you triggers threat detection in your body—your job status is threatened, your reputation is on the line, and you are probably scared. This is not time for trying to feel normal. This is time for protecting yourself, following your union or legal guidance exactly, and managing the actual crisis, not your feelings about it.""",
        "what_to_do_now": [
            "Get legal representation or union help immediately—do not skip this step.",
            "Follow their guidance exactly. Do not try to handle this alone.",
            "Set a time limit for daily worry (say, 20 minutes) and discipline yourself to it."
        ],
        "what_to_say": [
            "I am in an investigation and I need my representative at every step.",
            "I am not answering questions without guidance because I am protecting myself appropriately.",
            "This is temporary and stressful and I am doing the right things."
        ]
    },
    "new-06-shift-work-relationship-survival-plan": {
        "what_is_happening": """Shift work erodes relationships because you are not available when the other person needs you most, and vice versa. No amount of romance fixes the simple math of opposite schedules. Your job is to protect a few anchors you can both count on, rather than trying to maintain continuous connection.""",
        "what_to_do_now": [
            "Name 2-3 non-negotiable couple touchpoints (Sunday breakfast, Tuesday text check-in, whatever you can keep).",
            "Protect those times ruthlessly.",
            "On off-days, do one shared activity, not long-distance relationship maintenance."
        ],
        "what_to_say": [
            "This schedule is hard on us and I am not going to pretend it is not.",
            "These are the times I can promise I am fully here. Outside that, I am managing the shift.",
            "I am not pulling away from you; I am trying to protect what I can show up for."
        ]
    },
    "new-07-co-parenting-under-burnout-and-conflict": {
        "what_is_happening": """Co-parenting while burned out or in conflict usually means you are managing two crises at once: your own depletion and the conflict with the other parent. Kids read both. Your job is not to fix the co-parent or the conflict instantly—it is to keep yourself functioning and give kids one stable parent.""",
        "what_to_do_now": [
            "Pick one parenting commitment you will protect no matter what (bedtime, one meal, one check-in).",
            "Take that off the table from conflict negotiations.",
            "Keep co-parent communication to logistics only, not emotions."
        ],
        "what_to_say": [
            "I am running on empty right now and I need to protect my capacity with the kids.",
            "On this topic, here is what I am doing regardless. We can talk about the rest when I am more stable.",
            "Let us stick to [logistics topic] and I will keep you in the loop."
        ]
    },
    "new-08-returning-to-work-after-mental-health-leave": {
        "what_is_happening": """Returning to work after mental health leave is re-entry shock. Your brain got used to a different pace, and now you are back in the high-demand environment that contributed to your leaving. You are also under extra scrutiny in your own mind, terrified you will fall apart again.""",
        "what_to_do_now": [
            "Return to your light duty or part-time first if you can—do not go full intensity.",
            "Name one work situation that was part of the original problem and plan one new response.",
            "Schedule one check-in with your therapist or support person for mid-week."
        ],
        "what_to_say": [
            "I am back and taking this slow. I know what led to my leave and I am managing it differently now.",
            "I will be transparent if I need adjustments, and I am committed to this role.",
            "I am still in recovery and I am working."
        ]
    },
    "new-09-peer-support-conversations-for-teammates": {
        "what_is_happening": """Peer support means you are not a therapist and you are not responsible for fixing them. Your job is to listen, name what you see, and connect them to actual help. Many peer supporters burn out because they absorb the emotional weight of the problem.""",
        "what_to_do_now": [
            "Listen to what they say without trying to solve it in one conversation.",
            "Name back what you heard so they feel seen.",
            "Name one concrete resource and leave it with them rather than trying to make them use it."
        ],
        "what_to_say": [
            "I hear you. That sounds really hard.",
            "Here is what I see: [what they are up against]. And here is where you get actual professional help.",
            "I am here to check in with you, and I am also not the person who fixes this."
        ]
    },
    "new-13-digital-overload-and-doom-scroll-recovery": {
        "what_is_happening": """Doom-scrolling is not a moral failing. It is your nervous system's way of managing anxiety by staying hyper-aware of threat. But it keeps your threat system locked on, which makes anxiety worse. Breaking the cycle means replacing the compulsion with something that actually calms your nervous system.""",
        "what_to_do_now": [
            "Delete apps or move them to a screen folder so they are not one-tap access.",
            "When you want to scroll, do one 60-second body-based alternative instead (walk, shake, breathe, cold water).",
            "At night, put your phone in another room one hour before bed."
        ],
        "what_to_say": [
            "I am using my phone as an anxiety management tool and it is making anxiety worse.",
            "I am breaking the one-tap access so I have time to choose something better.",
            "The first few days are hardest and then my nervous system recalibrates."
        ]
    },
    "new-14-caffeine-and-sleep-trap-reset-for-frontline-schedules": {
        "what_is_happening": """Shift work + caffeine + sleep debt creates a trap: you need caffeine to function in the shift, caffeine keeps you wired when you finally sleep, poor sleep makes you need more caffeine. Breaking this cycle means picking one variable to shift and holding it for two weeks.""",
        "what_to_do_now": [
            "Choose: cut caffeine after noon, or shift your caffeine timing two hours earlier, or none (hardest).",
            "Commit to that one change for 14 days no matter what.",
            "On days off, do not use caffeine as a catch-up tool—your body is trying to recalibrate."
        ],
        "what_to_say": [
            "I am caught in caffeine and sleep patterns that are not working.",
            "For the next two weeks I am trying [one specific change]. That is the only thing I am changing.",
            "This will be rough and then it will settle."
        ]
    },
    "new-15-eating-patterns-under-stress-reset-guide": {
        "what_is_happening": """When you are under stress, eating becomes either invisible (you do not eat) or a coping tool (you eat to manage feelings). Neither is about hunger. Your job is not to fix your eating perfectly—it is to create one pattern you can repeat when stressed that keeps your body fueled.""",
        "what_to_do_now": [
            "Pick one meal you will face directly when stressed (breakfast, lunch, or dinner).",
            "Make it simple and do not require willpower (PB&J, cereal, pasta, whatever).",
            "Eat that meal at the same time every day, even if small."
        ],
        "what_to_say": [
            "My eating goes sideways when I am stressed and I am not going to fix that by willpower alone.",
            "I am committing to one meal that works when I am overwhelmed.",
            "This is about keeping my body functional, not being perfect."
        ]
    },
    "new-16-boundaries-with-family-who-do-not-understand-the-job": {
        "what_is_happening": """Family members who are not in the work do not understand why you come home wired, why you cannot just leave work at work, or why you need to decompress alone. They think something is wrong with you. You are protecting yourself by not forcing them to understand something they have not lived.""",
        "what_to_do_now": [
            "Name the one or two boundary violations that happen most (unsolicited advice, pressure to go out, asking details about calls).",
            "State your boundary once, clearly, then enforce it without re-explaining.",
            "Plan one activity or topic that does not involve the job that keeps connection alive."
        ],
        "what_to_say": [
            "I am not talking about the work when I am home. I need that containment for my own recovery.",
            "When you ask [specific thing], it pulls me back in and I cannot do that.",
            "Here is what I can share about my day: [non-work topics]."
        ]
    },
    "new-17-dating-while-carrying-trauma-and-hypervigilance": {
        "what_is_happening": """Trauma and hypervigilance make dating harder because you are reading threat in normal relationship moments. You may isolate, push people away, or move too fast seeking safety. You are not broken for this. You need to pace differently and name what is happening so your person can understand.""",
        "what_to_do_now": [
            "Tell the person early and clearly: I have been through something difficult and I am managing some hypervigilance.",
            "Name one specific way it shows up for you when stressed (withdrawing, testing, asking for reassurance a lot).",
            "Ask them to be patient with the pattern and tell you when they notice it."
        ],
        "what_to_say": [
            "I carry some trauma and sometimes that shows up as [specific pattern]. It is not about you.",
            "When I do this, here is what helps: [what actually helps]. Here is what makes it worse: [what triggers].",
            "I want this to work and I am managing my stuff. Bear with me."
        ]
    },
    "new-18-year-one-transition-guide-for-newly-separated-or-retired-frontline": {
        "what_is_happening": """Leaving the job (through separation or retirement) is an identity loss. Your routine vanishes, your sense of purpose gets muddled, and suddenly you have space and no structure in it. The first year is disorientation, not failure. You are rebuilding how you see yourself outside the role.""",
        "what_to_do_now": [
            "Do not search for a replacement identity in year one—just stabilize the basics (sleep, eat, move).",
            "Keep one connection to the community (coffee with someone from work, volunteer in adjacent field, something).",
            "Do not fill all the time instantly; boredom is actually part of how your nervous system recalibrates."
        ],
        "what_to_say": [
            "I am no longer in the role and I am figuring out who I am now.",
            "This is not laziness or depression—this is transition and it takes time.",
            "I am staying connected to the community in smaller ways while I settle."
        ]
    }
}

def extract_section(content, section_name):
    """Extract a section from guide content"""
    pattern = rf"^## {section_name}\n\n(.*?)(?=^##|$)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else None

def rebuild_guide(content, filename, refinement):
    """Rebuild a guide with refined sections"""
    # Parse the metadata section
    metadata_match = re.match(r"(# .*?\n(?:.*?\n)*?)(?=^##)", content, re.MULTILINE)
    metadata = metadata_match.group(1).strip() if metadata_match else ""
    
    # Parse what this helps with
    what_helps_match = re.search(r"^## What This Helps With\n\n(.*?)(?=^##)", content, re.MULTILINE | re.DOTALL)
    what_helps = what_helps_match.group(1).strip() if what_helps_match else ""
    
    # Parse what is happening - use refined if available
    if "what_is_happening" in refinement:
        what_happening = refinement["what_is_happening"]
    else:
        what_happening_match = re.search(r"^## What Is Happening\n\n(.*?)(?=^##)", content, re.MULTILINE | re.DOTALL)
        what_happening = what_happening_match.group(1).strip() if what_happening_match else ""
    
    # Parse what to do now - use refined if available
    if "what_to_do_now" in refinement:
        what_todo = format_list(refinement["what_to_do_now"])
    else:
        what_todo_match = re.search(r"^## What To Do Now\n\n(.*?)(?=^##)", content, re.MULTILINE | re.DOTALL)
        what_todo = what_todo_match.group(1).strip() if what_todo_match else ""
    
    # Parse what to say - use refined if available
    if "what_to_say" in refinement:
        what_say = "\n".join([f"- {item}" for item in refinement["what_to_say"]])
    else:
        what_say_match = re.search(r"^## What To Say\n\n(.*?)(?=^##)", content, re.MULTILINE | re.DOTALL)
        what_say = what_say_match.group(1).strip() if what_say_match else ""
    
    # Extract remaining sections that should not be modified
    mistakes_match = re.search(r"^## Common Mistakes To Avoid\n\n(.*?)(?=^##)", content, re.MULTILINE | re.DOTALL)
    mistakes = mistakes_match.group(1).strip() if mistakes_match else ""
    
    plan_match = re.search(r"^## 24-Hour Action Plan\n\n(.*?)(?=^##)", content, re.MULTILINE | re.DOTALL)
    plan = plan_match.group(1).strip() if plan_match else ""
    
    worksheet1_match = re.search(r"^## Worksheet 1:.*?\n\nGoal:[^\n]*\n\n(Prompts:.*?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
    worksheet1_content = worksheet1_match.group(1).strip() if worksheet1_match else ""
    
    worksheet2_match = re.search(r"^## Worksheet 2:.*?\n\nGoal:[^\n]*\n\n(Prompts:.*?)$", content, re.MULTILINE | re.DOTALL)
    worksheet2_content = worksheet2_match.group(1).strip() if worksheet2_match else ""
    
    # Rebuild the guide
    rebuilt = f"""{metadata}

## What This Helps With

{what_helps}

## What Is Happening

{what_happening}

## What To Do Now

{what_todo}

## What To Say

{what_say}

## Common Mistakes To Avoid

{mistakes}

## 24-Hour Action Plan

{plan}

## Worksheet 1: Pattern Finder

Goal: Identify triggers, context, and early warning signs.

{worksheet1_content}

## Worksheet 2: Action Builder

Goal: Turn insight into one script and one 24-hour commitment.

{worksheet2_content}
"""
    
    return rebuilt

def format_list(items):
    """Format a list for markdown"""
    return "\n".join([f"{i+1}. {item}" for i, item in enumerate(items)])

# Process guides
guide_dir = Path("content/topic-guides")
split_dir = guide_dir / "splits"
new_dir = guide_dir / "new-topics"

for guide_path in list(split_dir.glob("*.md")) + list(new_dir.glob("*.md")):
    filename = guide_path.stem
    
    if filename in refinements:
        print(f"Refining: {filename}")
        
        with open(guide_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        refinement = refinements[filename]
        
        # Rebuild the guide with refined sections
        rebuilt = rebuild_guide(content, filename, refinement)
        
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(rebuilt)
        print(f"  ✓ Updated")

print("\nEditorial refinement pass complete.")
print(f"Refined {len(refinements)} guides with specific, direct language.")
