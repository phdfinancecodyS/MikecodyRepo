#!/usr/bin/env python3
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE_ROOT = ROOT / "content" / "topic-guides"
TOPIC_CATALOG_PATH = ROOT / "quiz" / "topic-catalog.json"
OUTPUT_GUIDE_CATALOG = ROOT / "quiz" / "base-guide-catalog.json"
OUTPUT_PRODUCT_CATALOG = ROOT / "quiz" / "product-catalog.json"
OUTPUT_ROUTING_CONFIG = ROOT / "quiz" / "recommendation-routing-config.json"
OUTPUT_OFFER_MAPPING = ROOT / "planning" / "GUIDE-OFFER-MAPPING.csv"
AUDIENCE_MANIFEST = ROOT / "planning" / "AUDIENCE-SLANT-MANIFEST.csv"

KEYWORDS = {
    "crisis": ["suicid", "hopeless", "crisis", "safety", "panic", "refuses help", "survivor guilt", "grief after suicide"],
    "relationship": ["partner", "family", "parent", "kids", "communication", "repair", "dating", "co-parent", "home"],
    "sleep": ["sleep", "wake", "nightmare", "3am", "apnea", "fatigue"],
    "body": ["pain", "tension", "headache", "tbi", "brain fog", "balance", "motion", "noise", "crowds", "body image"],
    "habit": ["alcohol", "pill", "habit", "scroll", "compulsion", "doom-scroll", "dopamine", "caffeine", "eating patterns"],
    "work": ["work", "identity", "mission", "meaning", "tribe", "team", "investigation", "returning to work", "underemployed", "money"],
    "moral": ["moral", "shame", "villain", "faith", "betrayed", "guilt"],
    "intimacy": ["desire", "sex", "touch", "intimacy", "disclosure"],
}

CLUSTER_OVERRIDES = {
    "ch-01": "reactivity",
    "ch-03": "reactivity",
    "ch-04": "reactivity",
    "ch-06": "general",
    "ch-08": "moral",
    "ch-09": "general",
    "ch-11": "general",
    "ch-12": "reactivity",
    "ch-13": "sleep",
    "ch-14": "body",
    "ch-19": "body",
    "ch-20": "body",
    "ch-21": "relationship",
    "ch-22": "relationship",
    "ch-23": "relationship",
    "ch-24": "relationship",
    "ch-26": "relationship",
    "ch-27": "relationship",
    "ch-28": "general",
    "ch-29": "intimacy",
    "ch-30": "intimacy",
    "ch-31": "intimacy",
    "ch-33": "intimacy",
    "ch-34": "intimacy",
    "ch-35": "intimacy",
    "ch-36": "moral",
    "ch-37": "moral",
    "ch-38": "moral",
    "ch-39": "moral",
    "ch-41": "work",
    "ch-42": "work",
    "ch-45": "work",
    "ch-46": "work",
    "split-01": "reactivity",
    "split-02": "relationship",
    "split-03": "general",
    "split-04": "sleep",
    "split-05": "crisis",
    "split-06": "crisis",
    "split-07": "general",
    "split-08": "general",
    "split-09": "sleep",
    "split-10": "sleep",
    "split-11": "body",
    "split-12": "body",
    "split-13": "body",
    "split-14": "body",
    "split-15": "habit",
    "split-16": "habit",
    "split-17": "relationship",
    "split-18": "work",
    "split-19": "habit",
    "split-20": "moral",
    "split-21": "intimacy",
    "split-22": "intimacy",
    "split-23": "work",
    "split-24": "work",
    "split-25": "work",
    "split-26": "relationship",
    "split-27": "habit",
    "split-28": "habit",
    "new-01": "crisis",
    "new-02": "body",
    "new-03": "crisis",
    "new-04": "moral",
    "new-05": "work",
    "new-06": "relationship",
    "new-07": "relationship",
    "new-08": "work",
    "new-09": "relationship",
    "new-10": "general",
    "new-11": "crisis",
    "new-12": "crisis",
    "new-13": "habit",
    "new-14": "sleep",
    "new-15": "habit",
    "new-16": "relationship",
    "new-17": "intimacy",
    "new-18": "work",
}


