// POST /api/quiz/topic-match
// Runs the topic matcher against the user's answers, resolves guide recommendations,
// and persists a topic_match_session row.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 2

import { createSupabaseServerClient } from '../../_lib/supabase';
import type { TopicMatchRequest, TopicMatchResponse, ProductId } from '../../_lib/types';

// ─────────────────────────────────────────────────────────────────────────────
// Domain-to-offer mapping (derived from quiz/recommendation-routing-config.json)
// ─────────────────────────────────────────────────────────────────────────────
const DOMAIN_OFFER_MAP: Record<string, ProductId> = {
  anxiety_overthinking:          'kit',
  communication_relationships:   'guide',
  trauma_ptsd:                   'kit',
  depression_motivation:         'kit',
  sleep_body_pain_substances:    'kit',
  crisis_self_harm:              'free_crisis_resources',
  general_mental_health:         'guide',
};

// Simplified domain scoring — the real matcher loads quiz/topic-matcher-flow.json.
// This scaffold implements the routing scaffold; replace with full config-driven
// evaluation before production.
function matchDomain(answers: TopicMatchRequest['answers']): {
  domain: string;
  guideIds: string[];
  whyMatched: string[];
} {
  // TODO: replace with config-driven evaluation from quiz/topic-matcher-flow.json
  const domain = 'general_mental_health';
  const guideIds: string[] = [];
  const whyMatched: string[] = [];

  if (answers.tm_q1) {
    whyMatched.push(`User prioritised: ${answers.tm_q1}`);
  }
  if (answers.tm_q2) {
    whyMatched.push(`User selected pattern: ${answers.tm_q2}`);
  }
  if (answers.tm_q3?.length) {
    whyMatched.push(`User requested support style: ${answers.tm_q3.join(', ')}`);
  }

  return { domain, guideIds, whyMatched };
}

export async function POST(req: Request): Promise<Response> {
  let body: TopicMatchRequest;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  if (!body.quizSessionId) {
    return Response.json({ error: 'quizSessionId is required' }, { status: 400 });
  }

  // Validate tm_q3 selection limit (max 2)
  if (body.answers?.tm_q3 && body.answers.tm_q3.length > 2) {
    return Response.json({ error: 'Maximum 2 selections allowed for tm_q3' }, { status: 400 });
  }

  const db = createSupabaseServerClient();

  // Verify quiz_session exists
  const { data: session, error: sessionErr } = await db
    .from('quiz_sessions')
    .select('id')
    .eq('id', body.quizSessionId)
    .single();

  if (sessionErr || !session) {
    return Response.json({ error: 'quiz_session not found' }, { status: 404 });
  }

  const { domain, guideIds, whyMatched } = matchDomain(body.answers ?? {});
  const offerType: ProductId = DOMAIN_OFFER_MAP[domain] ?? 'guide';

  // Persist topic_match_session
  const { data: matchSession, error: insertErr } = await db
    .from('topic_match_sessions')
    .insert({
      quiz_session_id:           body.quizSessionId,
      matcher_version:           body.matcherVersion ?? '1',
      tm_q1_option_id:           body.answers?.tm_q1 ?? null,
      tm_q2_option_id:           body.answers?.tm_q2 ?? null,
      tm_q3_option_ids_json:     body.answers?.tm_q3 ?? [],
      matched_domain:            domain,
      recommended_guide_ids_json: guideIds,
      recommended_offer_type:    offerType,
    })
    .select('id')
    .single();

  if (insertErr) {
    console.error('topic_match_sessions insert error', insertErr);
    return Response.json({ error: 'Failed to save topic match' }, { status: 500 });
  }

  const response: TopicMatchResponse = {
    topicMatchSessionId: matchSession.id,
    matchedDomain:       domain,
    recommendedGuideIds: guideIds,
    recommendedOfferType: offerType,
    whyMatched,
  };

  return Response.json(response, { status: 200 });
}
