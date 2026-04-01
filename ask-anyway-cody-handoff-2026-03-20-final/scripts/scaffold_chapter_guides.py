#!/usr/bin/env python3
"""
Build 33 chapter guides from the original 47 chapters (keeping singles, not splits)
Maps keep-single chapters to guide files with proper metadata and draft content
"""
import os
from pathlib import Path

# Mapping of chapter numbers to titles for the KEEP-SINGLE chapters
# These are the 33 chapters that should NOT be split
chapters_to_keep = {
    1: "Always On: Your High-Alert Brain",
    3: "Hypervigilance at Home",
    4: "Anger and Short-Fuse Days",
    6: "Depression and Numbness",
    8: "Shame Spirals + Self-Loathing",
    9: "Memory Slips",
    11: "Decision Fatigue",
    12: "Overreacting to Small Stuff",
    13: "Chronic Sleep Debt",
    14: "Sleep Apnea and Snoring",
    19: "Noise, Crowds, Public Spaces",
    20: "Vision, Balance, Motion Sensitivity",
    21: "Home Feels Like a Minefield",
    22: "Red/Yellow/Green Communication",
    23: "Repair After Damage",
    24: "Parenting on Empty",
    26: "Kids in the Blast Radius",
    27: "Family Life in Transition",
    28: "Emotional Numbness",
    29: "Low Desire and Low Drive",
    30: "Stress Shuts Down Sex",
    31: "Sex and Avoidance After Difficult Experiences",
    33: "Touch Without Pressure",
    34: "Body Image, Scars, Sexual Confidence",
    35: "Sex After Injury/Health Change",
    36: "Moral Injury 101",
    37: "Betrayed by the System",
    38: "When You Feel Like the Villain",
    39: "Faith, God, Big Questions",
    41: "Between Worlds: Identity After Role",
    42: "Rebuilding Mission and Meaning",
    45: "Loneliness and Loss of Tribe",
    46: "Lone Wolf to Healthy Team Member",
}

def get_batch_for_chapter(ch_num):
    """Assign batch based on chapter priority"""
    if ch_num in [1, 4, 6, 8, 23, 36]:  # Core nervous system + repair + moral injury
        return "batch-1"
    elif ch_num in [24, 26, 27, 29, 30, 31]:  # Relationships/family/intimacy
        return "batch-2"
    else:
        return "batch-3"

def get_guide_filename(ch_num, title):
    """Create filename from chapter number and title"""
    clean_title = title.lower().replace(": ", "-").replace("/", "-and-").replace("+", "and").replace(" ", "-").replace("--", "-")
    return f"ch-{ch_num:02d}-{clean_title}.md"

def profile_for_title(title):
    """Map title to psychological profile for drafting"""
    low = title.lower()
    if any(x in low for x in ["crisis", "suicid", "hopeless", "danger"]):
        return "crisis"
    elif any(x in low for x in ["anger", "rage", "blow", "short-fuse", "overreact"]):
        return "reactivity"
    elif any(x in low for x in ["sleep", "wake", "nightmare", "3am", "fatigue", "debt"]):
        return "sleep"
    elif any(x in low for x in ["parent", "family", "kid", "home", "relation", "partner", "couple"]):
        return "relationship"
    elif any(x in low for x in ["moral", "shame", "guilt", "faith", "betrayal", "villain"]):
        return "moral"
    elif any(x in low for x in ["sex", "intimacy", "desire", "touch", "body image"]):
        return "intimacy"
    elif any(x in low for x in ["pain", "tension", "body", "migraine", "headache", "sense"]):
        return "body"
    elif any(x in low for x in ["scroll", "habit", "loop", "compul", "dopamine"]):
        return "habit"
    elif any(x in low for x in ["work", "identity", "job", "role", "meaning", "transition"]):
        return "work"
    else:
        return "general"

def scaffold_chapter_guides():
    """Create all 33 chapter guide files with scaffold structure"""
    chapter_dir = Path("content/topic-guides/chapters")
    chapter_dir.mkdir(parents=True, exist_ok=True)
    
    template = """# {title}

Status: draft_v1_complete
Guide ID: ch-{ch_num:02d}
Guide type: chapter
Source: Ch{ch_num}
Batch: {batch}
Priority: {priority}

## What This Helps With

This guide helps with "{title}" when it keeps showing up in your week and you need a practical response.
Use this when you want clear words and a clear next step, not theory.

## What Is Happening

[Profile-specific content will be added during drafting]

## What To Do Now

[Profile-specific steps will be added during drafting]

## What To Say

[Profile-specific scripts will be added during drafting]

## Common Mistakes To Avoid

- [Mistake 1]
- [Mistake 2]
- [Mistake 3]

## 24-Hour Action Plan

- Immediate action: choose one step above and do it in the next hour.
- One support action: send one check-in text to someone safe.
- One follow-up action: write what worked and what to change tomorrow.

## Worksheet 1: Pattern Finder

Goal: Identify triggers, context, and early warning signs.

Prompts:
- In the last 7 days, when did "{title}" show up most?
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
"""
    
    for ch_num, title in sorted(chapters_to_keep.items()):
        filename = get_guide_filename(ch_num, title)
        filepath = chapter_dir / filename
        batch = get_batch_for_chapter(ch_num)
        priority = "high" if batch == "batch-1" else "medium"
        
        content = template.format(
            title=title,
            ch_num=ch_num,
            batch=batch,
            priority=priority
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Scaffolded: {filename}")
    
    print(f"\nScaffolded {len(chapters_to_keep)} chapter guides in content/topic-guides/chapters/")

if __name__ == "__main__":
    scaffold_chapter_guides()
    print("\nChapter guide scaffolding complete.")