def load_topic_domains():
    data = json.loads(TOPIC_CATALOG_PATH.read_text(encoding="utf-8"))
    mapping = {}
    for topic in data.get("topics", []):
        mapping[f"Ch{topic['chapter']}"] = {
            "chapter_id": topic["id"],
            "domain": topic["domain"],
            "tags": topic.get("tags", []),
        }
    return mapping


def parse_guide(path: Path):
    text = path.read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", text, re.MULTILINE).group(1).strip()
    meta = {}
    for key in ["Status", "Guide ID", "Guide type", "Source", "Batch", "Priority"]:
        match = re.search(rf"^{re.escape(key)}: (.+)$", text, re.MULTILINE)
        meta[key] = match.group(1).strip() if match else ""
    return title, meta


def infer_cluster(title: str, guide_id: str):
    if guide_id in CLUSTER_OVERRIDES:
        return CLUSTER_OVERRIDES[guide_id]
    low = title.lower()
    for cluster, words in KEYWORDS.items():
        if any(word in low for word in words):
            return cluster
    return "general"


def infer_offer_lane(title: str, priority: str, cluster: str):
    low = title.lower()
    if cluster == "crisis" or any(word in low for word in ["crisis", "suicid", "panic", "safety", "hopeless"]):
        return {
            "primary_offer": "kit",
            "secondary_offer": "sms",
            "bundle_role": "safety_first",
        }
    if cluster in {"habit", "work"}:
        return {
            "primary_offer": "bundle",
            "secondary_offer": "sms",
            "bundle_role": "ongoing_support",
        }
    if cluster in {"relationship", "intimacy", "moral"}:
        return {
            "primary_offer": "guide",
            "secondary_offer": "kit",
            "bundle_role": "conversation_tools",
        }
    if cluster in {"sleep", "body"}:
        return {
            "primary_offer": "guide",
            "secondary_offer": "bundle",
            "bundle_role": "regulation_stack",
        }
    return {
        "primary_offer": "guide" if priority == "medium" else "kit",
        "secondary_offer": "sms",
        "bundle_role": "practical_support",
    }


