#!/usr/bin/env python3
"""
Etsy OAuth 2.0 PKCE helper + bulk listing uploader.

Handles the full OAuth 2.0 authorization code flow with PKCE, then creates
draft listings and uploads PDF files for all 79 Ask Anyway guides.

Prerequisites:
  1. Register an app at https://www.etsy.com/developers/your-apps
  2. Set callback URL to: http://localhost:5555/callback
  3. Copy your API Key (keystring) into .env as ETSY_API_KEY
  4. Run: python3 scripts/etsy_generate_listings.py  (creates listings.json)

Usage:
  # First time: authenticate + upload
  python3 scripts/etsy_upload.py

  # Dry run (no API calls, just validate listings.json)
  python3 scripts/etsy_upload.py --dry-run

  # Resume after interruption (skips already-created listings)
  python3 scripts/etsy_upload.py --resume

  # Re-authenticate only (refresh expired token)
  python3 scripts/etsy_upload.py --auth-only

Environment variables (or .env file):
  ETSY_API_KEY        - Your Etsy app API Key keystring (required)
  ETSY_SHOP_ID        - Your Etsy shop numeric ID (auto-detected after auth)
  ETSY_TAXONOMY_ID    - Seller taxonomy ID for your listings (default: 2078)
"""

import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS_FILE = ROOT / "output" / "etsy" / "listings.json"
TOKEN_FILE = ROOT / ".etsy_token.json"
PROGRESS_FILE = ROOT / "output" / "etsy" / "upload_progress.json"

API_BASE = "https://openapi.etsy.com/v3"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
AUTH_URL = "https://www.etsy.com/oauth/connect"
CALLBACK_PORT = 5555
CALLBACK_URL = f"http://localhost:{CALLBACK_PORT}/callback"

SCOPES = "listings_w listings_r shops_r"
RATE_LIMIT_DELAY = 0.15  # ~7 req/sec (under 10/sec limit)


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def load_env():
    """Load .env file if present."""
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def get_api_key():
    api_key = os.environ.get("ETSY_API_KEY", "")
    if not api_key:
        print("ERROR: ETSY_API_KEY not set.")
        print("  1. Register an app at https://www.etsy.com/developers/your-apps")
        print("  2. Add to .env: ETSY_API_KEY=your_keystring_here")
        sys.exit(1)
    return api_key


def get_shared_secret():
    secret = os.environ.get("ETSY_SHARED_SECRET", "")
    if not secret:
        print("ERROR: ETSY_SHARED_SECRET not set.")
        print("  Add to .env: ETSY_SHARED_SECRET=your_shared_secret_here")
        sys.exit(1)
    return secret


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def generate_pkce():
    """Generate PKCE code_verifier and code_challenge."""
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


