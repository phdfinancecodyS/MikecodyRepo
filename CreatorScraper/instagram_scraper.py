"""
instagram_scraper.py
────────────────────
Searches Instagram by hashtag via Apify and returns full creator profiles.
Outputs: handle, followers, following, posts, engagement rate,
         bio, niche tags, profile URL, email if in bio.
"""

import os
import time
import pandas as pd
from apify_client import ApifyClient
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()

APIFY_TOKEN       = os.getenv("APIFY_API_TOKEN")
HASHTAGS          = [h.strip() for h in os.getenv("INSTAGRAM_HASHTAGS", "").split(",")]
MIN_FOLLOWERS     = int(os.getenv("MIN_FOLLOWERS", 5000))
MAX_FOLLOWERS     = int(os.getenv("MAX_FOLLOWERS", 1000000))
RESULTS_PER_TAG   = int(os.getenv("RESULTS_PER_HASHTAG", 50))
OUTPUT_FILE       = os.getenv("INSTAGRAM_OUTPUT", "instagram_creators.csv")


def calculate_engagement(likes: int, comments: int, followers: int) -> float:
    if followers == 0:
        return 0.0
    return round(((likes + comments) / followers) * 100, 2)


def extract_email_from_bio(bio: str) -> str:
    import re
    if not bio:
        return ""
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", bio)
    return match.group(0) if match else ""


def tag_niche(bio: str, username: str) -> str:
    keywords = {
        "therapist":     ["therapist", "lcsw", "lmft", "psychologist", "counselor"],
        "mental health": ["mental health", "mentalhealth", "mh advocate"],
        "anxiety":       ["anxiety", "anxious", "panic"],
        "depression":    ["depression", "depressed"],
        "wellness":      ["wellness", "wellbeing", "self care", "selfcare"],
        "veteran":       ["veteran", "military", "ptsd"],
        "grief":         ["grief", "loss", "bereave"],
        "addiction":     ["recovery", "sobriety", "addiction", "sober"],
    }
    combined = (bio or "").lower() + " " + (username or "").lower()
    for niche, words in keywords.items():
        if any(w in combined for w in words):
            return niche
    return "general"


def get_tier(followers: int) -> str:
    if followers < 10_000:    return "Nano"
    if followers < 100_000:   return "Micro"
    if followers < 500_000:   return "Mid-Tier"
    if followers < 1_000_000: return "Macro"
    return "Mega"


def flat_fee_estimate(followers: int) -> str:
    if followers < 10_000:    return "$25-$75"
    if followers < 100_000:   return "$75-$300"
    if followers < 500_000:   return "$300-$1,500"
    if followers < 1_000_000: return "$1,500-$4,000"
    return "$4,000-$20,000"


def scrape_instagram_creators() -> pd.DataFrame:
    """
    Uses Apify apify/instagram-hashtag-scraper to search by hashtag
    and collect creator profile data.
    """
    if not APIFY_TOKEN or APIFY_TOKEN == "your_apify_token_here":
        console.print("[red]❌ APIFY_API_TOKEN not set in .env file[/red]")
        return pd.DataFrame()

    client = ApifyClient(APIFY_TOKEN)
    all_creators = {}

    console.print(f"\n[magenta]📸 Starting Instagram scrape across {len(HASHTAGS)} hashtags...[/magenta]\n")

    for hashtag in HASHTAGS:
        console.print(f"  [yellow]→ Searching #{hashtag}...[/yellow]")

        run_input = {
            "hashtags":        [hashtag],
            "resultsLimit":    RESULTS_PER_TAG,
            "scrapePostsUntilDate": "",
            "proxyConfiguration": {"useApifyProxy": True},
        }

        try:
            run = client.actor("apify/instagram-hashtag-scraper").call(run_input=run_input)
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

            found = 0
            for item in items:
                owner = item.get("ownerUsername", "")
                if not owner or owner in all_creators:
                    continue

                # Instagram hashtag scraper gives post-level data
                # We use it to identify creators then aggregate
                followers  = item.get("ownerFollowersCount", 0)
                if not MIN_FOLLOWERS <= followers <= MAX_FOLLOWERS:
                    continue

                likes      = item.get("likesCount", 0)
                comments   = item.get("commentsCount", 0)
                bio        = item.get("ownerBiography", "")
                email      = extract_email_from_bio(bio)

                all_creators[owner] = {
                    "platform":        "Instagram",
                    "handle":          f"@{owner}",
                    "profile_url":     f"https://www.instagram.com/{owner}",
                    "followers":       followers,
                    "following":       item.get("ownerFollowingCount", 0),
                    "total_likes":     likes,
                    "video_count":     item.get("ownerPostsCount", 0),
                    "avg_engagement":  calculate_engagement(likes, comments, followers),
                    "bio":             bio,
                    "email":           email,
                    "niche":           tag_niche(bio, owner),
                    "tier":            get_tier(followers),
                    "found_via":       f"#{hashtag}",
                    "outreach_status": "Not contacted",
                    "flat_fee_est":    flat_fee_estimate(followers),
                    "notes":           "",
                }
                found += 1

            console.print(f"     [green]✓ {found} new creators found[/green]")
            time.sleep(2)

        except Exception as e:
            console.print(f"     [red]✗ Error on #{hashtag}: {e}[/red]")

    df = pd.DataFrame(list(all_creators.values()))
    if not df.empty:
        df = df.sort_values("followers", ascending=False)

    console.print(f"\n[green]✅ Instagram scrape complete — {len(df)} unique creators found[/green]\n")
    return df


def save_and_display(df: pd.DataFrame):
    if df.empty:
        console.print("[red]No creators found to save.[/red]")
        return

    df.to_csv(OUTPUT_FILE, index=False)
    console.print(f"[blue]💾 Saved to {OUTPUT_FILE}[/blue]\n")

    table = Table(title="Instagram Creators Found", show_lines=True)
    table.add_column("Handle", style="magenta")
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
    df = scrape_instagram_creators()
    save_and_display(df)
