# Creator Scraper  - TikTok & Instagram Affiliate Finder

Finds mental health creators on TikTok and Instagram, scores them by
followers/engagement, tags their niche, and exports a full outreach tracker.

---

## Setup (One Time)

### 1. Get a Free Apify Account
- Go to https://apify.com → sign up free
- Go to Settings → Integrations → copy your **API Token**
- Open `.env` and paste your token:
  ```
  APIFY_API_TOKEN=your_token_here
  ```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Your Search (optional)
Edit `.env` to change:
- `TIKTOK_HASHTAGS`  - which hashtags to search
- `INSTAGRAM_HASHTAGS`  - which hashtags to search
- `MIN_FOLLOWERS` / `MAX_FOLLOWERS`  - size filter
- `RESULTS_PER_HASHTAG`  - how many creators per hashtag

---

## Usage

```bash
# Scrape both TikTok + Instagram (recommended)
python run_scraper.py

# TikTok only
python run_scraper.py --tiktok

# Instagram only
python run_scraper.py --instagram

# Regenerate outreach tracker from existing CSVs (no new scraping)
python run_scraper.py --tracker
```

---

## Output Files

| File | What It Is |
|---|---|
| `tiktok_creators.csv` | All TikTok creators found |
| `instagram_creators.csv` | All Instagram creators found |
| `all_creators.csv` | Combined, deduplicated, sorted by followers |
| `outreach_tracker.csv` | Your recruitment CRM  - fill this in as you work |

---

## Outreach Tracker Columns

| Column | How to Use |
|---|---|
| `outreach_status` | Not contacted / Contacted / Responded / Signed / Declined |
| `contact_method` | DM / Email / Collabstr |
| `date_contacted` | When you reached out |
| `response` | Yes / No / No response |
| `deal_type` | Flat / Rev Share / Hybrid |
| `agreed_fee` | What you agreed to pay |
| `rev_share_pct` | % they earn on sales (if rev share) |
| `tracking_link` | yoursite.com/quiz?ref=handle |
| `post_date` | When they posted |
| `post_url` | Link to their video |
| `clicks_driven` | From your analytics |
| `completions` | Quiz completions from their link |
| `sales_driven` | Purchases from their link |
| `revenue_generated` | Dollar value generated |
| `notes` | Anything else |

---

## Recommended Creator Mix (Month 1)

| Tier | Count | Why |
|---|---|---|
| Nano (1k-10k) | 20 | Low cost, test content angles |
| Micro (10k-100k) | 8 | Best ROI, high engagement |
| Mid-Tier (100k-500k) | 2 | Scale what worked |

**Total Month 1 budget estimate: $2,000-$5,000**

---

## Notes on Apify Costs
- Free tier: $5 of compute per month (roughly 100-200 creator profiles)
- Starter: $49/mo (plenty for ongoing monthly scrapes)
- Each actor run costs ~$0.10-$0.50 depending on result count

---

## ⏸ WHERE WE STOPPED  - March 20, 2026

### Status: Ready to Run  - Waiting on Apify Token

Everything is built. The only thing blocking the first run is the Apify API token.

### To Pick Up Next Session:

**Step 1  - Get Apify token (5 min)**
- Go to apify.com → sign up free
- Settings → Integrations → copy Personal API Token

**Step 2  - Paste token into .env**
```
APIFY_API_TOKEN=paste_your_token_here
```

**Step 3  - Run the scraper**
```bash
cd /Users/codysullivan/Documents/CreatorScraper
/usr/bin/python3 run_scraper.py
```

**Step 4  - Review output files**
- `all_creators.csv`  - full creator list
- `outreach_tracker.csv`  - open in Google Sheets, start DM outreach

---

### What's Built So Far

| File | Status |
|---|---|
| `tiktok_scraper.py` | ✅ Complete |
| `instagram_scraper.py` | ✅ Complete |
| `run_scraper.py` | ✅ Complete |
| `.env` | ⚠️ Needs Apify token |
| `all_creators.csv` | ⏳ Generates after first run |
| `outreach_tracker.csv` | ⏳ Generates after first run |

---

### Bigger Picture  - What This Is Part Of

This scraper is Step 1 of the Mental Health Platform affiliate program.

Full business plan is at:
`/Users/codysullivan/Documents/MentalHealthPlatform_BusinessPlan.md`

**Platform products:**
- Free Mental Health Quiz (traffic engine)
- Crisis Kit  - $5
- How to Help Guide  - $10
- Check On Me SMS  - $4.99/mo
- Therapist Directory  - affiliate revenue

**Next build tasks after scraper runs:**
1. Build the quiz (Next.js + Supabase)
2. Stripe payment integration
3. ElevenLabs + D-ID video generation pipeline
4. TikTok bio landing page
5. Deploy to Vercel

**Partner responsibilities:**
- Cody  - business strategy, tech, payments, affiliates (this file)
- Partner  - all content, quiz questions, guides, scripts, clinical accuracy
