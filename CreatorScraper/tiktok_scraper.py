"""
tiktok_scraper.py
─────────────────
Searches TikTok by hashtag via Apify and returns full creator profiles.
Outputs: handle, followers, following, likes, engagement rate,
         bio, niche tags, video count, profile URL.
"""

import os
import time
import pandas as pd
from apify_client import ApifyClient
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import print as rprint

load_dotenv()
console = Console()

APIFY_TOKEN       = os.getenv("APIFY_API_TOKEN")
HASHTAGS          = [h.strip() for h in os.getenv("TIKTOK_HASHTAGS", "").split(",")]
MIN_FOLLOWERS     = int(os.getenv("MIN_FOLLOWERS", 5000))
MAX_FOLLOWERS     = int(os.getenv("MAX_FOLLOWERS", 1000000))
RESULTS_PER_TAG   = int(os.getenv("RESULTS_PER_HASHTAG", 50))
OUTPUT_FILE       = os.getenv("TIKTOK_OUTPUT", "tiktok_creators.csv")


def calculate_engagement(likes: int, comments: int, shares: int, followers: int) -> float:
    """Engagement rate = (likes + comments + shares) / followers * 100"""
    if followers == 0:
        return 0.0
    return round(((likes + comments + shares) / followers) * 100, 2)


def extract_email_from_bio(bio: str) -> str:
    """Crude email extraction from bio text."""
    import re
    if not bio:
        return ""
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", bio)
    return match.group(0) if match else ""


def tag_niche(bio: str, username: str) -> str:
    """Tag creator niche based on keywords in bio/username."""
    keywords = {
        "therapist":        ["therapist", "lcsw", "lmft", "psychologist", "counselor"],
        "mental health":    ["mental health", "mentalhealth", "mh advocate"],
        "anxiety":          ["anxiety", "anxious", "panic"],
        "depression":       ["depression", "depressed"],
        "wellness":         ["wellness", "wellbeing", "self care", "selfcare"],
        "veteran":          ["veteran", "military", "ptsd", "vets"],
        "grief":            ["grief", "loss", "bereave"],
        "addiction":        ["recovery", "sobriety", "addiction", "sober"],
        "general":          [],
    }
    combined = (bio or "").lower() + " " + (username or "").lower()
    for niche, words in keywords.items():
        if any(w in combined for w in words):
            return niche
    return "general"


def scrape_tiktok_creators() -> pd.DataFrame:
    """
    Uses Apify clockworks/tiktok-scraper to search by hashtag
    and collect creator profile data.
    """
    if not APIFY_TOKEN or APIFY_TOKEN == "your_apify_token_here":
        console.print("[red]❌ APIFY_API_TOKEN not set in .env file[/red]")
        return pd.DataFrame()

    client = ApifyClient(APIFY_TOKEN)
    all_creators = {}  # keyed by username to deduplicate

    console.print(f"\n[cyan]🎵 Starting TikTok scrape across {len(HASHTAGS)} hashtags...[/cyan]\n")

    for hashtag in HASHTAGS:
        console.print(f"  [yellow]→ Searching #{hashtag}...[/yellow]")

        run_input = {
            "hashtags":       [hashtag],
            "resultsPerPage": RESULTS_PER_TAG,
            "maxProfilesPerQuery": RESULTS_PER_TAG,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
            "proxyConfiguration": {"useApifyProxy": True},
        }

        try:
            run = client.actor("clockworks/tiktok-scraper").call(run_input=run_input)
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

            found = 0
            for item in items:
                author = item.get("authorMeta", {})
                username = author.get("name", "")
                followers = author.get("fans", 0)

                # Filter by follower range
                if not MIN_FOLLOWERS <= followers <= MAX_FOLLOWERS:
                    continue

                if username in all_creators:
                    continue  # already have this creator

                stats = item.get("diggCount", 0), item.get("commentCount", 0), item.get("shareCount", 0)
                bio = author.get("signature", "")
                email = extract_email_from_bio(bio)

                all_creators[username] = {
                    "platform":        "TikTok",
                    "handle":          f"@{username}",
                    "profile_url":     f"https://www.tiktok.com/@{username}",
                    "followers":       followers,
                    "following":       author.get("following", 0),
                    "total_likes":     author.get("heart", 0),
                    "video_count":     author.get("video", 0),
                    "avg_engagement":  calculate_engagement(stats[0], stats[1], stats[2], followers),
                    "bio":             bio,
                    "email":           email,
                    "niche":           tag_niche(bio, username),
                    "tier":            get_tier(followers),
                    "found_via":       f"#{hashtag}",
                    "outreach_status": "Not contacted",
                    "flat_fee_est":    flat_fee_estimate(followers),
                    "notes":           "",
                }
                found += 1

            console.print(f"     [green]✓ {found} new creators found[/green]")
            time.sleep(2)  # avoid rate limiting

        except Exception as e:
            console.print(f"     [red]✗ Error on #{hashtag}: {e}[/red]")

    df = pd.DataFrame(list(all_creators.values()))
    if not df.empty:
        df = df.sort_values("followers", ascending=False)

    console.print(f"\n[green]✅ TikTok scrape complete — {len(df)} unique creators found[/green]\n")
    return df


def get_tier(followers: int) -> str:
    if followers < 10_000:   return "Nano"
    if followers < 100_000:  return "Micro"
    if followers < 500_000:  return "Mid-Tier"
    if followers < 1_000_000: return "Macro"
    return "Mega"


def flat_fee_estimate(followers: int) -> str:
    if followers < 10_000:   return "$25-$75"
    if followers < 100_000:  return "$75-$300"
    if followers < 500_000:  return "$300-$1,500"
    if followers < 1_000_000: return "$1,500-$4,000"
    return "$4,000-$20,000"


def save_and_display(df: pd.DataFrame):
    if df.empty:
        console.print("[red]No creators found to save.[/red]")
        return

    df.to_csv(OUTPUT_FILE, index=False)
    console.print(f"[blue]💾 Saved to {OUTPUT_FILE}[/blue]\n")

    # Display summary table
    table = Table(title="TikTok Creators Found", show_lines=True)
    table.add_column("Handle", style="cyan")
    table.add_column("Tier", style="yellow")
    table.add_column("Followers", justify="right")
    table.add_column("Engagement %", justify="right", style="green")
    table.add_column("Niche")
    table.add_column("Email")
    table.add_column("Est. Fee")

    for _, row in df.head(20).iterrows():
        table.add_row(
            row["handle"],
            row["tier"],
            f"{row['followers']:,}",
            f"{row['avg_engagement']}%",
            row["niche"],
            row["email"] or "—",
            row["flat_fee_est"],
        )

    console.print(table)
    console.print(f"\n[dim]Showing top 20 of {len(df)} creators. Full list in {OUTPUT_FILE}[/dim]")


if __name__ == "__main__":
    df = scrape_tiktok_creators()
    save_and_display(df)