def main():
    topic_domains = load_topic_domains()
    base_guides = []

    for folder in [GUIDE_ROOT / "chapters", GUIDE_ROOT / "splits", GUIDE_ROOT / "new-topics"]:
        for path in sorted(folder.glob("*.md")):
            title, meta = parse_guide(path)
            cluster = infer_cluster(title, meta.get("Guide ID", ""))
            domain_info = topic_domains.get(meta["Source"], {}) if meta.get("Source", "").startswith("Ch") else {}
            offer = infer_offer_lane(title, meta.get("Priority", "medium"), cluster)
            base_guides.append({
                "guide_id": meta.get("Guide ID", ""),
                "title": title,
                "guide_type": meta.get("Guide type", ""),
                "source": meta.get("Source", ""),
                "batch": meta.get("Batch", ""),
                "priority": meta.get("Priority", ""),
                "status": meta.get("Status", ""),
                "base_path": str(path.relative_to(ROOT)),
                "domain": domain_info.get("domain", "gap_or_custom"),
                "chapter_id": domain_info.get("chapter_id"),
                "tags": domain_info.get("tags", []),
                "cluster": cluster,
                "offer_lane": offer,
            })

    guide_catalog = {
        "version": 1,
        "name": "base_guide_catalog",
        "baseGuideCount": len(base_guides),
        "audienceBucketCount": sum(1 for _ in csv.DictReader(AUDIENCE_MANIFEST.open(encoding='utf-8'))) // len(base_guides) if base_guides else 0,
        "guides": base_guides,
    }
    OUTPUT_GUIDE_CATALOG.write_text(json.dumps(guide_catalog, indent=2), encoding="utf-8")

    product_catalog = {
        "version": 1,
        "name": "product_catalog",
        "products": [
            {
                "product_id": "guide",
                "label": "Guide",
                "description": "One focused, fast-win topic guide",
                "pricingProfileKey": "guide",
                "delivery": "digital_download",
            },
            {
                "product_id": "kit",
                "label": "Kit",
                "description": "Guide plus scripts, worksheets, and action tools for harder moments",
                "pricingProfileKey": "kit",
                "delivery": "digital_download",
            },
            {
                "product_id": "sms",
                "label": "Check On Me",
                "description": "Ongoing accountability and reminder texts",
                "pricingProfileKey": "sms",
                "delivery": "subscription_sms",
            },
            {
                "product_id": "bundle",
                "label": "Bundle",
                "description": "Top-matched guides and tools bundled into one easier decision",
                "pricingProfileKey": "bundle",
                "delivery": "digital_bundle_optional_sms",
            },
            {
                "product_id": "free_crisis_resources",
                "label": "Free Crisis Resources",
                "description": "Immediate crisis and therapist support resources",
                "pricingProfileKey": None,
                "delivery": "free_resource",
            }
        ]
    }
    OUTPUT_PRODUCT_CATALOG.write_text(json.dumps(product_catalog, indent=2), encoding="utf-8")

    routing_config = {
        "version": 1,
        "name": "recommendation_routing_config",
        "steps": [
            "score_quiz",
            "assign_risk_level",
            "run_topic_matcher_if_allowed",
            "run_audience_matcher_if_allowed",
            "select_primary_guide",
            "select_primary_offer_lane",
            "attach_overlay_buckets_if_present",
            "render_results_cta_stack",
            "persist_recommendation_event"
        ],
        "riskRules": {
            "low_risk": {
                "allowTopicMatcher": True,
                "allowAudienceMatcher": True,
                "defaultPrimaryOffer": "guide",
                "prependFreeCrisisResources": True,
            },
            "moderate_risk": {
                "allowTopicMatcher": True,
                "allowAudienceMatcher": True,
                "defaultPrimaryOffer": "kit",
                "prependFreeCrisisResources": True,
            },
            "high_risk": {
                "allowTopicMatcher": True,
                "allowAudienceMatcher": True,
                "defaultPrimaryOffer": "kit",
                "prependFreeCrisisResources": True,
                "forceSafetyFirstLayout": True,
            },
            "critical": {
                "allowTopicMatcher": False,
                "allowAudienceMatcher": False,
                "defaultPrimaryOffer": "free_crisis_resources",
                "prependFreeCrisisResources": True,
                "hidePaidOffersAboveFold": True,
            }
        },
        "bucketRules": {
            "maxIdentitySelections": 2,
            "maxContextSelections": 2,
            "maxOverlayBuckets": 2,
            "fallbackBucket": "general-mental-health",
            "preferSpecificOccupationOverBroad": True,
        },
        "outputContracts": {
            "recommendationRecord": [
                "session_id",
                "lead_id",
                "risk_level",
                "matched_guide_id",
                "matched_offer_id",
                "primary_audience_bucket_id",
                "overlay_bucket_ids",
                "why_matched",
                "timestamp"
            ]
        }
    }
    OUTPUT_ROUTING_CONFIG.write_text(json.dumps(routing_config, indent=2), encoding="utf-8")

    with OUTPUT_OFFER_MAPPING.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
            "guide_id", "title", "source", "batch", "priority", "cluster", "domain", "primary_offer", "secondary_offer", "bundle_role"
        ])
        writer.writeheader()
        for item in base_guides:
            writer.writerow({
                "guide_id": item["guide_id"],
                "title": item["title"],
                "source": item["source"],
                "batch": item["batch"],
                "priority": item["priority"],
                "cluster": item["cluster"],
                "domain": item["domain"],
                "primary_offer": item["offer_lane"]["primary_offer"],
                "secondary_offer": item["offer_lane"]["secondary_offer"],
                "bundle_role": item["offer_lane"]["bundle_role"],
            })

    print(f"base_guides={len(base_guides)}")
    print(f"wrote={OUTPUT_GUIDE_CATALOG.relative_to(ROOT)}")
    print(f"wrote={OUTPUT_PRODUCT_CATALOG.relative_to(ROOT)}")
    print(f"wrote={OUTPUT_ROUTING_CONFIG.relative_to(ROOT)}")
    print(f"wrote={OUTPUT_OFFER_MAPPING.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
