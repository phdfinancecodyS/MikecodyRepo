#!/usr/bin/env bash
# =============================================================================
# Ask Anyway: Infrastructure Setup Script
# Run this ONCE to provision all external services.
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()  { echo -e "${YELLOW}[TODO]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; }

ENV_FILE="web/.env.local"

echo "================================================================"
echo "  Ask Anyway: Infrastructure Readiness Check"
echo "================================================================"
echo ""

# ── Check env file exists ────────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
  fail "web/.env.local not found. Copy from template first."
  exit 1
fi
info "web/.env.local exists"

# ── Check each required variable ─────────────────────────────────────────────
check_var() {
  local var_name="$1"
  local val
  val=$(grep "^${var_name}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
  if [[ -z "$val" ]]; then
    warn "$var_name is empty. Needs configuration."
    return 1
  else
    info "$var_name is set"
    return 0
  fi
}

MISSING=0
echo ""
echo "── Supabase ──"
check_var SUPABASE_URL || ((MISSING++))
check_var SUPABASE_SERVICE_KEY || ((MISSING++))

echo ""
echo "── Stripe ──"
check_var STRIPE_SECRET_KEY || ((MISSING++))
check_var STRIPE_WEBHOOK_SECRET || ((MISSING++))
check_var STRIPE_PRICE_IDS || ((MISSING++))

echo ""
echo "── SendGrid ──"
check_var SENDGRID_API_KEY || ((MISSING++))
check_var SENDGRID_FROM_EMAIL || ((MISSING++))

echo ""
echo "── Twilio ──"
check_var TWILIO_ACCOUNT_SID || ((MISSING++))
check_var TWILIO_AUTH_TOKEN || ((MISSING++))
check_var TWILIO_FROM_NUMBER || ((MISSING++))

echo ""
echo "── Analytics (optional) ──"
check_var NEXT_PUBLIC_GA4_MEASUREMENT_ID || true
check_var NEXT_PUBLIC_FB_PIXEL_ID || true

echo ""
echo "── Sentry (optional) ──"
check_var NEXT_PUBLIC_SENTRY_DSN || true

# ── Check Supabase CLI ───────────────────────────────────────────────────────
echo ""
echo "── Supabase Migrations ──"
if command -v supabase &>/dev/null; then
  info "supabase CLI found"
  echo "  To apply migrations:"
  echo "    supabase db push --db-url postgresql://postgres:<password>@<host>:5432/postgres"
else
  warn "supabase CLI not installed. Install: brew install supabase/tap/supabase"
fi

# ── Check Stripe CLI ────────────────────────────────────────────────────────
echo ""
echo "── Stripe Webhook Testing ──"
if command -v stripe &>/dev/null; then
  info "stripe CLI found"
  echo "  To forward webhooks locally:"
  echo "    stripe listen --forward-to localhost:3000/api/webhooks/stripe"
else
  warn "stripe CLI not installed. Install: brew install stripe/stripe-cli/stripe"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "================================================================"
if [[ $MISSING -eq 0 ]]; then
  info "All required variables configured!"
  echo ""
  echo "  Next steps:"
  echo "  1. Apply Supabase migrations"
  echo "  2. Start dev server: cd web && npm run dev"
  echo "  3. Start CCE backend: cd ask-anyway/cce-backend && uvicorn src.app:app"
else
  warn "$MISSING required variable(s) still need configuration."
  echo ""
  echo "  Setup guides:"
  echo "  1. Supabase: https://supabase.com/dashboard -> New Project -> Settings -> API"
  echo "  2. Stripe:   https://dashboard.stripe.com/apikeys"
  echo "     Create products: Guide (\$9), Kit (\$19), SMS (\$4.99/mo), Bundle (\$34)"
  echo "  3. SendGrid: https://app.sendgrid.com/settings/api_keys"
  echo "  4. Twilio:   https://console.twilio.com -> Account Info"
fi
echo "================================================================"
