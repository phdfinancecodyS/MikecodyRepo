"""
run_scraper.py
──────────────
Master runner — scrapes TikTok + Instagram, deduplicates,
merges into one master CSV, and generates an outreach tracker.

Usage:
    python run_scraper.py              # scrape both platforms
    python run_scraper.py --tiktok     # TikTok only
    python run_scraper.py --instagram  # Instagram only
    python run_scraper.py --tracker    # generate outreach tracker from existing CSVs
"""

import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

load_dotenv()
console = Console()

COMBINED_OUTPUT  = os.getenv("COMBINED_OUTPUT",  "all_creators.csv")
TIKTOK_OUTPUT    = os.getenv("TIKTOK_OUTPUT",    "tiktok_creators.csv")
INSTAGRAM_OUTPUT = os.getenv("INSTAGRAM_OUTPUT", "instagram_creators.csv")
OUTREACH_TRACKER = os.getenv("OUTREACH_TRACKER", "outreach_tracker.csv")


def print_banner():
    console.print(Panel.fit(
        "[bold cyan]Mental Health Platform — Creator Scraper[/bold cyan]\n"
        "[dim]TikTok + Instagram affiliate recruitment tool[/dim]",
        border_style="cyan"
    ))


def run_tiktok() -> pd.DataFrame:
    from tiktok_scraper import scrape_tiktok_creators
    return scrape_tiktok_creators()


def run_instagram() -> pd.DataFrame:
    from instagram_scraper import scrape_instagram_creators
    return scrape_instagram_creators()


def merge_results(tt_df: pd.DataFrame, ig_df: pd.DataFrame) -> pd.DataFrame:
    """Merge TikTok and Instagram results, sort by followers."""
    frames = [df for df in [tt_df, ig_df] if not df.empty]
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["handle"], keep="first")
    combined = combined.sort_values("followers", ascending=False)
    combined["scraped_date"] = datetime.now().strftime("%Y-%m-%d")
    return combined


def generate_outreach_tracker(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates an outreach tracker from the master creator list.
    Adds columns for your workflow.
    """
    tracker = df[[
        "platform", "handle", "profile_url", "tier",
        "followers", "avg_engagement", "niche",
        "email", "flat_fee_est", "found_via"
    ]].copy()

    tracker["outreach_status"]  = "Not contacted"
    tracker["contact_method"]   = ""        # DM / Email / Collabstr
    tracker["date_contacted"]   = ""
    tracker["response"]         = ""        # Yes / No / No response
    tracker["deal_type"]        = ""        # Flat / Rev Share / Hybrid
    tracker["agreed_fee"]       = ""
    tracker["rev_share_pct"]    = ""
    tracker["tracking_link"]    = ""        # yoursite.com/quiz?ref=handle
    tracker["post_date"]        = ""
    tracker["post_url"]         = ""
    tracker["clicks_driven"]    = ""
    tracker["completions"]      = ""
    tracker["sales_driven"]     = ""
    tracker["revenue_generated"] = ""
    tracker["notes"]            = ""

    return tracker


def print_summary(df: pd.DataFrame):
    if df.empty:
        return

    console.print("\n[bold]📊 Creator Summary[/bold]\n")

    # By platform
    platform_counts = df["platform"].value_counts()
    for platform, count in platform_counts.items():
        console.print(f"  {platform}: [cyan]{count}[/cyan] creators")

    console.print()

    # By tier
    tier_order = ["Nano", "Micro", "Mid-Tier", "Macro", "Mega"]
    tier_counts = df["tier"].value_counts()
    table = Table(title="Creators by Tier", show_lines=False)
    table.add_column("Tier", style="yellow")
    table.add_column("Count", justify="right", style="cyan")
    table.add_column("Est. Cost Per Post")
    table.add_column("Typical Views/Post")

    tier_info = {
        "Nano":     ("$25-$75",        "500-2,000"),
        "Micro":    ("$75-$300",       "5,000-25,000"),
        "Mid-Tier": ("$300-$1,500",    "25,000-100,000"),
        "Macro":    ("$1,500-$4,000",  "100,000-400,000"),
        "Mega":     ("$4,000-$20,000", "400,000-2,000,000"),
    }
    for tier in tier_order:
        if tier in tier_counts:
            cost, views = tier_info.get(tier, ("—", "—"))
            table.add_row(tier, str(tier_counts[tier]), cost, views)
    console.print(table)

    # By niche
    console.print()
    niche_counts = df["niche"].value_counts()
    niche_table = Table(title="Creators by Niche", show_lines=False)
    niche_table.add_column("Niche", style="magenta")
    niche_table.add_column("Count", justify="right", style="cyan")
    for niche, count in niche_counts.items():
        niche_table.add_row(niche.title(), str(count))
    console.print(niche_table)

    # Creators with emails (easiest to contact directly)
    with_email = df[df["email"] != ""]
    console.print(f"\n[green]✉️  {len(with_email)} creators have email addresses in their bio[/green]")
    console.print(f"[dim]These are your easiest direct contacts — no DM needed[/dim]\n")


def main():
    print_banner()

    args = sys.argv[1:]
    do_tiktok    = "--tiktok"    in args or not args or "--tracker" not in args
    do_instagram = "--instagram" in args or not args or "--tracker" not in args
    do_tracker   = "--tracker"   in args or not args

    if "--tiktok" in args and "--instagram" not in args:
        do_instagram = False
    if "--instagram" in args and "--tiktok" not in args:
        do_tiktok = False

    tt_df = pd.DataFrame()
    ig_df = pd.DataFrame()

    # ── Scrape ──
    if do_tiktok and "--tracker" not in args:
        tt_df = run_tiktok()
        if not tt_df.empty:
            tt_df.to_csv(TIKTOK_OUTPUT, index=False)
            console.print(f"[blue]💾 TikTok results saved → {TIKTOK_OUTPUT}[/blue]")

    if do_instagram and "--tracker" not in args:
        ig_df = run_instagram()
        if not ig_df.empty:
            ig_df.to_csv(INSTAGRAM_OUTPUT, index=False)
            console.print(f"[blue]💾 Instagram results saved → {INSTAGRAM_OUTPUT}[/blue]")

    # ── Load existing if generating tracker only ──
    if "--tracker" in args:
        if os.path.exists(TIKTOK_OUTPUT):
            tt_df = pd.read_csv(TIKTOK_OUTPUT)
        if os.path.exists(INSTAGRAM_OUTPUT):
            ig_df = pd.read_csv(INSTAGRAM_OUTPUT)

    # ── Merge ──
    combined = merge_results(tt_df, ig_df)
    if not combined.empty:
        combined.to_csv(COMBINED_OUTPUT, index=False)
        console.print(f"[blue]💾 Combined list saved → {COMBINED_OUTPUT}[/blue]")

    # ── Outreach tracker ──
    if not combined.empty:
        tracker = generate_outreach_tracker(combined)
        tracker.to_csv(OUTREACH_TRACKER, index=False)
        console.print(f"[blue]💾 Outreach tracker saved → {OUTREACH_TRACKER}[/blue]\n")

    # ── Summary ──
    print_summary(combined)

    console.print(Panel.fit(
        f"[bold green]✅ Done![/bold green]\n\n"
        f"[cyan]{COMBINED_OUTPUT}[/cyan] — full creator list\n"
        f"[cyan]{OUTREACH_TRACKER}[/cyan] — your recruitment CRM\n\n"
        "[dim]Open the outreach tracker in Excel or Google Sheets.\n"
        "Fill in contact_method, date_contacted, response as you work.[/dim]",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
