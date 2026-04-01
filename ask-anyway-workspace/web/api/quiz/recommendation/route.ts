// POST /api/quiz/recommendation
// Resolves the final guide, audience-specific asset path, and offer lane
// from the quiz session, topic match, and audience match sessions.
// Persists a guide_recommendations row.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 4

import { createSupabaseServerClient } from '../../_lib/supabase';
import type {
  RecommendationRequest,
  RecommendationResponse,
  ProductId,
  RiskLevel,
} from '../../_lib/types';

// Offer defaults by risk level (from quiz/recommendation-routing-config.json)
const DEFAULT_OFFER_BY_RISK: Record<RiskLevel, ProductId> = {
  low_risk:      'guide',
  moderate_risk: 'kit',
  high_risk:     'kit',
  critical:      'free_crisis_resources',
};

// Secondary offer pairings
const SECONDARY_OFFER: Partial<Record<ProductId, ProductId>> = {
  guide: 'sms',
  kit:   'sms',
  bundle: null as unknown as ProductId,
};

const FALLBACK_BUCKET = 'general-mental-health';
const FALLBACK_GUIDE  = 'general-mental-health-starter';

function buildVariantPath(guideId: string, bucketId: string): string {
  return `content/topic-guides/audience-slants/${bucketId}/${guideId}.md`;
}

export async function POST(req: Request): Promise<Response> {
  let body: RecommendationRequest;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  if (!body.quizSessionId) {
    return Response.json({ error: 'quizSessionId is required' }, { status: 400 });
  }

  const db = createSupabaseServerClient();

  // ── Load quiz_session ──────────────────────────────────────────────────────
  const { data: quizSession, error: quizErr } = await db
    .from('quiz_sessions')
    .select('id, risk_level, lead_id')
    .eq('id', body.quizSessionId)
    .single();

  if (quizErr || !quizSession) {
    return Response.json({ error: 'quiz_session not found' }, { status: 404 });
  }

  const riskLevel = (quizSession.risk_level as RiskLevel) ?? 'low_risk';

  // Critical: no topic/audience matching required; show crisis resources
  if (riskLevel === 'critical') {
    const { data: rec, error: recErr } = await db
      .from('guide_recommendations')
      .insert({
        quiz_session_id:          body.quizSessionId,
        topic_match_session_id:   null,
        audience_match_session_id: null,
        base_guide_id:            FALLBACK_GUIDE,
        audience_variant_path:    null,
        primary_offer_id:         'free_crisis_resources',
        secondary_offer_id:       null,
        bundle_role:              null,
        why_matched_json:         { riskLevel: 'critical' },
      })
      .select('id')
      .single();

    if (recErr) {
      console.error('guide_recommendations insert (critical) error', recErr);
      return Response.json({ error: 'Failed to save recommendation' }, { status: 500 });
    }

    const response: RecommendationResponse = {
      guideRecommendationId: rec.id,
      baseGuideId:           FALLBACK_GUIDE,
      baseGuideTitle:        'Crisis Resources',
      audienceBucketId:      FALLBACK_BUCKET,
      audienceVariantPath:   '',
      primaryOfferId:        'free_crisis_resources',
      secondaryOfferId:      null,
      bundleRole:            null,
      showCrisisResources:   true,
      whyMatched:            { riskLevel: 'critical' },
    };

    return Response.json(response, { status: 200 });
  }

  // ── Load topic_match_session (optional) ───────────────────────────────────
  let topicMatchData: { recommended_guide_ids_json: string[]; recommended_offer_type: string } | null = null;
  if (body.topicMatchSessionId) {
    const { data } = await db
      .from('topic_match_sessions')
      .select('recommended_guide_ids_json, recommended_offer_type')
      .eq('id', body.topicMatchSessionId)
      .single();
    topicMatchData = data ?? null;
  }

  // ── Load audience_match_session (optional) ────────────────────────────────
  let audienceMatchData: { primary_bucket_id: string; overlay_bucket_ids_json: string[] } | null = null;
  if (body.audienceMatchSessionId) {
    const { data } = await db
      .from('audience_match_sessions')
      .select('primary_bucket_id, overlay_bucket_ids_json')
      .eq('id', body.audienceMatchSessionId)
      .single();
    audienceMatchData = data ?? null;
  }

  // ── Resolve guide id ───────────────────────────────────────────────────────
  const recommendedGuideIds: string[] = topicMatchData?.recommended_guide_ids_json ?? [];
  const baseGuideId = recommendedGuideIds[0] ?? FALLBACK_GUIDE;

  // ── Resolve audience bucket ────────────────────────────────────────────────
  const audienceBucketId = audienceMatchData?.primary_bucket_id ?? FALLBACK_BUCKET;

  // ── Resolve offers ─────────────────────────────────────────────────────────
  const primaryOfferId: ProductId =
    (topicMatchData?.recommended_offer_type as ProductId) ?? DEFAULT_OFFER_BY_RISK[riskLevel];
  const secondaryOfferId: ProductId | null = SECONDARY_OFFER[primaryOfferId] ?? null;

  const audienceVariantPath = buildVariantPath(baseGuideId, audienceBucketId);

  const whyMatched = {
    riskLevel,
    guide:    baseGuideId,
    audience: [audienceBucketId, ...(audienceMatchData?.overlay_bucket_ids_json ?? [])],
    offer:    primaryOfferId,
  };

  // ── Persist guide_recommendations ─────────────────────────────────────────
  const { data: rec, error: recErr } = await db
    .from('guide_recommendations')
    .insert({
      quiz_session_id:          body.quizSessionId,
      topic_match_session_id:   body.topicMatchSessionId ?? null,
      audience_match_session_id: body.audienceMatchSessionId ?? null,
      base_guide_id:            baseGuideId,
      audience_variant_path:    audienceVariantPath,
      primary_offer_id:         primaryOfferId,
      secondary_offer_id:       secondaryOfferId,
      bundle_role:              null,
      why_matched_json:         whyMatched,
    })
    .select('id')
    .single();

  if (recErr) {
    console.error('guide_recommendations insert error', recErr);
    return Response.json({ error: 'Failed to save recommendation' }, { status: 500 });
  }

  const response: RecommendationResponse = {
    guideRecommendationId: rec.id,
    baseGuideId,
    baseGuideTitle:      baseGuideId,   // TODO: resolve human title from quiz/base-guide-catalog.json
    audienceBucketId,
    audienceVariantPath,
    primaryOfferId,
    secondaryOfferId,
    bundleRole:          null,
    showCrisisResources: true,
    whyMatched,
  };

  return Response.json(response, { status: 200 });
}
