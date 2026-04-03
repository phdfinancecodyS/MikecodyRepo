from playwright.sync_api import sync_playwright
from pathlib import Path

html = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@900&family=Raleway:wght@400;500&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 500px; height: 500px;
    display: flex; align-items: center; justify-content: center;
    background: transparent;
  }
  .logo {
    width: 380px; height: 380px;
    border-radius: 50%;
    border: 3px solid #1a6b6a;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    background: #faf7f2;
  }
  .logo-the {
    font-family: 'Raleway', sans-serif; font-weight: 400;
    font-size: 14px; letter-spacing: 9px;
    text-transform: uppercase; color: #1a6b6a;
    margin-bottom: 2px;
  }
  .logo-ask {
    font-family: 'Montserrat', sans-serif; font-weight: 900;
    font-size: 84px; text-transform: uppercase; color: #1a6b6a;
    line-height: 1.0; letter-spacing: -2px;
  }
  .logo-anyway {
    font-family: 'Montserrat', sans-serif; font-weight: 900;
    font-size: 84px; text-transform: uppercase; color: #d4922a;
    line-height: 1.0; letter-spacing: -2px;
  }
  .logo-line {
    width: 70px; height: 3px;
    background: #d4922a; margin: 10px 0;
  }
  .logo-campaign {
    font-family: 'Raleway', sans-serif; font-weight: 500;
    font-size: 12px; letter-spacing: 9px;
    text-transform: uppercase; color: #1a6b6a;
    margin-top: 2px;
  }
</style>
</head><body>
<div class="logo">
  <div class="logo-the">THE</div>
  <div class="logo-ask">ASK</div>
  <div class="logo-anyway">ANYWAY</div>
  <div class="logo-line"></div>
  <div class="logo-campaign">CAMPAIGN</div>
</div>
</body></html>"""

out = Path('/Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health/output/etsy/logo-500x500.png')
out.parent.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 500, 'height': 500})
    page.set_content(html)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(out), omit_background=True)
    browser.close()

print(f'Saved: {out} ({out.stat().st_size // 1024} KB)')
