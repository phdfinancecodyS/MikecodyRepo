#!/usr/bin/env python3
"""
Generate 4 Etsy listing images per guide (2000×2000 px each).

Image 1 — Thumbnail    : Teal colour block + logo badge + guide title (unique)
Image 2 — Inside Look  : PDF page-1 screenshot inset on warm-white card (unique)
Image 3 — What's Inside: Fixed "5 sections every guide has" template (shared)
Image 4 — Who It's For : Audience bullets grouped by guide category (semi-unique)

Output: output/etsy/listing-images/<guide_id>/image-{1..4}.png

Usage:
    python3 scripts/build_listing_images.py            # all 79
    python3 scripts/build_listing_images.py ch-01      # single guide by id
    python3 scripts/build_listing_images.py --img 1    # only image type 1 for all
"""

import argparse
import json
import sys
import textwrap
from pathlib import Path

import fitz  # pymupdf
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
LISTINGS_PATH = ROOT / "output" / "etsy" / "listings.json"
OUT_BASE = ROOT / "output" / "etsy" / "listing-images"

# ── Brand ────────────────────────────────────────────────────────────────────
TEAL        = "#1a6b6a"
TEAL_DARK   = "#0f4e4d"
TEAL_MID    = "#2a8a89"
AMBER       = "#d4922a"
AMBER_LIGHT = "#e8a840"
WARM_WHITE  = "#faf7f2"
CHARCOAL    = "#2d2d2d"
SLATE       = "#4a5568"
OFF_WHITE   = "#f0ede8"

LOGO_HTML = """
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
     width:110px;height:110px;border-radius:50%;border:3px solid {amber};
     background:{teal_dark};padding:8px;gap:1px;">
  <span style="font-family:'Montserrat',sans-serif;font-weight:900;font-size:8px;
        letter-spacing:3px;color:{amber};text-transform:uppercase;">THE</span>
  <span style="font-family:'Montserrat',sans-serif;font-weight:900;font-size:18px;
        letter-spacing:1px;color:{warm_white};text-transform:uppercase;line-height:1;">ASK</span>
  <span style="font-family:'Montserrat',sans-serif;font-weight:900;font-size:18px;
        letter-spacing:1px;color:{amber};text-transform:uppercase;line-height:1;">ANYWAY</span>
  <span style="font-family:'Montserrat',sans-serif;font-weight:900;font-size:7px;
        letter-spacing:3px;color:{warm_white};text-transform:uppercase;">CAMPAIGN</span>
</div>
""".format(amber=AMBER, teal_dark=TEAL_DARK, warm_white=WARM_WHITE)

FONT_LINK = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&family=Raleway:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">'

