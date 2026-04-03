"""
Configuration loader for quiz-system JSON configs.
Loads guide catalog, topic-matcher, audience-bucket, recommendation routing,
product catalog, and fulfillment config from the workspace quiz/ directory.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Resolve quiz config directory: prefer QUIZ_CONFIG_DIR env var,
# then fall back to ../../quiz/ relative to this file.
_DEFAULT_QUIZ_DIR = Path(__file__).resolve().parent.parent.parent.parent / "quiz"
QUIZ_DIR = Path(os.getenv("QUIZ_CONFIG_DIR", str(_DEFAULT_QUIZ_DIR)))

# Resolve content directory
_DEFAULT_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "content"
CONTENT_DIR = Path(os.getenv("CONTENT_DIR", str(_DEFAULT_CONTENT_DIR)))


def _load_json(filename: str) -> dict:
    path = QUIZ_DIR / filename
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─── Guide Catalog ─────────────────────────────────────────────────

GUIDE_CATALOG: Dict[str, Any] = _load_json("base-guide-catalog.json")
GUIDES_BY_ID: Dict[str, Any] = {}
GUIDES_BY_DOMAIN: Dict[str, List[Any]] = {}
GUIDES_BY_CLUSTER: Dict[str, List[Any]] = {}

for _g in GUIDE_CATALOG.get("guides", []):
    GUIDES_BY_ID[_g["guide_id"]] = _g
    GUIDES_BY_DOMAIN.setdefault(_g["domain"], []).append(_g)
    GUIDES_BY_CLUSTER.setdefault(_g.get("cluster", "general"), []).append(_g)


# ─── Topic-to-Domain Mapping ──────────────────────────────────────
# Maps CCE topic IDs (anxiety, depression, etc.) to catalog domains
# so the outcome builder can find the right guide.

TOPIC_TO_DOMAIN: Dict[str, str] = {
    "anxiety":       "nervous_system_mood_cognition",
    "depression":    "nervous_system_mood_cognition",
    "trauma":        "nervous_system_mood_cognition",
    "grief":         "moral_injury_guilt_shame_spirituality",
    "relationships": "relationships_family_parenting",
    "family":        "relationships_family_parenting",
    "loneliness":    "relationships_family_parenting",
    "work":          "work_identity_transition",
    "recovery":      "dopamine_habits_addictions",
    "general":       "gap_or_custom",
}

# More specific topic-to-guide mapping for best first match
TOPIC_TO_GUIDE_ID: Dict[str, str] = {
    "anxiety":       "split-03", # Overthinking Loop (anxiety-specific, high priority)
    "depression":    "ch-06",    # Depression and Numbness
    "trauma":        "ch-01",    # Always On: Your High-Alert Brain
    "grief":         "new-03",   # Grief After Suicide Loss (high priority)
    "relationships": "ch-23",    # Repair After Damage (high priority)
    "family":        "ch-24",    # Parenting on Empty
    "loneliness":    "ch-45",    # Loneliness and Loss of Tribe
    "work":          "ch-41",    # Between Worlds: Identity After Role
    "recovery":      "split-15", # Alcohol Numbing Interrupt
    "general":       "new-10",   # How To Ask for Help Without Feeling Weak
    "crisis":        "split-05", # Hopelessness First Aid (safety_first)
}


# ─── Recommendation Routing ───────────────────────────────────────

RECOMMENDATION_CONFIG: Dict[str, Any] = _load_json("recommendation-routing-config.json")
RISK_RULES: Dict[str, Any] = RECOMMENDATION_CONFIG.get("riskRules", {})


# ─── Audience Buckets ─────────────────────────────────────────────

AUDIENCE_CONFIG: Dict[str, Any] = _load_json("audience-bucket-flow.json")
AUDIENCE_BUCKETS: Dict[str, Any] = {}
for _b in AUDIENCE_CONFIG.get("buckets", []):
    AUDIENCE_BUCKETS[_b["id"]] = _b

AUDIENCE_QUESTIONS: List[Any] = AUDIENCE_CONFIG.get("questions", [])


# ─── Product Catalog ──────────────────────────────────────────────

PRODUCT_CATALOG: Dict[str, Any] = _load_json("product-catalog.json")
PRODUCTS_BY_ID: Dict[str, Any] = {}
for _p in PRODUCT_CATALOG.get("products", []):
    PRODUCTS_BY_ID[_p["product_id"]] = _p


# ─── Topic Matcher Flow ──────────────────────────────────────────

TOPIC_MATCHER: Dict[str, Any] = _load_json("topic-matcher-flow.json")
# pricingProfiles is a dict keyed by profile name, each containing product dicts
PRICING_PROFILES: Dict[str, Any] = TOPIC_MATCHER.get("pricingProfiles", {})

ACTIVE_PRICING = TOPIC_MATCHER.get("activePricingProfile", "hub_spoke_default")


# ─── Fulfillment Config ──────────────────────────────────────────

FULFILLMENT_CONFIG: Dict[str, Any] = _load_json("fulfillment-config.json")


# ─── Guide-Offer Mapping (from CSV) ──────────────────────────────
# Per-guide offer routing: primary_offer, secondary_offer, bundle_role

import csv

GUIDE_OFFER_MAP: Dict[str, Dict[str, str]] = {}
_offer_csv = QUIZ_DIR.parent / "planning" / "GUIDE-OFFER-MAPPING.csv"
if _offer_csv.exists():
    with open(_offer_csv, encoding="utf-8") as _f:
        for _row in csv.DictReader(_f):
            GUIDE_OFFER_MAP[_row["guide_id"]] = {
                "primary_offer": _row.get("primary_offer", "guide"),
                "secondary_offer": _row.get("secondary_offer", "sms"),
                "bundle_role": _row.get("bundle_role", "practical_support"),
            }


# ─── Quiz Scoring Config ──────────────────────────────────────────

QUIZ_CONTENT: Dict[str, Any] = _load_json("quiz-content.json")
QUIZ_SCORING_RANGES: List[Any] = QUIZ_CONTENT.get("scoring", {}).get("ranges", [])
QUIZ_SCORING_OVERRIDES: List[Any] = QUIZ_CONTENT.get("scoring", {}).get("overrides", [])


# ─── Etsy Listing IDs ────────────────────────────────────────────

ETSY_LISTINGS: Dict[str, int] = {}
_etsy_progress = QUIZ_DIR.parent / "output" / "etsy" / "upload_progress.json"
if _etsy_progress.exists():
    with open(_etsy_progress, encoding="utf-8") as _f:
        _etsy_data = json.load(_f)
        for _gid, _info in _etsy_data.get("completed", {}).items():
            ETSY_LISTINGS[_gid] = _info.get("listing_id", 0)


# ─── Content Path Resolver ────────────────────────────────────────

def resolve_guide_path(guide_id: str, audience_bucket: Optional[str] = None) -> Optional[Path]:
    """Resolve filesystem path for a guide, with optional audience variant."""
    guide = GUIDES_BY_ID.get(guide_id)
    if not guide:
        return None

    if audience_bucket and audience_bucket != "general-mental-health":
        # Try audience-specific variant
        base_filename = Path(guide["base_path"]).name
        variant_path = CONTENT_DIR / "topic-guides" / "audience-slants" / audience_bucket / base_filename
        if variant_path.exists():
            return variant_path

    # Fall back to base guide
    base_path = CONTENT_DIR.parent / guide["base_path"]
    if base_path.exists():
        return base_path

    return None


def get_guide_for_topic(topic_id: str) -> Optional[Dict[str, Any]]:
    """Return the best-matched guide entry for a CCE topic."""
    guide_id = TOPIC_TO_GUIDE_ID.get(topic_id)
    if guide_id:
        return GUIDES_BY_ID.get(guide_id)

    domain = TOPIC_TO_DOMAIN.get(topic_id, "gap_or_custom")
    guides = GUIDES_BY_DOMAIN.get(domain, [])
    if guides:
        # Prefer high-priority guides
        high = [g for g in guides if g.get("priority") == "high"]
        return high[0] if high else guides[0]

    return None


def get_offer_for_risk(risk_level: str) -> Dict[str, Any]:
    """Return the offer configuration for a given risk level."""
    rule = RISK_RULES.get(risk_level, {})
    default_offer = rule.get("defaultPrimaryOffer", "guide")
    # PRICING_PROFILES is {profile_name: {product_key: {price, billing, ...}}}
    profile = PRICING_PROFILES.get(ACTIVE_PRICING, {})
    price_info = profile.get(default_offer, {})

    product = PRODUCTS_BY_ID.get(default_offer, {})

    return {
        "product_id": default_offer,
        "label": product.get("label", default_offer),
        "description": product.get("description", ""),
        "price": price_info.get("price"),
        "billing": price_info.get("billing", "one_time"),
        "hide_paid_above_fold": rule.get("hidePaidOffersAboveFold", False),
        "force_safety_first": rule.get("forceSafetyFirstLayout", False),
    }


def get_offer_for_guide(guide_id: str, risk_level: str) -> Dict[str, Any]:
    """Return per-guide offer routing with Etsy purchase link."""
    guide_offer = GUIDE_OFFER_MAP.get(guide_id, {})
    primary_key = guide_offer.get("primary_offer", "guide")

    rule = RISK_RULES.get(risk_level, {})
    profile = PRICING_PROFILES.get(ACTIVE_PRICING, {})
    price_info = profile.get(primary_key, {})
    product = PRODUCTS_BY_ID.get(primary_key, {})

    # Etsy listing URL for this guide
    etsy_listing_id = ETSY_LISTINGS.get(guide_id)
    etsy_url = f"https://www.etsy.com/listing/{etsy_listing_id}" if etsy_listing_id else None

    return {
        "product_id": primary_key,
        "label": product.get("label", primary_key),
        "description": product.get("description", ""),
        "price": price_info.get("price"),
        "etsy_price": 6.99,
        "billing": price_info.get("billing", "one_time"),
        "secondary_offer": guide_offer.get("secondary_offer"),
        "bundle_role": guide_offer.get("bundle_role"),
        "etsy_url": etsy_url,
        "etsy_listing_id": etsy_listing_id,
        "hide_paid_above_fold": rule.get("hidePaidOffersAboveFold", False),
        "force_safety_first": rule.get("forceSafetyFirstLayout", False),
    }