# ---------------------------------------------------------------------------
# OAuth 2.0 flow
# ---------------------------------------------------------------------------

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler to capture OAuth callback."""

    auth_code = None
    auth_state = None
    error = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/callback":
            if "code" in params:
                CallbackHandler.auth_code = params["code"][0]
                CallbackHandler.auth_state = params.get("state", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<h2>Authorization successful!</h2>"
                    b"<p>You can close this tab and return to the terminal.</p>"
                )
            elif "error" in params:
                CallbackHandler.error = params.get("error_description", params["error"])[0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h2>Error: {CallbackHandler.error}</h2>".encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass  # Suppress HTTP server logs


def do_oauth_flow(api_key: str) -> dict:
    """Run the full OAuth 2.0 PKCE flow. Returns token dict."""
    verifier, challenge = generate_pkce()
    state = secrets.token_urlsafe(16)

    # Build authorization URL
    params = {
        "response_type": "code",
        "client_id": api_key,
        "redirect_uri": CALLBACK_URL,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    # Start local callback server
    server = http.server.HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    server_thread = threading.Thread(target=server.handle_request, daemon=True)
    server_thread.start()

    print("\n=== Etsy OAuth 2.0 Authorization ===")
    print(f"\nOpen this URL in your browser to authorize:\n")
    print(f"  {auth_url}\n")
    print("Waiting for authorization...")

    # Wait for callback
    server_thread.join(timeout=300)
    server.server_close()

    if CallbackHandler.error:
        print(f"\nAuthorization failed: {CallbackHandler.error}")
        sys.exit(1)

    if not CallbackHandler.auth_code:
        print("\nTimeout: No authorization received within 5 minutes.")
        sys.exit(1)

    # Validate state
    if CallbackHandler.auth_state != state:
        print("\nSecurity error: State mismatch. Possible CSRF attack.")
        sys.exit(1)

    print("Authorization code received! Exchanging for access token...")

    # Exchange code for token
    token_data = {
        "grant_type": "authorization_code",
        "client_id": api_key,
        "redirect_uri": CALLBACK_URL,
        "code": CallbackHandler.auth_code,
        "code_verifier": verifier,
    }

    req = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(token_data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        token = json.loads(resp.read().decode())

    # Save token
    token["obtained_at"] = int(time.time())
    TOKEN_FILE.write_text(json.dumps(token, indent=2))
    print(f"Access token saved to {TOKEN_FILE}")
    print(f"  Token expires in: {token['expires_in']}s")
    print(f"  User ID: {token['access_token'].split('.')[0]}")

    return token


def refresh_token(api_key: str, token: dict) -> dict:
    """Refresh an expired OAuth token."""
    print("Refreshing access token...")
    data = {
        "grant_type": "refresh_token",
        "client_id": api_key,
        "refresh_token": token["refresh_token"],
    }
    req = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        new_token = json.loads(resp.read().decode())

    new_token["obtained_at"] = int(time.time())
    TOKEN_FILE.write_text(json.dumps(new_token, indent=2))
    print("Token refreshed successfully.")
    return new_token


def load_or_auth(api_key: str, force_auth: bool = False) -> dict:
    """Load existing token or run OAuth flow."""
    if not force_auth and TOKEN_FILE.exists():
        token = json.loads(TOKEN_FILE.read_text())
        obtained = token.get("obtained_at", 0)
        expires_in = token.get("expires_in", 3600)
        if time.time() - obtained < expires_in - 60:
            print("Using existing access token.")
            return token
        else:
            # Try refresh
            try:
                return refresh_token(api_key, token)
            except Exception as e:
                print(f"Token refresh failed ({e}), re-authenticating...")

    return do_oauth_flow(api_key)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_request(method: str, path: str, api_key: str, token: str,
                data=None, files=None, shared_secret: str = "") -> dict:
    """Make an authenticated API request to Etsy Open API v3."""
    url = f"{API_BASE}{path}"
    # Etsy v3 requires shared secret appended to keystring in x-api-key
    x_api_key = api_key if not shared_secret else f"{api_key}:{shared_secret}"
    headers = {
        "x-api-key": x_api_key,
        "Authorization": f"Bearer {token}",
    }

    if files:
        # Multipart upload (supports mixed form fields via data + file fields via files)
        boundary = secrets.token_hex(16)
        body = b""
        # Add plain form fields first (if data dict provided alongside files)
        if data:
            for field_name, field_value in data.items():
                body += f"--{boundary}\r\n".encode()
                body += f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'.encode()
                body += str(field_value).encode() + b"\r\n"
        # Add file fields
        for field_name, (filename, file_data, content_type) in files.items():
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
            body += f"Content-Type: {content_type}\r\n\r\n".encode()
            body += file_data + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

    elif data is not None:
        encoded = urllib.parse.urlencode(data, doseq=True)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=encoded.encode(), headers=headers, method=method)

    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  API error {e.code}: {error_body}")
        raise


def get_shop_id(api_key: str, access_token: str, shared_secret: str = "") -> int:
    """Get the authenticated user's shop ID."""
    # Extract user ID from token prefix (format: userid.rest_of_token)
    user_id = access_token.split(".")[0]
    shop = api_request("GET", f"/application/users/{user_id}/shops", api_key, access_token, shared_secret=shared_secret)
    # Response may contain results array or direct shop_id
    if isinstance(shop, dict):
        shop_id = shop.get("shop_id")
        if not shop_id and "results" in shop:
            results = shop["results"]
            if results:
                shop_id = results[0].get("shop_id")
    if not shop_id:
        print("ERROR: Could not find your Etsy shop. Make sure you have an active shop.")
        sys.exit(1)
    return shop_id