# ── Who It's For mapping ─────────────────────────────────────────────────────
WHO_MAP = {
    # chapters (trauma/ptsd cluster)
    "ch-01": ["Anyone whose body won't let them feel safe", "Partners trying to understand hyperarousal", "Therapists looking for take-home tools"],
    "ch-03": ["First responders & veterans at home", "Families walking on eggshells", "Anyone whose guard never seems to come down"],
    "ch-04": ["People who explode first, regret later", "Partners on the receiving end of outbursts", "Parents trying to model emotional control"],
    "ch-06": ["Anyone going through the motions feeling nothing", "Loved ones trying to reach someone who's shut down", "People who used to feel more alive"],
    "ch-08": ["People trapped in shame loops", "Survivors of any kind of loss or failure", "Clinicians treating shame-based presentations"],
    "ch-09": ["People who can't remember who they used to be", "Anyone whose brain fog is affecting relationships", "Caregivers supporting someone with memory issues"],
    "ch-11": ["People paralyzed by too many choices", "Leaders burning out on decision fatigue", "Partners planning around someone's overwhelm"],
    "ch-12": ["People who overreact and can't figure out why", "Loved ones confused by disproportionate responses", "Any high-stress professional"],
    "ch-13": ["Anyone running on fumes and worse each week", "Shift workers and first responders", "Partners managing around someone's exhaustion"],
    "ch-14": ["Anyone whose snoring is wrecking their relationship", "Partners sleeping in separate rooms", "People ignoring sleep apnea symptoms"],
    "ch-19": ["Trauma survivors hypersensitive to crowds", "Anyone who avoids public spaces", "Veterans and first responders post-service"],
    "ch-20": ["Anyone with unexplained dizziness or vestibular issues", "TBI survivors navigating sensory symptoms", "Caregivers supporting someone with motion sensitivity"],
    "ch-21": ["Families where one person's trauma changed everything", "Partners who feel like they live in a minefield", "Anyone trying to make home feel safe again"],
    "ch-22": ["Couples fighting the same fight over and over", "Partners who shut down or escalate under stress", "Anyone who wants a shared language for hard days"],
    "ch-23": ["Couples repairing after a blow-up or betrayal", "Anyone who said something they can't take back", "People who need a roadmap for sincere apology"],
    "ch-24": ["Exhausted parents running on empty", "Single parents without backup", "Partners co-parenting with someone struggling"],
    "ch-26": ["Families where a child absorbed a parent's trauma", "Parents worried about what they're passing on", "School counselors and family therapists"],
    "ch-27": ["Families going through any major life change", "Military and veteran families in transition", "Anyone whose home life is shifting under their feet"],
    "ch-28": ["People who feel nothing and don't know why", "Partners confused by emotional distance", "Anyone recovering from burnout or dissociation"],
    "ch-29": ["Couples navigating mismatched libido", "Anyone whose desire dropped after trauma or stress", "Partners afraid to bring it up"],
    "ch-30": ["Couples where stress is killing intimacy", "Anyone who shuts down sexually when overwhelmed", "Partners trying to stay connected"],
    "ch-31": ["Couples getting back to physical connection after a rough patch", "Trauma survivors navigating avoidance", "Partners who need language for this"],
    "ch-33": ["Couples where touch has become a source of pressure", "Trauma survivors with physical boundaries", "Anyone navigating touch after loss or injury"],
    "ch-34": ["People uncomfortable in their body after injury or illness", "Couples rebuilding physical intimacy", "Anyone whose body image is affecting closeness"],
    "ch-35": ["Couples navigating intimacy after surgery or health change", "Anyone whose illness changed their relationship with their body", "Partners adjusting expectations together"],
    "ch-36": ["Veterans, first responders, and anyone carrying moral weight", "People who can't forgive themselves", "Chaplains and counselors working with moral injury"],
    "ch-37": ["Anyone who feels betrayed by leadership, systems, or institutions", "First responders and veterans who lost faith in the organization", "People processing institutional betrayal"],
    "ch-38": ["People who feel like they became the bad guy", "Anyone processing harm they caused", "Therapists working with shame and perpetration trauma"],
    "ch-39": ["Anyone wrestling with God after trauma", "Believers whose faith cracked under loss", "Chaplains, pastors, and faith community leaders"],
    "ch-41": ["Veterans and first responders transitioning out of service", "Anyone whose identity was tied to a role that ended", "Career counselors and transition coaches"],
    "ch-42": ["Anyone searching for purpose after a major life change", "Veterans and retirees rebuilding meaning", "People in the in-between phase"],
    "ch-45": ["Anyone who feels completely alone since leaving service or a job", "People mourning the loss of their team", "Veterans, first responders, anyone in transition"],
    "ch-46": ["Anyone who struggles to accept help or ask for support", "People transitioning from high-accountability roles", "Partners trying to get through to someone who won't ask"],
    # splits
    "split-01": ["People who explode then hate themselves for it", "Partners living with someone's anger outbursts", "Anyone trying to repair after a blowup"],
    "split-02": ["Partners shut out by someone's emotional walls", "Anyone who goes quiet and can't find the way back", "Couples where one person disappears under stress"],
    "split-03": ["Anyone trapped in their own head at 2am", "People whose overthinking is damaging relationships", "Anyone burned out on their own brain"],
    "split-04": ["Anyone spiraling the moment they lie down", "Insomnia sufferers whose mind won't turn off", "Partners watching someone suffer through anxious nights"],
    "split-05": ["Anyone in the darkest stretch of their life", "Loved ones sitting with someone in despair", "Clinicians looking for a take-home tool"],
    "split-06": ["Anyone trying to help someone in crisis", "People who froze or said the wrong thing before", "First responders, counselors, and concerned family members"],
    "split-07": ["Anyone paralyzed by worst-case thinking", "People who can't see options when stressed", "Partners trying to help without feeding the spiral"],
    "split-08": ["Anyone whose brain feels scattered and broken", "People with ADHD, TBI, or high-stress cognitive fog", "Partners trying to communicate with someone who can't track"],
    "split-09": ["Anyone waking in terror from nightmares", "PTSD survivors and trauma-exposed first responders", "Partners lying next to someone with night terrors"],
    "split-10": ["Anyone locked in the 3am wake cycle", "Shift workers and anyone with disrupted sleep", "Partners watching someone suffer through restless nights"],
    "split-11": ["People managing chronic pain conditions", "Anyone in a pain flare trying to function", "Caregivers supporting someone in chronic pain"],
    "split-12": ["People carrying tension they can't release", "Anyone whose body holds stress physically", "Clients working with somatic therapists"],
    "split-13": ["TBI survivors navigating daily function", "Caregivers of TBI survivors", "Anyone dealing with cognitive symptoms post-injury"],
    "split-14": ["Chronic headache and migraine sufferers", "Anyone trying to stay functional during a pain day", "Partners and caregivers of headache sufferers"],
    "split-15": ["People using alcohol to cope with stress", "Loved ones worried about someone's drinking", "Anyone in early recovery or pre-contemplation"],
    "split-16": ["People leaning on medication or substances to function", "Anyone questioning their relationship with pills", "Loved ones trying to start the conversation"],
    "split-17": ["Partners and spouses of trauma survivors", "Anyone absorbing someone else's emotional weight", "Therapists and counselors working with secondary trauma"],
    "split-18": ["First responder and military teams", "HR and peer-support coordinators", "Managers noticing secondary trauma in their people"],
    "split-19": ["Anyone trying to break a habit that's hurting them", "People in early recovery from any behavior", "Therapists using habit-loop models"],
    "split-20": ["People stuck in shame spirals they can't exit", "Anyone whose inner critic is destroying them", "Therapists using shame-based frameworks"],
    "split-21": ["Couples where shame has destroyed intimacy", "Anyone whose past is blocking closeness", "Partners trying to get through shame without making it worse"],
    "split-22": ["Couples navigating a hard disclosure", "Anyone trying to rebuild trust after truth comes out", "Partners wondering if they can come back from this"],
    "split-23": ["People whose entire identity was their job", "Anyone mourning a career or role that ended", "HR professionals supporting off-boarding transitions"],
    "split-24": ["Anyone drowning in too much at once", "People in crisis mode with no stabilization plan", "Clinicians looking for a take-home stabilization tool"],
    "split-25": ["Anyone avoiding their finances out of shame or fear", "People in financial stress affecting their relationships", "Partners trying to get on the same page about money"],
    "split-26": ["Anyone living in a chaotic, overwhelming home", "People whose environment is making everything worse", "Partners trying to establish shared household routines"],
    "split-27": ["Anyone doom-scrolling their way through depression or anxiety", "People using screens to avoid their life", "Partners frustrated by phone-first behavior"],
    "split-28": ["Anyone stuck in compulsive behaviors they can't stop", "People questioning if their habit has become a problem", "Therapists working with OCD or impulsive presentations"],
    # new topics
    "new-01": ["Anyone who has panic attacks in public", "People terrified of their next episode", "Partners and coworkers who witness panic attacks"],
    "new-02": ["First responders after a traumatic call", "Anyone in the crash that comes after a crisis", "Peer-support teams doing next-day follow-up"],
    "new-03": ["People who lost someone to suicide", "Survivors struggling with the specific grief of loss by suicide", "Counselors supporting suicide-loss survivors"],
    "new-04": ["First responders managing survivor guilt", "Anyone haunted by who didn't make it", "Military veterans carrying the weight of loss"],
    "new-05": ["First responders under investigation or complaint", "Anyone in the fog of administrative stress", "Peer-support coordinators and union reps"],
    "new-06": ["First responders and shift workers in relationships", "Partners of shift workers feeling the strain", "Couples where schedule is destroying connection"],
    "new-07": ["Co-parents trying to stay functional under stress", "Blended families managing high conflict", "Single parents co-parenting with a struggling ex"],
    "new-08": ["Anyone returning to work after mental health leave", "HR professionals supporting a return-to-work plan", "Managers welcoming someone back"],
    "new-09": ["First responders checking in on a struggling teammate", "Peer-support volunteers", "Anyone who wants to have a real conversation at work"],
    "new-10": ["Anyone who was raised to handle it alone", "Veterans and first responders new to asking for support", "Partners trying to get someone to open up"],
    "new-11": ["Anyone without a crisis plan", "People who've been in crisis with no support structure", "Clinicians working on safety planning outside the office"],
    "new-12": ["Loved ones of someone refusing help", "Anyone who's tried everything and hit a wall", "Counselors coaching families on engagement strategies"],
    "new-13": ["Anyone whose screen time is eating their mental health", "People using doom-scroll as an avoidance strategy", "Partners frustrated by partner's device use"],
    "new-14": ["Shift workers and first responders trapped in caffeine-sleep cycles", "Anyone whose sleep and stimulant use has become a loop", "Night-shift workers trying to feel human"],
    "new-15": ["First responders and shift workers with stress eating patterns", "Anyone whose eating is connected to emotion or erratic schedules", "People trying to reset without a diet plan"],
    "new-16": ["First responders and veterans with unsupportive families", "Anyone whose job is misunderstood at home", "Partners trying to bridge the understanding gap"],
    "new-17": ["Veterans and first responders re-entering the dating world", "Anyone trying to form connection while carrying trauma", "Singles wondering if they'll ever let someone in"],
    "new-18": ["Newly separated or retired military and first responders", "Spouses managing the transition alongside their partner", "Transition assistance staff and chaplains"],
}

