#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "content" / "topic-guides"
OUTPUT_DIR = BASE_DIR / "audience-slants"
MANIFEST_PATH = ROOT / "planning" / "AUDIENCE-SLANT-MANIFEST.csv"

BUCKETS = [
    {
        "id": "christian",
        "label": "Christian",
        "tier": "primary",
        "what_this": "This version is written for people who want practical mental health help that can sit alongside Christian faith, prayer, and church life without turning into a sermon.",
        "happening": "When your faith matters to you, pain often hits two places at once: your nervous system and your beliefs about God, hope, suffering, and support. The goal here isn't to over-spiritualize the problem or ignore faith. It's to tell the truth about what's happening and use support that fits your real life.",
        "step": "Name what's a mental health problem, what's a faith question, and where the two are overlapping so you don't blur them into one knot.",
        "say": [
            "I'm struggling, and I don't need a polished answer right now. I need honest support.",
            "Prayer can be part of this, and I also need practical help."
        ],
        "mistake": "Using spiritual language to avoid the actual problem, the actual action step, or the actual support you need.",
        "worksheet1": "How does faith language help this problem, and where does it make you hide instead of tell the truth?",
        "worksheet2": "What is one support step you can take this week that fits both your faith and your actual mental health needs?"
    },
    {
        "id": "military-veteran",
        "label": "Military / Veteran",
        "tier": "primary",
        "what_this": "This version is written for military and veteran life, where mission, hypervigilance, identity, loss of tribe, and carrying the past all shape how a problem lands.",
        "happening": "Military life trains your body and mind around vigilance, control, performance, and mission. Even after service, those patterns don't disappear just because the environment changed. A lot of the struggle isn't weakness. It's training, injury, loss, and identity still showing up in civilian life.",
        "step": "Ask whether this reaction belongs to your current environment or to training and survival patterns that are still firing after the mission changed.",
        "say": [
            "Part of this is service-related, and I'm not going to shame myself for the fact that it still shows up.",
            "I need support that respects the way training and loss changed me."
        ],
        "mistake": "Expecting civilian routines, relationships, or workplaces to make sense without accounting for service, transition, or loss of tribe.",
        "worksheet1": "Where does training still help you, and where is it creating friction in civilian life or close relationships?",
        "worksheet2": "What is one action this week that supports adjustment without asking you to erase who you were in service?"
    },
    {
        "id": "first-responder",
        "label": "First Responder",
        "tier": "primary",
        "what_this": "This version is written for first responder life, where repeated exposure, shift strain, public pressure, dark humor, and post-incident carryover change how stress works.",
        "happening": "First responder culture teaches you to function under pressure, suppress what's inconvenient, and keep moving. That helps on scene. It doesn't always help off scene. The same skills that keep you effective at work can make home life, sleep, relationships, and emotional recovery a lot harder.",
        "step": "Separate on-scene function from off-scene recovery. What works in the job may be exactly what's breaking things at home.",
        "say": [
            "I know how to perform under pressure. I'm still learning how to come down from it.",
            "The fact that I can do the job doesn't mean the job isn't affecting me."
        ],
        "mistake": "Using competence at work as proof that the stress isn't costing you anything outside the job.",
        "worksheet1": "What parts of the job follow you home most often: irritability, numbness, sleep disruption, scanning, or disconnection?",
        "worksheet2": "What is one recovery practice you can use after shift that helps you come home without bringing the whole scene with you?"
    },
    {
        "id": "general-mental-health",
        "label": "General Mental Health",
        "tier": "fallback",
        "what_this": "This version stays broad and practical so it works if you don't want a specific identity lens on the problem.",
        "happening": "A lot of mental health problems get worse when people overcomplicate them or wait too long to act. The goal is to name the pattern clearly, understand it in plain language, and take one useful next step.",
        "step": "Strip the problem down to what's actually happening this week, not the whole story of your life.",
        "say": [
            "This is real, and I can work with what's in front of me right now.",
            "I don't need a perfect plan to take the next useful step."
        ],
        "mistake": "Staying vague about the problem so long that you can't act on it.",
        "worksheet1": "What part of this problem is most active in your life right now?",
        "worksheet2": "What is the smallest useful action you can take in the next 24 hours?"
    },
    {
        "id": "lgbtq",
        "label": "LGBTQ+",
        "tier": "primary",
        "what_this": "This version is written with LGBTQ+ life in mind, including identity stress, belonging, safety, chosen family, and the extra labor of figuring out where you can fully exhale.",
        "happening": "Mental health problems don't land in a vacuum. If you are LGBTQ+, the issue may be sitting on top of identity stress, rejection history, minority stress, hiding, code-switching, or exhaustion from always reading whether a space is safe. That doesn't mean your identity is the problem. It means the context matters.",
        "step": "Ask whether this problem is being made worse by unsafety, hiding, isolation, or being around people who don't actually let you be known.",
        "say": [
            "I need support that doesn't make me shrink, explain myself, or scan the room first.",
            "Part of what makes this harder is the environment, not just me."
        ],
        "mistake": "Treating identity stress like it's irrelevant background noise when it's actively shaping the problem.",
        "worksheet1": "Where do you feel most defended, hidden, or on alert in your current environment?",
        "worksheet2": "What is one way to move toward people, places, or routines where you don't have to perform safety all the time?"
    },
    {
        "id": "high-stress-jobs",
        "label": "High Stress Jobs",
        "tier": "overlay",
        "what_this": "This version is written for people whose work life runs hot: high demand, high stakes, low recovery, and pressure that keeps leaking into the rest of life.",
        "happening": "When work takes a lot out of you, mental health problems often get mislabeled as personality issues or motivation issues. A lot of the strain is cumulative load. Your job may be training your nervous system to stay switched on, rush, perform, and postpone recovery.",
        "step": "Ask how much of this pattern gets worse after deadlines, conflict, overload, or long stretches without real recovery.",
        "say": [
            "Work pressure is shaping this more than I want to admit.",
            "I need support that works in real life, not advice that assumes I have unlimited downtime."
        ],
        "mistake": "Designing a recovery plan that only works on perfect weeks instead of on the weeks you actually live.",
        "worksheet1": "What parts of your job predictably make this problem spike?",
        "worksheet2": "What is one change you can make that fits your real schedule, not an imaginary calmer life?"
    },
    {
        "id": "single-parent",
        "label": "Single Parent",
        "tier": "primary",
        "what_this": "This version is written for single-parent life, where mental health problems hit in the middle of responsibility, no backup, and the pressure to keep functioning even when you're depleted.",
        "happening": "Single-parent stress changes the shape of a problem because there's less margin. You may not get to collapse, sleep in, or hand things off. That means symptoms can get hidden behind competence, and small problems can feel huge because there isn't much buffer.",
        "step": "Ask what this problem costs you as a parent, and where you need support before it becomes a crisis of exhaustion or disconnection.",
        "say": [
            "I'm carrying a lot with very little margin, and that changes what support needs to look like.",
            "I don't need judgment. I need practical help and a realistic plan."
        ],
        "mistake": "Setting a support plan that assumes you have extra time, extra childcare, or extra energy that you don't actually have.",
        "worksheet1": "When does this problem hit hardest in the rhythm of parenting, and what is happening around it?",
        "worksheet2": "What is one support step that would actually reduce your load this week?"
    },
    {
        "id": "healthcare-workers",
        "label": "Healthcare Workers",
        "tier": "primary",
        "what_this": "This version is written for healthcare workers who carry clinical pressure, moral stress, compassion fatigue, shift strain, and the weird tension of caring for everybody while neglecting yourself.",
        "happening": "Healthcare work teaches you to override your own body, emotions, and limits in order to care for other people. That can become a problem fast. You may be good at triaging everyone else while ignoring what is happening in you until it spills over.",
        "step": "Ask whether you're applying professional competence to everyone except yourself, and what it's costing you.",
        "say": [
            "I know how to care for people. I'm not doing a good job of applying that same honesty to myself right now.",
            "This isn't just stress. It's accumulation, moral strain, and not enough recovery."
        ],
        "mistake": "Using clinical knowledge to explain your own problem while still avoiding the practical steps you would recommend to someone else.",
        "worksheet1": "What parts of clinical work or patient care are most connected to this pattern lately?",
        "worksheet2": "What would you tell a colleague in your exact situation, and what keeps you from taking your own advice?"
    },
    {
        "id": "educators",
        "label": "Educators",
        "tier": "primary",
        "what_this": "This version is written for educators dealing with emotional labor, performance pressure, burnout, care overload, and the reality of trying to keep showing up while running low.",
        "happening": "Education work asks for constant emotional output, patience, attention, and management of other people’s needs. That can make mental health problems feel invisible because you're still performing. But being able to teach or lead a room doesn't mean you're okay.",
        "step": "Ask how much of this pattern is tied to the emotional labor of always being on, available, and responsible for the tone of the room.",
        "say": [
            "I can still do the job and still be struggling.",
            "I need support that accounts for emotional labor, not just workload."
        ],
        "mistake": "Using your ability to stay functional in front of others as proof that nothing needs attention.",
        "worksheet1": "Which moments in teaching or school life are most linked to this issue right now?",
        "worksheet2": "What is one boundary or support move that would protect your energy without asking you to stop caring?"
    },
    {
        "id": "social-workers-counselors",
        "label": "Social Workers / Counselors",
        "tier": "overlay",
        "what_this": "This version is written for helpers whose job is to hold pain, track systems, stay regulated for others, and still have a private human nervous system of their own.",
        "happening": "Helping professions make it easy to intellectualize your own distress, normalize overload, or keep functioning because you know how to sound okay. But insight isn't the same as relief. Secondary trauma, compassion fatigue, and system strain can make your own symptoms harder to admit.",
        "step": "Ask where your helper training is helping and where it's actually making it easier to bypass your own needs.",
        "say": [
            "I know the language of this, and I still need real support for my own life.",
            "Insight isn't enough. I need action and recovery too."
        ],
        "mistake": "Confusing professional self-awareness with actual personal recovery.",
        "worksheet1": "How does your role as a helper make this pattern easier to hide or explain away?",
        "worksheet2": "What is one support move you would not hesitate to recommend to a client or colleague in your shoes?"
    },
    {
        "id": "bipoc-racial-trauma",
        "label": "BIPOC / Racial Trauma",
        "tier": "overlay",
        "what_this": "This version is written with racial stress, cultural pressure, belonging, vigilance, and the impact of systemic harm in mind.",
        "happening": "Mental health problems can get heavier when they sit on top of racism, code-switching, cultural pressure, isolation, or the constant question of whether a space is safe. That doesn't mean everything is about race. It means race and racial stress may be increasing the load in ways that matter.",
        "step": "Ask where this problem gets worse because you're carrying extra vigilance, pressure to hold it together, or lack of safe understanding.",
        "say": [
            "Part of this is personal, and part of this is the environment I'm trying to function inside.",
            "I need support that sees the full context, not just my symptoms."
        ],
        "mistake": "Treating systemic stress like it's irrelevant background instead of part of the real load you're carrying.",
        "worksheet1": "Where do you feel most pressure to stay composed, guarded, or unreadable?",
        "worksheet2": "What kind of support would feel culturally safe, honest, and useful right now?"
    },
    {
        "id": "faith-beyond-christian",
        "label": "Faith Beyond Christian",
        "tier": "overlay",
        "what_this": "This version is written for people whose faith, spirituality, or sacred practices matter and should be respected as part of healing without assuming a specifically Christian frame.",
        "happening": "When faith matters to you, mental health problems often carry spiritual questions too: meaning, suffering, discipline, belonging, trust, and how to stay connected without bypassing what is real. The goal isn't to flatten faith into generic wellness or turn everything into doctrine. It's to use what is true and usable.",
        "step": "Separate what needs grounding, action, and support now from the bigger spiritual questions that may take longer to work through.",
        "say": [
            "My faith matters here, and I also need practical help in the real world.",
            "I'm allowed to honor what is sacred to me without pretending that's the only thing I need."
        ],
        "mistake": "Using spiritual practice alone as a substitute for honest problem-solving, support, or safety planning.",
        "worksheet1": "What parts of your faith or spiritual life make you feel steadier, and what parts make you feel pressure right now?",
        "worksheet2": "What is one action you can take that honors your spiritual life and still addresses the actual problem directly?"
    },
    {
        "id": "neurodivergent",
        "label": "Neurodivergent",
        "tier": "primary",
        "what_this": "This version is written with neurodivergent life in mind, including overwhelm, sensory load, executive function strain, rejection sensitivity, masking, and burnout.",
        "happening": "A lot of mental health advice quietly assumes a nervous system and executive function style that you may not have. If you're neurodivergent, the same problem can hit harder because of sensory overload, task switching, time blindness, social effort, or the cost of masking. That doesn't mean you're doing it wrong. It means the plan has to fit your brain.",
        "step": "Ask whether this problem is being intensified by sensory overload, masking, executive friction, or the cost of trying to function in a way that doesn't fit you.",
        "say": [
            "I need a plan that fits how my brain actually works, not advice built for someone else’s system.",
            "Some of this isn't laziness or avoidance. It's executive and sensory load."
        ],
        "mistake": "Using shame to force yourself into systems, routines, or expectations that are already failing your nervous system.",
        "worksheet1": "What parts of this problem are really about overload, task friction, masking, or recovery time?",
        "worksheet2": "What support, cue, or environmental change would make the next step easier for your actual brain?"
    },
    {
        "id": "grief-loss",
        "label": "Grief / Loss",
        "tier": "primary",
        "what_this": "This version is written for people carrying grief, fresh loss, old loss that is still active, or the kind of missing that changes how every other problem lands.",
        "happening": "Grief changes the shape of everything. It lowers capacity, intensifies loneliness, scrambles concentration, and can make normal stress feel enormous. It also doesn't move in a straight line. The goal isn't to rush you past grief. It's to help you function while grief is still part of the room.",
        "step": "Ask how much of this problem is being amplified by grief load, anniversaries, reminders, or the effort of trying to function while carrying absence.",
        "say": [
            "This problem isn't happening separate from grief. Grief is part of the load right now.",
            "I don't need to be over this to take a useful next step."
        ],
        "mistake": "Judging yourself for reduced capacity without accounting for the real weight of loss.",
        "worksheet1": "How is grief changing your energy, concentration, relationships, or stress tolerance right now?",
        "worksheet2": "What is one way to support yourself this week that respects both the problem and the grief you're carrying?"
    },
    {
        "id": "chronic-illness-chronic-pain",
        "label": "Chronic Illness / Chronic Pain",
        "tier": "overlay",
        "what_this": "This version is written for people whose mental health load is tangled with symptoms, flare cycles, pain, fatigue, uncertainty, and the extra work of living in a body that takes more management.",
        "happening": "Chronic illness and chronic pain change the rules. Energy is less predictable, symptoms can wipe out capacity fast, and a lot of advice doesn't account for the real cost of simply getting through a day. Your mental health is affected by both the condition and the life restriction around it.",
        "step": "Ask where this problem gets sharper during flares, fatigue, pain spikes, or the frustration of not being able to do what you want at the pace you want.",
        "say": [
            "My body is part of this problem, not just the backdrop.",
            "I need a plan that respects energy limits and symptom reality."
        ],
        "mistake": "Setting expectations that ignore pain, fatigue, flare cycles, or the recovery cost of everyday tasks.",
        "worksheet1": "What symptoms, limits, or energy patterns are most connected to this issue?",
        "worksheet2": "What is one action that supports you without pretending your body has more capacity than it does?"
    },
    {
        "id": "young-adult-gen-z",
        "label": "Young Adults / Gen Z",
        "tier": "primary",
        "what_this": "This version is written for young adult life, where identity, money, work, relationships, social comparison, and figuring out who you are all collide at once.",
        "happening": "Young adult problems often get minimized as a phase, but the load is real. You may be building identity, trying to stay afloat financially, dealing with unstable work, comparing yourself online, and making adult decisions without much margin. That changes how stress, shame, and mental health hit.",
        "step": "Ask where this issue is tied to uncertainty about identity, stability, belonging, or comparison pressure rather than just personal weakness.",
        "say": [
            "I'm not behind because I'm struggling. I'm carrying a lot while building a life.",
            "I need help that works in real life, not advice from someone pretending this stage is simple."
        ],
        "mistake": "Treating social comparison and instability like they're minor background issues when they're actively driving stress.",
        "worksheet1": "Where do comparison, instability, or identity pressure show up most strongly in this issue?",
        "worksheet2": "What is one step that moves you toward steadiness instead of just temporary relief?"
    },
    {
        "id": "addiction-recovery",
        "label": "Addiction / Recovery",
        "tier": "primary",
        "what_this": "This version is written for people dealing with addiction, compulsive coping, sobriety, recovery, relapse fear, secrecy, and the work of building a life that doesn't depend on numbing.",
        "happening": "Addiction and recovery change how mental health problems feel because the urge to numb, escape, control, or disappear is always close by. Even if substances or compulsions aren't the main issue today, recovery thinking, shame, secrecy, and relapse fear can still shape the problem hard.",
        "step": "Ask whether this issue is waking up urges to numb, isolate, hide, or tell yourself one slip doesn't matter.",
        "say": [
            "This is the kind of moment that can push me toward old coping, so I need to move early.",
            "I don't need to handle this alone or in secret."
        ],
        "mistake": "Waiting until the urge is loud before using support, structure, or accountability.",
        "worksheet1": "What thoughts, feelings, or situations around this problem make you want to numb out, hide, or go back to old coping?",
        "worksheet2": "What is one recovery-aligned action you can take in the next 24 hours that protects both your mental health and your sobriety?"
    }
]

