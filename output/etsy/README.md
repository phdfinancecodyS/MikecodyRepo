# Etsy Upload System

Two scripts to generate listing data and bulk-upload all 79 Ask Anyway guides to Etsy.

## Quick Start

```bash
# 1. Generate listing data (titles, descriptions, tags, prices)
python3 scripts/etsy_generate_listings.py

# 2. Validate everything before touching Etsy
python3 scripts/etsy_upload.py --dry-run

# 3. Authenticate with Etsy (one-time, opens browser)
python3 scripts/etsy_upload.py --auth-only

# 4. Upload all 79 listings
python3 scripts/etsy_upload.py
```

## Prerequisites

1. **Etsy Developer Account**  - Register at https://www.etsy.com/developers/your-apps
2. **Create an App**  - Set callback URL to `http://localhost:5555/callback`
3. **Copy your API Key** (the keystring) into `.env`:
   ```
   ETSY_API_KEY=your_keystring_here
   ```
4. **Active Etsy Shop**  - The upload script auto-detects your shop ID
5. **PDFs generated**  - Run `python3 scripts/build_pdf.py --base-guides` first

## Files

| File | Purpose |
|------|---------|
| `scripts/etsy_generate_listings.py` | Generates `output/etsy/listings.json` from guide catalog + markdown |
| `scripts/etsy_upload.py` | OAuth 2.0 auth + bulk listing creation + PDF upload |
| `output/etsy/listings.json` | Generated listing data (review/edit before uploading) |
| `output/etsy/upload_progress.json` | Upload progress tracker (for resume on interrupt) |
| `.etsy_token.json` | OAuth tokens (auto-created, gitignored) |

## Listing Data

Each listing includes:
- **Title**: SEO-optimized, max 140 chars (e.g., "Always On: Your High-Alert Brain - Mental Health Guide + Worksheets - Digital Download PDF")
- **Description**: Hook text from guide + what's included + crisis resources
- **Tags**: 9-12 per listing (6 universal + catalog-specific + domain + cluster)
- **Price**: $6.99
- **Type**: Digital download

## Upload Modes

```bash
# Dry run  - validate without API calls
python3 scripts/etsy_upload.py --dry-run

# Auth only  - authenticate and detect shop ID
python3 scripts/etsy_upload.py --auth-only

# Full upload  - create draft listings + upload PDFs
python3 scripts/etsy_upload.py

# Resume interrupted upload  - skip already-completed listings
python3 scripts/etsy_upload.py --resume

# Custom taxonomy ID (default: 2078)
python3 scripts/etsy_upload.py --taxonomy-id 1234
```

## Taxonomy ID

The default taxonomy ID is 2078. To find the correct one for your category:
1. Authenticate first: `python3 scripts/etsy_upload.py --auth-only`
2. Browse seller taxonomy at https://www.etsy.com/developers/documentation/reference#operation/getSellerTaxonomyNodes
3. Pass it: `python3 scripts/etsy_upload.py --taxonomy-id YOUR_ID`

## Rate Limiting

The upload script stays under Etsy's 10 req/sec limit (~7 req/sec actual). Each listing requires 2 API calls (create listing + upload PDF), so 79 guides = ~158 calls = ~23 seconds.

## After Upload

All listings are created as **drafts**. You'll need to:
1. Add listing images/mockups in Etsy Seller Dashboard
2. Review and publish each listing (or bulk-publish)
3. Set shipping profiles if needed