# ── HTML builders ─────────────────────────────────────────────────────────────

def wrap_title(title: str, max_chars: int = 28) -> str:
    """Wrap title at word boundaries for display."""
    words = title.split()
    lines, current = [], []
    for word in words:
        if sum(len(w) for w in current) + len(current) + len(word) > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "<br>".join(lines)


def html_image1(title: str) -> str:
    """Thumbnail: teal background, logo, title."""
    # Strip the suffix for display
    display = title.replace(" - Conversation Scripts + Action Plan - Digital PDF", "").strip()
    # Split at colon for two-line dramatic effect if present
    if ": " in display:
        part1, part2 = display.split(": ", 1)
    else:
        part1, part2 = None, display

    part2_wrapped = wrap_title(part2, 22)

    part1_html = f"""
      <p style="font-family:'Montserrat',sans-serif;font-weight:700;font-size:28px;
         color:{AMBER};text-transform:uppercase;letter-spacing:2px;margin:0 0 12px;
         line-height:1.2;">{part1}:</p>
    """ if part1 else ""

    return f"""<!DOCTYPE html><html><head>{FONT_LINK}
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ width:2000px; height:2000px; background:{TEAL}; display:flex; align-items:center; justify-content:center; }}
.card {{ width:2000px; height:2000px; background:linear-gradient(160deg,{TEAL} 0%,{TEAL_DARK} 100%);
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  padding:120px 140px; gap:0; position:relative; }}
.top-accent {{ position:absolute; top:0; left:0; right:0; height:12px; background:{AMBER}; }}
.bottom-accent {{ position:absolute; bottom:0; left:0; right:0; height:12px; background:{AMBER}; }}
.side-accent {{ position:absolute; left:0; top:0; bottom:0; width:12px; background:{AMBER}; }}
.side-accent-r {{ position:absolute; right:0; top:0; bottom:0; width:12px; background:{AMBER}; }}
.logo-wrap {{ margin-bottom:60px; }}
h1 {{ font-family:'Montserrat',sans-serif; font-weight:900; font-size:96px; color:{WARM_WHITE};
  text-align:center; line-height:1.1; text-transform:uppercase; letter-spacing:1px; margin:0 0 30px; }}
.tagline {{ font-family:'Raleway',sans-serif; font-weight:400; font-size:36px; color:{AMBER_LIGHT};
  text-align:center; letter-spacing:2px; margin-top:40px; }}
.divider {{ width:120px; height:4px; background:{AMBER}; margin:40px auto; border-radius:2px; }}
.badge {{ font-family:'Montserrat',sans-serif; font-weight:700; font-size:22px; color:{TEAL_DARK};
  background:{AMBER}; padding:12px 36px; border-radius:40px; text-transform:uppercase;
  letter-spacing:2px; margin-top:50px; }}
</style></head><body>
<div class="card">
  <div class="top-accent"></div><div class="bottom-accent"></div>
  <div class="side-accent"></div><div class="side-accent-r"></div>
  <div class="logo-wrap">{LOGO_HTML}</div>
  {part1_html}
  <h1>{part2_wrapped}</h1>
  <div class="divider"></div>
  <div class="tagline">Conversation Scripts + Action Plan</div>
  <div class="badge">Instant Download · PDF</div>
</div>
</body></html>"""


