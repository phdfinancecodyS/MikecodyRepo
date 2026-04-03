import json

SUFFIX = " - Conversation Scripts + Action Plan - Digital PDF"

rewrites = {
    1:  "Still On Alert: When Your Brain Won't Stop Scanning for Danger",
    2:  "On Guard in Your Own Home: Dealing With Hypervigilance",
    6:  "Memory Slips and Brain Fog: When You Can't Remember Like You Used To",
    10: "Sleep Apnea and Snoring: What It's Doing to Your Mind",
    11: "Overwhelmed by Noise, Crowds, and Public Places",
    12: "Dizziness and Motion Sensitivity: What's Happening and What to Do",
    14: "A Stress Communication System for Couples: Red, Yellow, Green",
    15: "After You Said or Did Something Harmful: How to Repair",
    18: "When Family Life Is Falling Apart: Surviving Transitions Together",
    23: "Too Much Pressure Around Touch: How to Talk About It",
    26: "Moral Injury: When You Can't Forgive What You Did or Saw",
    29: "Wrestling With Faith After Trauma: Having the Big Conversations",
    33: "Going It Alone Isn't Working: How to Accept Help Again",
    34: "After the Blowup: How to Repair When You've Lost Your Temper",
    35: "When You Go Cold and Shut Down: How to Reconnect",
    36: "Stuck in Your Head: Breaking the Overthinking Loop",
    37: "Lying Awake Spiraling: What to Do When Anxiety Takes Over at Night",
    38: "When It Feels Hopeless: First Aid for Your Darkest Days",
    39: "How to Talk to Someone in Crisis: Scripts and Action Steps",
    40: "Stuck in Worst-Case Thinking: How to Break Tunnel Vision",
    41: "Can't Focus or Think Straight: How to Reset a Scattered Brain",
    42: "Waking Up From Nightmares: Getting Through the Rest of the Night",
    43: "Waking Up at 3am Every Night: How to Break the Cycle",
    44: "When Chronic Pain Flares: How to Get Through the Day",
    45: "Body Locked Up With Tension: How to Actually Release It",
    46: "TBI and Brain Fog: How to Function on the Hard Days",
    47: "Headaches That Won't Quit: How to Keep Functioning",
    48: "Drinking to Cope: How to Interrupt the Numbing Pattern",
    49: "Relying on Medication to Cope: How to Interrupt the Cycle",
    52: "Breaking a Habit That's Hurting You: How to Reset",
    53: "Stuck in a Shame Spiral: How to Stop the Loop",
    54: "When Shame Is Destroying Your Intimacy: How to Repair",
    55: "After the Disclosure: Repairing Trust When Hard Truths Come Out",
    56: "When the Job Was Who You Were: Life After Work Identity Loss",
    57: "Completely Overwhelmed: How to Stabilize When Everything's Too Much",
    58: "Avoiding Your Finances: How to Break the Money Avoidance Cycle",
    59: "House Is a Disaster: How to Reset When the Chaos Is Winning",
    60: "Can't Stop Scrolling: How to Break the Doom-Scroll Loop",
    61: "Can't Stop: How to Interrupt Compulsive Behaviors",
    65: "Survivor Guilt After Traumatic Calls and Incidents",
    66: "Under Investigation or Complaint: How to Survive the Stress",
    75: "The Caffeine and Sleep Trap: Breaking the Cycle on Shift Work",
    76: "Stress Eating and Skipping Meals: How to Reset",
    79: "The First Year Out: Transition Guide for Newly Separated or Retired",
}

data = json.load(open('output/etsy/listings.json', encoding='utf-8'))
listings = data if isinstance(data, list) else data.get('listings', data)

changed = 0
over_limit = []
for i, listing in enumerate(listings, 1):
    if i in rewrites:
        listing['title'] = rewrites[i] + SUFFIX
        changed += 1
        if len(listing['title']) > 140:
            over_limit.append((i, len(listing['title']), listing['title']))

with open('output/etsy/listings.json', 'w', encoding='utf-8') as f:
    json.dump(listings if isinstance(data, list) else data, f, ensure_ascii=False, indent=2)

print(f"Updated {changed} titles.")
if over_limit:
    print("OVER 140 CHARS:")
    for idx, length, title in over_limit:
        print(f"  {idx:02d} ({length}): {title}")
else:
    print("All titles within 140 char limit.")

# Print all 79 final titles
print("\nFINAL TITLES:")
for i, l in enumerate(listings, 1):
    print(f"{i:02d} ({len(l['title'])}): {l['title']}")