# ---------------------------------------------------------------------------
# Upload logic
# ---------------------------------------------------------------------------

def load_progress() -> dict:
    """Load upload progress (for resume capability)."""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"completed": {}, "errors": []}


def save_progress(progress: dict):
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def create_listing(listing: dict, shop_id: int, taxonomy_id: int,
                   api_key: str, access_token: str, shared_secret: str = "") -> int:
    """Create a draft listing and return listing_id."""
    form_data = {
        "quantity": listing["quantity"],
        "title": listing["title"],
        "description": listing["description"],
        "price": listing["price"],
        "who_made": listing["who_made"],
        "when_made": listing["when_made"],
        "is_supply": str(listing["is_supply"]).lower(),
        "taxonomy_id": taxonomy_id,
        "type": listing["type"],
        "tags": listing["tags"],
    }

    result = api_request(
        "POST",
        f"/application/shops/{shop_id}/listings",
        api_key, access_token,
        data=form_data,
        shared_secret=shared_secret,
    )
    return result["listing_id"]


def _sanitize_filename(name: str, max_len: int = 70) -> str:
    """Sanitize filename for Etsy: only letters, numbers, hyphens, underscores, periods. Max 70 chars."""
    import re as _re
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    # Strip invalid chars (keep alphanumeric, hyphen, underscore, period)
    stem = _re.sub(r"[^a-zA-Z0-9_\-]", "", stem)
    ext_part = f".{ext}" if ext else ""
    max_stem = max_len - len(ext_part)
    return stem[:max_stem] + ext_part


def upload_file(listing_id: int, pdf_path: str, shop_id: int,
                api_key: str, access_token: str, shared_secret: str = ""):
    """Upload a PDF file to a listing."""
    full_path = ROOT / pdf_path
    file_data = full_path.read_bytes()
    filename = _sanitize_filename(full_path.name)

    api_request(
        "POST",
        f"/application/shops/{shop_id}/listings/{listing_id}/files",
        api_key, access_token,
        data={"name": filename},
        files={"file": (filename, file_data, "application/pdf")},
        shared_secret=shared_secret,
    )


def upload_images(listing_id: int, guide_id: str, shop_id: int,
                  api_key: str, access_token: str, shared_secret: str = ""):
    """Upload listing images (image-1 through image-4) for a guide."""
    img_dir = ROOT / "output" / "etsy" / "listing-images" / guide_id
    uploaded = 0
    for rank, img_num in enumerate([1, 2, 3, 4], start=1):
        img_path = img_dir / f"image-{img_num}.png"
        if not img_path.exists():
            print(f"    Image {img_num} not found, skipping")
            continue
        file_data = img_path.read_bytes()
        filename = f"{guide_id}-image-{img_num}.png"
        api_request(
            "POST",
            f"/application/shops/{shop_id}/listings/{listing_id}/images",
            api_key, access_token,
            data={"rank": rank},
            files={"image": (filename, file_data, "image/png")},
            shared_secret=shared_secret,
        )
        uploaded += 1
        time.sleep(RATE_LIMIT_DELAY)
    return uploaded