def html_image3() -> str:
    """Shared 'What's Inside' template."""
    sections = [
        ("01", "What's Actually Happening", "Plain-language breakdown of what this looks and feels like — no diagnoses, no jargon."),
        ("02", "Exact Scripts and Phrases", "Word-for-word lines you can say out loud — to start, stay in, and follow through on the conversation."),
        ("03", "What NOT to Say", "The well-meaning things that close the conversation, and what to say instead."),
        ("04", "24-Hour Action Plan", "Three concrete steps you can take today, before you lose the moment."),
        ("05", "Crisis Resources", "988 Lifeline, Crisis Text Line, and guidance on when to escalate — always included, never skipped."),
    ]
    items_html = ""
    for num, title, desc in sections:
        items_html += f"""
        <div style="display:flex;gap:36px;align-items:flex-start;padding:36px 0;
             border-bottom:1px solid {OFF_WHITE};">
          <div style="min-width:72px;height:72px;border-radius:50%;background:{AMBER};
               display:flex;align-items:center;justify-content:center;
               font-family:'Montserrat',sans-serif;font-weight:900;font-size:26px;
               color:{TEAL_DARK};">{num}</div>
          <div>
            <p style="font-family:'Montserrat',sans-serif;font-weight:700;font-size:38px;
               color:{TEAL_DARK};margin:0 0 10px;">{title}</p>
            <p style="font-family:'Raleway',sans-serif;font-weight:400;font-size:30px;
               color:{SLATE};line-height:1.5;margin:0;">{desc}</p>
          </div>
        </div>"""

    return f"""<!DOCTYPE html><html><head>{FONT_LINK}
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ width:2000px; height:2000px; background:{WARM_WHITE}; }}
.card {{ width:2000px; height:2000px; background:{WARM_WHITE}; padding:100px 120px;
  display:flex; flex-direction:column; }}
.header {{ margin-bottom:60px; }}
h1 {{ font-family:'Montserrat',sans-serif; font-weight:900; font-size:68px; color:{TEAL_DARK};
  text-transform:uppercase; letter-spacing:2px; margin:0; }}
.sub {{ font-family:'Raleway',sans-serif; font-weight:400; font-size:34px; color:{SLATE};
  margin-top:14px; }}
.accent {{ width:100px; height:6px; background:{AMBER}; margin:24px 0 0; border-radius:3px; }}
.footer {{ margin-top:auto; display:flex; align-items:center; gap:24px;
  padding-top:40px; border-top:2px solid {OFF_WHITE}; }}
.footer-text {{ font-family:'Montserrat',sans-serif; font-weight:700; font-size:26px;
  color:{TEAL};letter-spacing:1px; }}
</style></head><body>
<div class="card">
  <div class="header">
    <h1>What's Inside</h1>
    <p class="sub">Every guide includes all five sections below.</p>
    <div class="accent"></div>
  </div>
  {items_html}
  <div class="footer">
    {LOGO_HTML}
    <span class="footer-text">ASK ANYWAY CAMPAIGN · askanywayguides.etsy.com</span>
  </div>
</div>
</body></html>"""


