#!/usr/bin/env python3
"""Render the Etsy shop banner HTML to a 1200x300 PNG."""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent

async def main():
    html_path = ROOT / "brand" / "etsy-shop-banner.html"
    out_path = ROOT / "output" / "etsy" / "shop-banner-1200x300.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1400, "height": 500})
        await page.goto(f"file://{html_path}")
        await page.wait_for_load_state("networkidle")
        banner = page.locator(".banner")
        await banner.screenshot(path=str(out_path))
        await browser.close()
        size_kb = os.path.getsize(out_path) / 1024
        print(f"Saved: {out_path}")
        print(f"Size: {size_kb:.0f} KB")
        print(f"Dimensions: 1200x300px")

asyncio.run(main())