def do_upload(listings: list, shop_id: int, taxonomy_id: int,
              api_key: str, access_token: str, shared_secret: str = "", resume: bool = False):
    """Create all listings and upload PDFs."""
    progress = load_progress() if resume else {"completed": {}, "errors": []}
    total = len(listings)
    created = 0
    skipped = 0
    errors = 0

    print(f"\n=== Uploading {total} listings to shop {shop_id} ===\n")

    for i, listing in enumerate(listings, 1):
        gid = listing["guide_id"]

        # Skip if already completed (resume mode)
        if gid in progress["completed"]:
            skipped += 1
            continue

        print(f"[{i}/{total}] {listing['title'][:60]}...")

        try:
            # Create draft listing
            listing_id = create_listing(listing, shop_id, taxonomy_id,
                                       api_key, access_token, shared_secret)
            print(f"  Created listing {listing_id}")
            time.sleep(RATE_LIMIT_DELAY)

            # Upload PDF
            upload_file(listing_id, listing["pdf_path"], shop_id,
                       api_key, access_token, shared_secret)
            print(f"  Uploaded PDF")
            time.sleep(RATE_LIMIT_DELAY)

            # Upload listing images
            img_count = upload_images(listing_id, gid, shop_id,
                                     api_key, access_token, shared_secret)
            print(f"  Uploaded {img_count} images")

            progress["completed"][gid] = {
                "listing_id": listing_id,
                "title": listing["title"],
            }
            created += 1
            save_progress(progress)

        except Exception as e:
            print(f"  ERROR: {e}")
            progress["errors"].append({"guide_id": gid, "error": str(e)})
            errors += 1
            save_progress(progress)
            time.sleep(1)  # Extra delay after error

    print(f"\n=== Upload Complete ===")
    print(f"  Created: {created}")
    print(f"  Skipped (already done): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Progress saved: {PROGRESS_FILE}")

    if errors:
        print(f"\n  Failed listings:")
        for err in progress["errors"]:
            print(f"    {err['guide_id']}: {err['error']}")


