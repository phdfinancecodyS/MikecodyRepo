# Platform Architecture Blueprint

Date: 2026-03-20
Status: Pre-drafting architecture checkpoint

## Goal

Finish the system architecture, routing, and backend mapping before additional guide drafting work.

## End-to-End Flow

1. User lands on quiz landing page with UTM values.
2. User starts quiz.
3. Quiz session stores answers, score, and risk level.
4. Results page renders immediate risk-based support.
5. Topic matcher runs if allowed by risk rules.
6. Audience matcher runs if allowed by risk rules.
7. Recommendation engine selects:
   - base guide
   - audience-specific guide variant
   - primary offer lane
   - secondary offer lane
8. CTA stack renders with crisis resources always visible.
9. Optional email/SMS capture occurs after results.
10. Checkout creates Stripe session.
11. Webhook triggers digital fulfillment and automations.

## Architecture Layers

### Layer 1: Content System
- 79 base guides
- 17 audience buckets
- 1,343 audience variants
- 2 worksheets per guide

### Layer 2: Matching System
- Risk scorer
- Topic matcher
- Audience matcher
- Recommendation engine

### Layer 3: Commerce System
- Product catalog
- Offer-lane mapping
- Checkout and webhooks
- Fulfillment rules

### Layer 4: Automation System
- Email follow-up
- SMS check-ins
- event logging
- purchase and fulfillment tracking

## Required Assets

### Content Assets
- quiz/base-guide-catalog.json
- planning/AUDIENCE-SLANT-MANIFEST.csv
- planning/GUIDE-OFFER-MAPPING.csv

### Matching Assets
- quiz/topic-matcher-flow.json
- quiz/audience-bucket-flow.json
- quiz/recommendation-routing-config.json
- quiz/api-contracts.json

### Commerce Assets
- quiz/product-catalog.json
- pricingProfiles in quiz/topic-matcher-flow.json

### Implementation Contracts
- planning/QUIZ-IMPLEMENTATION-CONTRACT.md
- planning/BACKEND-SYSTEM-CONTRACT.md
- planning/API-ROUTE-SPECS.md
- planning/TECH-HANDOFF-FOR-CODY.md

## Recommendation Engine Inputs

The engine should evaluate:
- quiz risk level
- topic matcher answers
- audience matcher selections
- base guide catalog metadata
- offer-lane mapping

## Recommendation Engine Outputs

The engine should return:
- matched guide id
- matched guide title
- matched audience bucket
- audience variant asset path
- primary offer id
- secondary offer id
- reason for match
- safety-first flags

## Priority Order For Implementation

1. Quiz persistence and scoring
2. Topic matcher integration
3. Audience matcher integration
4. Recommendation engine
5. Product mapping and checkout
6. Fulfillment and automation
7. Reporting and analytics

## What Is Finished

- Base guide catalog exists
- Audience variant catalog exists
- Audience matcher flow exists
- Offer-lane mapping exists
- Routing config exists
- Backend contract exists

## What Cody Should Build Next

1. Database tables from BACKEND-SYSTEM-CONTRACT.md
2. API endpoints for scoring, matching, recommendation, and checkout
3. Results page recommendation service using quiz/recommendation-routing-config.json
4. Asset resolver that maps base guide id + audience bucket to file path
5. Stripe webhook fulfillment pipeline

## Architecture Lock Rule

No more large-scale guide drafting should happen until:
- this architecture is accepted as the source of truth
- recommendation logic is approved
- backend persistence fields are locked
- Cody confirms implementation feasibility
