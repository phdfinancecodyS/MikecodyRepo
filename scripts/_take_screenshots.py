"""Take preview screenshots of generated HTML files."""
from playwright.sync_api import sync_playwright
import os

BASE = "/Users/michaeljenkins/Documents/WorkspaceHub/Workspaces/tiktok-mental-health"
OUT = os.path.join(BASE, "output")
W, H = 816, 1056


def shot(page, selector, name, y_offset=0):
    el = page.query_selector(selector)
    if not el:
        print(f"  SKIP {name} (selector not found)")
        return
    el.scroll_into_view_if_needed()
    box = el.bounding_box()
    y = max(0, box["y"] + y_offset)
    page.screenshot(path=f"{OUT}/preview-{name}.png", clip={"x": 0, "y": y, "width": W, "height": H})
    print(f"  OK   {name}")


with sync_playwright() as p:
    browser = p.chromium.launch()

    # Guide
    page = browser.new_page(viewport={"width": W, "height": H})
    page.goto(f"file://{BASE}/output/pdf/ch-01-always-on-your-high-alert-brain.html")
    page.wait_for_load_state("networkidle")

    page.screenshot(path=f"{OUT}/preview-cover.png", clip={"x": 0, "y": 0, "width": W, "height": H})
    print("  OK   cover")

    shot(page, ".worksheet-section", "ws1")
    shot(page, ".crisis-footer", "crisis", y_offset=-200)
    shot(page, ".disclaimer-page", "disclaimer")
    shot(page, ".back-page", "back")

    # Worksheet standalone
    page2 = browser.new_page(viewport={"width": W, "height": H})
    page2.goto(f"file://{BASE}/output/pdf/split-24-overwhelm-stabilization-plan-worksheet-1.html")
    page2.wait_for_load_state("networkidle")

    page2.screenshot(path=f"{OUT}/preview-ws-cover.png", clip={"x": 0, "y": 0, "width": W, "height": H})
    print("  OK   ws-cover")

    shot(page2, ".disclaimer-page", "ws-disclaimer")
    shot(page2, ".back-page", "ws-back")

    browser.close()
    print("Done.")