def html_image4(bullets: list[str], title: str) -> str:
    """Who It's For with 3 audience bullets."""
    display = title.replace(" - Conversation Scripts + Action Plan - Digital PDF", "").strip()
    items_html = ""
    for b in bullets:
        items_html += f"""
        <div style="display:flex;gap:48px;align-items:center;
             padding:70px 60px;background:rgba(255,255,255,0.07);
             border-radius:16px;margin-bottom:32px;">
          <div style="min-width:24px;width:24px;height:24px;border-radius:50%;
               background:{AMBER};flex-shrink:0;"></div>
          <p style="font-family:'Raleway',sans-serif;font-weight:600;font-size:46px;
             color:{WARM_WHITE};line-height:1.4;margin:0;">{b}</p>
        </div>"""

    title_display = display[:80] + ("…" if len(display) > 80 else "")
    return f"""<!DOCTYPE html><html><head>{FONT_LINK}
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ width:2000px; height:2000px; background:{TEAL_DARK}; }}
.card {{ width:2000px; height:2000px; background:linear-gradient(160deg,{TEAL_DARK} 0%,{TEAL} 100%); padding:110px 120px;
  display:flex; flex-direction:column; }}
.label {{ font-family:'Montserrat',sans-serif; font-weight:700; font-size:30px;
  color:{AMBER}; text-transform:uppercase; letter-spacing:4px; margin-bottom:24px; }}
h1 {{ font-family:'Montserrat',sans-serif; font-weight:900; font-size:60px;
  color:{WARM_WHITE}; line-height:1.2; margin:0 0 32px; }}
.accent {{ width:100px; height:6px; background:{AMBER}; margin:0 0 70px; border-radius:3px; }}
.footer {{ margin-top:auto; display:flex; align-items:center; gap:24px;
  padding-top:48px; border-top:2px solid rgba(255,255,255,0.15); }}
.footer-text {{ font-family:'Montserrat',sans-serif; font-weight:700; font-size:28px;
  color:{AMBER_LIGHT};letter-spacing:1px; }}
</style></head><body>
<div class="card">
  <p class="label">Who This Is For</p>
  <h1>{title_display}</h1>
  <div class="accent"></div>
  {items_html}
  <div class="footer">
    {LOGO_HTML}
    <span class="footer-text">ASK ANYWAY CAMPAIGN</span>
  </div>
</div>
</body></html>"""