def do_dry_run(listings: list):
    """Validate listings without making API calls."""
    print(f"\n=== DRY RUN: Validating {len(listings)} listings ===\n")
    issues = []

    for listing in listings:
        gid = listing["guide_id"]
        title = listing["title"]
        tags = listing["tags"]
        pdf = ROOT / listing["pdf_path"]

        # Title checks
        if len(title) > 140:
            issues.append(f"{gid}: Title too long ({len(title)} > 140)")
        if title.count(":") > 1:
            issues.append(f"{gid}: Title has multiple colons")
        if title.count("+") > 1:
            issues.append(f"{gid}: Title has multiple + signs")

        # Tag checks
        if len(tags) > 13:
            issues.append(f"{gid}: Too many tags ({len(tags)} > 13)")
        for tag in tags:
            if len(tag) > 20:
                issues.append(f"{gid}: Tag too long: '{tag}' ({len(tag)} > 20)")

        # Price check
        if listing["price"] <= 0:
            issues.append(f"{gid}: Invalid price: {listing['price']}")

        # PDF exists
        if not pdf.exists():
            issues.append(f"{gid}: PDF not found: {listing['pdf_path']}")

        # Description length (Etsy has no strict limit but ~4000 is practical)
        if len(listing["description"]) > 10000:
            issues.append(f"{gid}: Description very long ({len(listing['description'])} chars)")

    if issues:
        print(f"ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("ALL LISTINGS VALID. No issues found.")

    # Stats
    print(f"\n  Total listings: {len(listings)}")
    print(f"  Price: ${listings[0]['price']}")
    print(f"  Listing fees: ${len(listings) * 0.20:.2f}")
    title_lens = [len(l["title"]) for l in listings]
    print(f"  Title lengths: {min(title_lens)}-{max(title_lens)} chars")
    tag_counts = [len(l["tags"]) for l in listings]
    print(f"  Tags: {min(tag_counts)}-{max(tag_counts)} per listing")

    # Sample listing
    print(f"\n--- Sample listing ({listings[0]['guide_id']}) ---")
    sample = listings[0]
    print(f"Title: {sample['title']}")
    print(f"Tags: {sample['tags']}")
    print(f"Description preview:\n{sample['description'][:500]}...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Upload Ask Anyway guides to Etsy")
    parser.add_argument("--dry-run", action="store_true",
                       help="Validate listings without uploading")
    parser.add_argument("--resume", action="store_true",
                       help="Resume interrupted upload (skip completed)")
    parser.add_argument("--auth-only", action="store_true",
                       help="Only authenticate, don't upload")
    parser.add_argument("--upload-files", action="store_true",
                       help="Upload PDFs + images to already-created listings (reads listing IDs from progress file)")
    parser.add_argument("--taxonomy-id", type=int, default=2078,
                       help="Etsy seller taxonomy ID (default: 2078 for digital guides)")
    args = parser.parse_args()

    load_env()

    # Load listings
    if not LISTINGS_FILE.exists():
        print(f"ERROR: {LISTINGS_FILE} not found.")
        print("  Run first: python3 scripts/etsy_generate_listings.py")
        sys.exit(1)

    data = json.loads(LISTINGS_FILE.read_text())
    listings = data["listings"]
    print(f"Loaded {len(listings)} listings from {LISTINGS_FILE}")

    # Dry run mode
    if args.dry_run:
        do_dry_run(listings)
        return

    # Auth
    api_key = get_api_key()
    shared_secret = get_shared_secret()
    token = load_or_auth(api_key, force_auth=args.auth_only)
    access_token = token["access_token"]

    if args.auth_only:
        print("\nAuthentication complete. Token saved.")
        # Also detect shop ID
        try:
            shop_id = get_shop_id(api_key, access_token, shared_secret)
            print(f"Shop ID: {shop_id}")
            print(f"  Add to .env: ETSY_SHOP_ID={shop_id}")
        except Exception as e:
            print(f"Could not detect shop ID: {e}")
        return

    # Get shop ID
    shop_id_str = os.environ.get("ETSY_SHOP_ID", "")
    if shop_id_str:
        shop_id = int(shop_id_str)
    else:
        shop_id = get_shop_id(api_key, access_token, shared_secret)
        print(f"Detected shop ID: {shop_id}")

    # Upload files only mode (for listings already created)
    if args.upload_files:
        progress = load_progress()
        if not progress["completed"]:
            print("ERROR: No listing IDs found in progress file. Run full upload first.")
            sys.exit(1)
        do_upload_files(listings, progress, shop_id, api_key, access_token, shared_secret)
        return

    # Upload
    do_upload(listings, shop_id, args.taxonomy_id,
              api_key, access_token, shared_secret, resume=args.resume)


def do_upload_files(listings: list, progress: dict, shop_id: int,
                    api_key: str, access_token: str, shared_secret: str = ""):
    """Upload PDFs and images to already-created listings."""
    completed = progress["completed"]
    total = len(listings)
    success = 0
    errors = 0

    print(f"\n=== Uploading files to {len(completed)} existing listings ===\n")

    for i, listing in enumerate(listings, 1):
        gid = listing["guide_id"]
        entry = completed.get(gid)
        if not entry:
            print(f"[{i}/{total}] {gid}: No listing ID found, skipping")
            continue

        listing_id = entry["listing_id"]
        if not entry.get("needs_files", True):
            print(f"[{i}/{total}] {gid}: Files already uploaded, skipping")
            continue

        print(f"[{i}/{total}] {listing['title'][:55]}... (ID {listing_id})")

        try:
            # Upload PDF
            upload_file(listing_id, listing["pdf_path"], shop_id,
                       api_key, access_token, shared_secret)
            print(f"  Uploaded PDF")
            time.sleep(RATE_LIMIT_DELAY)

            # Upload images
            img_count = upload_images(listing_id, gid, shop_id,
                                     api_key, access_token, shared_secret)
            print(f"  Uploaded {img_count} images")

            # Mark files as done
            entry["needs_files"] = False
            save_progress(progress)
            success += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1
            time.sleep(1)

    print(f"\n=== File Upload Complete ===")
    print(f"  Success: {success}")
    print(f"  Errors: {errors}")


if __name__ == "__main__":
    main()
