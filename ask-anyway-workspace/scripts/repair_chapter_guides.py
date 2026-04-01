#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTER_DIR = ROOT / "content" / "topic-guides" / "chapters"

PROFILE_DEFAULTS = {
    "crisis": {
        "mistakes": [
            "Waiting for certainty before acting on safety concerns.",
            "Trying to manage a high-risk moment alone and in secret.",
            "Treating the crisis like it will pass without direct action."
        ],
        "worksheet2": [
            "Script I will use word-for-word next time:",
            "The first safety step I will take:",
            "The first person or resource I will contact:",
            "What I will do in the next 24 hours to stay safer:",
            "How I will know I followed through by tomorrow night:"
        ]
    },
    "reactivity": {
        "mistakes": [
            "Waiting until the reaction is already big before trying to reset.",
            "Explaining the reaction instead of taking ownership for the impact.",
            "Leaving a hard moment without a return plan or repair step."
        ],
        "worksheet2": [
            "Script I will use word-for-word next time:",
            "The earliest body cue I will watch for:",
            "My 90-second reset routine:",
            "One repair action I will take in the next 24 hours:",
            "How I will measure success by tomorrow night:"
        ]
    },
    "sleep": {
        "mistakes": [
            "Trying a completely different sleep fix every night.",
            "Using screens, scrolling, or stimulation as your wind-down plan.",
            "Expecting one good night to repair long-term sleep strain."
        ],
        "worksheet2": [
            "My anchor sleep or wake time:",
            "The wind-down step I will protect this week:",
            "One thing I will stop doing that makes sleep worse:",
            "One action I will take in the next 24 hours:",
            "How I will measure progress by tomorrow night:"
        ]
    },
    "relationship": {
        "mistakes": [
            "Trying to fix the whole relationship in one conversation.",
            "Having the conversation when neither person is regulated enough for it.",
            "Skipping clear repair, boundaries, or follow-up after the hard moment."
        ],
        "worksheet2": [
            "Script I will use word-for-word next time:",
            "The boundary or request I need to make clearly:",
            "The repair action I will take in the next 24 hours:",
            "The person I need to follow up with:",
            "How I will know this went better by tomorrow night:"
        ]
    },
    "moral": {
        "mistakes": [
            "Treating shame like proof instead of one part of the story.",
            "Isolating with guilt instead of saying the truth out loud somewhere safe.",
            "Trying to rush forgiveness before honest accountability and repair."
        ],
        "worksheet2": [
            "The truth I need to say clearly to myself or someone safe:",
            "The value I want to act in line with next:",
            "One repair or accountability step I will take in the next 24 hours:",
            "The person or practice that helps me stay honest:",
            "How I will measure progress by tomorrow night:"
        ]
    },
    "intimacy": {
        "mistakes": [
            "Adding pressure when the real need is safety, pacing, or clarity.",
            "Assuming avoidance means you do not care about connection.",
            "Trying to force closeness before the body feels safe enough for it."
        ],
        "worksheet2": [
            "Script I will use word-for-word next time:",
            "The form of touch or closeness that feels most doable right now:",
            "One pressure-reducing action I will take in the next 24 hours:",
            "The person I need to communicate with clearly:",
            "How I will know this felt safer by tomorrow night:"
        ]
    },
    "body": {
        "mistakes": [
            "Ignoring physical warning signs until they take over the whole day.",
            "Pushing through symptoms as if force will solve a nervous-system problem.",
            "Treating body symptoms like a character problem instead of a signal."
        ],
        "worksheet2": [
            "The body-based script I will use next time:",
            "The regulation or pacing step I will take first:",
            "One body-support action I will take in the next 24 hours:",
            "The person or resource I will loop in if symptoms keep escalating:",
            "How I will measure progress by tomorrow night:"
        ]
    },
    "habit": {
        "mistakes": [
            "Waiting until the urge is loud before interrupting the pattern.",
            "Focusing only on stopping the habit without replacing what it was doing for you.",
            "Treating one slip like proof the whole effort is ruined."
        ],
        "worksheet2": [
            "The script I will use when the urge shows up:",
            "The replacement action I will use first:",
            "One accountability move I will make in the next 24 hours:",
            "The person, tool, or routine that helps me stay on track:",
            "How I will measure progress by tomorrow night:"
        ]
    },
    "work": {
        "mistakes": [
            "Treating work strain like it should stay neatly separated from the rest of your life.",
            "Building a plan that only works on calm weeks instead of real ones.",
            "Ignoring identity loss, overload, or purpose strain because you are still functioning."
        ],
        "worksheet2": [
            "Script I will use word-for-word next time:",
            "The work boundary or reset I need most:",
            "One action I will take in the next 24 hours to lower the load:",
            "The person I need to update, ask, or follow up with:",
            "How I will measure progress by tomorrow night:"
        ]
    },
    "general": {
        "mistakes": [
            "Waiting to feel perfectly ready before taking a useful step.",
            "Trying to solve the whole problem instead of the next part of it.",
            "Thinking about the change without building a follow-through plan."
        ],
        "worksheet2": [
            "Script I will use word-for-word next time:",
            "The first step I will take when this shows up again:",
            "One action I will take in the next 24 hours:",
            "The person I will check in with:",
            "How I will measure success by tomorrow night:"
        ]
    }
}