def html_image2_wrapper(pdf_screenshot_path: str, title: str) -> str:
    """Inside Look: embed the PDF page screenshot on a warm-white card."""
    display = title.replace(" - Conversation Scripts + Action Plan - Digital PDF", "").strip()
    return f"""<!DOCTYPE html><html><head>{FONT_LINK}
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ width:2000px; height:2000px; background:{WARM_WHITE}; }}
.card {{ width:2000px; height:2000px; background:{WARM_WHITE}; padding:80px 100px;
  display:flex; flex-direction:column; align-items:center; }}
.header {{ width:100%;display:flex;align-items:center;justify-content:space-between;
  margin-bottom:50px; }}
.header h2 {{ font-family:'Montserrat',sans-serif; font-weight:700; font-size:34px;
  color:{TEAL_DARK}; text-transform:uppercase; letter-spacing:2px; }}
.preview-label {{ font-family:'Raleway',sans-serif; font-weight:600; font-size:30px;
  color:{AMBER}; letter-spacing:2px; }}
.page-img {{ width:1700px; height:1560px; object-fit:cover; object-position:top;
  border:3px solid {OFF_WHITE}; border-radius:8px;
  box-shadow:0 12px 48px rgba(0,0,0,0.12); }}
.footer-note {{ margin-top:auto; font-family:'Raleway',sans-serif; font-weight:400;
  font-size:26px; color:{SLATE}; text-align:center; padding-top:20px; }}
</style></head><body>
<div class="card">
  <div class="header">
    <div>
      <h2>Inside Look</h2>
      <p style="font-family:'Raleway',sans-serif;font-size:26px;color:{SLATE};margin-top:6px;">{display[:60]}{"…" if len(display)>60 else ""}</p>
    </div>
    <span class="preview-label">Page 1 Preview</span>
  </div>
  <img class="page-img" src="file://{pdf_screenshot_path}" />
  <p class="footer-note">Full guide delivered instantly as a ready-to-print PDF.</p>
</div>
</body></html>"""


# ── Renderer ──────────────────────────────────────────────────────────────────

def render_html_to_png(html: str, out_path: Path, pw_page):
    """Write HTML to temp file and screenshot at 2000×2000."""
    tmp = out_path.with_suffix(".tmp.html")
    tmp.write_text(html, encoding="utf-8")
    pw_page.goto(f"file://{tmp.resolve()}", wait_until="networkidle")
    pw_page.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": 2000, "height": 2000})
    tmp.unlink(missing_ok=True)