SECTION_PATTERN = re.compile(r"^## (?P<name>.+?)\n\n(?P<body>.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)


def slug_to_tier(bucket_id):
    for bucket in BUCKETS:
        if bucket["id"] == bucket_id:
            return bucket["tier"]
    return "overlay"


def get_base_guides():
    guides = []
    for folder in [BASE_DIR / "chapters", BASE_DIR / "splits", BASE_DIR / "new-topics"]:
        for file_path in sorted(folder.glob("*.md")):
            guides.append(file_path)
    return guides


def parse_sections(text):
    sections = {}
    for match in SECTION_PATTERN.finditer(text):
        sections[match.group("name").strip()] = match.group("body").strip()
    return sections


def parse_metadata(text):
    title_match = re.match(r"# (.+?)\n", text)
    title = title_match.group(1).strip() if title_match else "Untitled"
    metadata = {}
    for key in ["Status", "Guide ID", "Guide type", "Source", "Batch", "Priority"]:
        match = re.search(rf"^{re.escape(key)}: (.+)$", text, re.MULTILINE)
        metadata[key] = match.group(1).strip() if match else ""
    return title, metadata


def parse_numbered_list(section_body):
    items = []
    for line in section_body.splitlines():
        match = re.match(r"\d+\.\s+(.*)", line.strip())
        if match:
            items.append(match.group(1).strip())
    return items


def parse_bullets(section_body):
    items = []
    for line in section_body.splitlines():
        match = re.match(r"-\s+(.*)", line.strip())
        if match:
            items.append(match.group(1).strip())
    return items


def format_numbered(items):
    return "\n".join(f"{idx + 1}. {item}" for idx, item in enumerate(items))


def format_bullets(items):
    return "\n".join(f"- {item}" for item in items)


def inject_worksheet_prompt(section_body, prompt):
    if not prompt:
        return section_body
    lines = section_body.splitlines()
    if prompt not in section_body:
        lines.append(f"- {prompt}")
    return "\n".join(lines).strip()


def build_variant(base_path, bucket):
    text = base_path.read_text(encoding="utf-8")
    title, metadata = parse_metadata(text)
    sections = parse_sections(text)

    what_this = sections.get("What This Helps With", "").strip()
    what_happening = sections.get("What Is Happening", "").strip()
    what_to_do_items = parse_numbered_list(sections.get("What To Do Now", ""))
    what_to_say_items = parse_bullets(sections.get("What To Say", ""))
    mistakes_items = parse_bullets(sections.get("Common Mistakes To Avoid", ""))
    action_plan = sections.get("24-Hour Action Plan", "").strip()

    # Find worksheet sections by prefix (titles may be topic-specific)
    ws1_name = None
    ws1_body = ""
    ws2_name = None
    ws2_body = ""
    for sec_name, sec_body in sections.items():
        if sec_name.startswith("Worksheet 1"):
            ws1_name = sec_name
            ws1_body = sec_body.strip()
        elif sec_name.startswith("Worksheet 2"):
            ws2_name = sec_name
            ws2_body = sec_body.strip()
    if ws1_name is None:
        ws1_name = "Worksheet 1: Pattern Finder"
    if ws2_name is None:
        ws2_name = "Worksheet 2: Action Builder"

    adapted_what_this = what_this + "\n" + bucket["what_this"]
    adapted_happening = bucket["happening"] + "\n\n" + what_happening
    adapted_do = [bucket["step"]] + what_to_do_items
    adapted_say = bucket["say"] + what_to_say_items
    adapted_mistakes = [bucket["mistake"]] + mistakes_items
    adapted_plan = action_plan + f"\n- Audience-lens support step: use one support, person, community, or routine that fits {bucket['label'].lower()} life."
    adapted_worksheet1 = inject_worksheet_prompt(ws1_body, bucket["worksheet1"])
    adapted_worksheet2 = inject_worksheet_prompt(ws2_body, bucket["worksheet2"])

    return f"""# {title}

Status: draft_v1_complete
Guide ID: {metadata.get('Guide ID', '')}
Guide type: {metadata.get('Guide type', '')}
Source: {metadata.get('Source', '')}
Batch: {metadata.get('Batch', '')}
Priority: {metadata.get('Priority', '')}
Audience Bucket: {bucket['label']}
Audience Tier: {bucket['tier']}
Base Guide Path: {base_path.relative_to(ROOT)}

## What This Helps With

{adapted_what_this}

## What Is Happening

{adapted_happening}

## What To Do Now

{format_numbered(adapted_do)}

## What To Say

{format_bullets(adapted_say)}

## Common Mistakes To Avoid

{format_bullets(adapted_mistakes)}

## 24-Hour Action Plan

{adapted_plan}

## {ws1_name}

{adapted_worksheet1}

## {ws2_name}

{adapted_worksheet2}
"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base_guides = get_base_guides()
    manifest_rows = []

    for bucket in BUCKETS:
        bucket_dir = OUTPUT_DIR / bucket["id"]
        bucket_dir.mkdir(parents=True, exist_ok=True)
        for base_path in base_guides:
            output_path = bucket_dir / base_path.name
            output_text = build_variant(base_path, bucket)
            output_path.write_text(output_text, encoding="utf-8")
            manifest_rows.append({
                "bucket_id": bucket["id"],
                "bucket_label": bucket["label"],
                "bucket_tier": bucket["tier"],
                "base_file": str(base_path.relative_to(ROOT)),
                "output_file": str(output_path.relative_to(ROOT)),
                "status": "draft_v1_complete"
            })

    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["bucket_id", "bucket_label", "bucket_tier", "base_file", "output_file", "status"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Base guides: {len(base_guides)}")
    print(f"Buckets: {len(BUCKETS)}")
    print(f"Audience variants created: {len(manifest_rows)}")
    print(f"Manifest written: {MANIFEST_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