PROFILE_OVERRIDES = {
    "ch-01": "reactivity",
    "ch-03": "reactivity",
    "ch-04": "reactivity",
    "ch-06": "general",
    "ch-08": "moral",
    "ch-09": "general",
    "ch-11": "general",
    "ch-12": "reactivity",
    "ch-13": "sleep",
    "ch-14": "body",
    "ch-19": "body",
    "ch-20": "body",
    "ch-21": "reactivity",
    "ch-22": "relationship",
    "ch-23": "relationship",
    "ch-24": "relationship",
    "ch-26": "relationship",
    "ch-27": "relationship",
    "ch-28": "general",
    "ch-29": "intimacy",
    "ch-30": "intimacy",
    "ch-31": "intimacy",
    "ch-33": "intimacy",
    "ch-34": "intimacy",
    "ch-35": "intimacy",
    "ch-36": "moral",
    "ch-37": "moral",
    "ch-38": "moral",
    "ch-39": "moral",
    "ch-41": "work",
    "ch-42": "work",
    "ch-45": "work",
    "ch-46": "work",
}


def get_profile(title):
    low = title.lower()
    if any(x in low for x in ["crisis", "suicid", "hopeless"]):
        return "crisis"
    if any(x in low for x in ["anger", "rage", "blow", "short", "overreact", "hypervigilance", "always on", "minefield"]):
        return "reactivity"
    if any(x in low for x in ["sleep", "wake", "nightmare", "apnea", "fatigue", "debt"]):
        return "sleep"
    if any(x in low for x in ["parent", "family", "kid", "home", "relation", "partner", "communication", "repair"]):
        return "relationship"
    if any(x in low for x in ["moral", "shame", "guilt", "faith", "betrayal", "villain"]):
        return "moral"
    if any(x in low for x in ["sex", "intimacy", "desire", "touch", "body image"]):
        return "intimacy"
    if any(x in low for x in ["pain", "tension", "body", "migraine", "headache", "noise", "vision", "balance", "slips"]):
        return "body"
    if any(x in low for x in ["scroll", "habit", "loop", "compul", "dopamine"]):
        return "habit"
    if any(x in low for x in ["work", "identity", "job", "role", "meaning", "transition", "tribe"]):
        return "work"
    return "general"


def replace_section(text, heading, body):
    pattern = re.compile(rf"(^## {re.escape(heading)}\n\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    return pattern.sub(lambda m: m.group(1) + body.strip() + "\n\n", text)


def main():
    fixed = 0
    for path in sorted(CHAPTER_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title_match = re.match(r"# (.+?)\n", text)
        title = title_match.group(1).strip() if title_match else path.stem
        guide_id_match = re.search(r"^Guide ID: (.+)$", text, re.MULTILINE)
        guide_id = guide_id_match.group(1).strip() if guide_id_match else path.stem.split("-")[0] + "-" + path.stem.split("-")[1]
        profile = PROFILE_OVERRIDES.get(guide_id, get_profile(title))
        defaults = PROFILE_DEFAULTS[profile]

        mistakes_body = "\n".join(f"- {item}" for item in defaults["mistakes"])
        worksheet2_body = "Goal: Turn insight into one script and one 24-hour commitment.\n\nPrompts:\n" + "\n".join(f"- {item}" for item in defaults["worksheet2"])

        updated = text
        updated = replace_section(updated, "Common Mistakes To Avoid", mistakes_body)
        updated = replace_section(updated, "Worksheet 2: Action Builder", worksheet2_body)

        if updated != text:
            path.write_text(updated, encoding="utf-8")
            fixed += 1
            print(f"Fixed: {path.name}")

    print(f"Chapter guides repaired: {fixed}")


if __name__ == "__main__":
    main()