def screenshot_pdf_page1(pdf_path: Path, out_path: Path) -> bool:
    """Render PDF page 1 to PNG using pymupdf. Returns True on success."""
    try:
      doc = fitz.open(str(pdf_path))
      page = doc[0]
      # Clip to top 65% of page, then render at 2x scale
      rect = page.rect
      clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * 0.65)
      mat = fitz.Matrix(2.0, 2.0)
      pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
      pix.save(str(out_path))
      doc.close()
      return True
    except Exception as e:
      print(f"  PDF screenshot failed for {pdf_path.name}: {e}")
      return False


def process_listing(listing: dict, images: set[int], pw_page, pw_page2=None):
    guide_id = listing["guide_id"]
    title = listing["title"]
    pdf_path = ROOT / listing["pdf_path"]
    out_dir = OUT_BASE / guide_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"  [{guide_id}] {title[:60]}...")

    # Image 1 — Thumbnail
    if 1 in images:
        p = out_dir / "image-1.png"
        render_html_to_png(html_image1(title), p, pw_page)

    # Image 2 — Inside Look (PDF page 1 screenshot)
    if 2 in images:
        p = out_dir / "image-2.png"
        raw_shot = out_dir / "page1-raw.png"
        ok = screenshot_pdf_page1(pdf_path, raw_shot)
        if ok:
            wrapper_html = html_image2_wrapper(str(raw_shot.resolve()), title)
            render_html_to_png(wrapper_html, p, pw_page)
            raw_shot.unlink(missing_ok=True)
        else:
            # Fallback: just use image 1 style with "Preview" label
            print(f"    Falling back to title card for image-2")
            render_html_to_png(html_image1(title), p, pw_page)

    # Image 3 — What's Inside (shared, but copy per listing for upload convenience)
    if 3 in images:
        p = out_dir / "image-3.png"
        shared = OUT_BASE / "_shared" / "image-3.png"
        if shared.exists():
            import shutil
            shutil.copy(shared, p)
        else:
            render_html_to_png(html_image3(), p, pw_page)

    # Image 4 — Who It's For
    if 4 in images:
        p = out_dir / "image-4.png"
        bullets = WHO_MAP.get(guide_id, [
            "Anyone who loves someone struggling",
            "People who don't know what to say",
            "Anyone who wants to help without hurting",
        ])
        render_html_to_png(html_image4(bullets[:3], title), p, pw_page)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("guide_id", nargs="?", help="Single guide ID to process (e.g. ch-01)")
    parser.add_argument("--img", type=int, choices=[1, 2, 3, 4], help="Only generate this image type")
    args = parser.parse_args()

    data = json.loads(LISTINGS_PATH.read_text(encoding="utf-8"))
    listings = data if isinstance(data, list) else data.get("listings", data)

    if args.guide_id:
        listings = [l for l in listings if l["guide_id"] == args.guide_id]
        if not listings:
            print(f"No listing found for guide_id: {args.guide_id}")
            sys.exit(1)

    images = {args.img} if args.img else {1, 2, 3, 4}

    # Pre-render shared image-3 once
    shared_dir = OUT_BASE / "_shared"
    shared_dir.mkdir(parents=True, exist_ok=True)
    shared_img3 = shared_dir / "image-3.png"

    print(f"Building listing images for {len(listings)} guides, image slots: {sorted(images)}")
    print(f"Output: {OUT_BASE}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 2000, "height": 2000})
        page2 = None  # no longer used; PDF rendering via pymupdf

        # Render shared image-3 once
        if 3 in images and not shared_img3.exists():
            print("Rendering shared image-3 (What's Inside)...")
            render_html_to_png(html_image3(), shared_img3, page)
            print(f"  Saved: {shared_img3}")
            print()

        for i, listing in enumerate(listings, 1):
            print(f"[{i:02d}/{len(listings)}] Processing {listing['guide_id']}...")
            process_listing(listing, images, page, page2)

        browser.close()

    # Final count
    all_images = list(OUT_BASE.glob("*/image-*.png"))
    print(f"\nDone. {len(all_images)} images total in {OUT_BASE}")


if __name__ == "__main__":
    main()
