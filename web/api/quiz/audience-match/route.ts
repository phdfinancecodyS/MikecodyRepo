// POST /api/quiz/audience-match
// Resolves primary and overlay audience buckets from identity/context selections
// and persists an audience_match_session row.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 3
// Bucket rules: quiz/recommendation-routing-config.json § bucketRules

import { createSupabaseServerClient } from '../../_lib/supabase';
import type { AudienceMatchRequest, AudienceMatchResponse } from '../../_lib/types';

const MAX_IDENTITY = 2;
const MAX_CONTEXT  = 2;
const MAX_OVERLAY  = 2;
const FALLBACK_BUCKET = 'general-mental-health';

export async function POST(req: Request): Promise<Response> {
  let body: AudienceMatchRequest;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  if (!body.quizSessionId) {
    return Response.json({ error: 'quizSessionId is required' }, { status: 400 });
  }

  const identityBuckets = body.identityBucketIds ?? [];
  const contextBuckets  = body.contextBucketIds  ?? [];

  // Enforce selection caps
  if (identityBuckets.length > MAX_IDENTITY) {
    return Response.json(
      { error: `Maximum ${MAX_IDENTITY} identity bucket selections allowed` },
      { status: 400 }
    );
  }
  if (contextBuckets.length > MAX_CONTEXT) {
    return Response.json(
      { error: `Maximum ${MAX_CONTEXT} context bucket selections allowed` },
      { status: 400 }
    );
  }

  const db = createSupabaseServerClient();

  // Verify quiz_session
  const { data: session, error: sessionErr } = await db
    .from('quiz_sessions')
    .select('id')
    .eq('id', body.quizSessionId)
    .single();

  if (sessionErr || !session) {
    return Response.json({ error: 'quiz_session not found' }, { status: 404 });
  }

  const allSelected = [...identityBuckets, ...contextBuckets];

  // If nothing selected, fall back
  let primaryBucketId: string;
  let fallbackUsed = false;

  if (allSelected.length === 0) {
    primaryBucketId = FALLBACK_BUCKET;
    fallbackUsed = true;
  } else if (allSelected.length === 1) {
    primaryBucketId = allSelected[0];
  } else {
    // Multiple selections: primaryBucketId is required
    if (!body.primaryBucketId) {
      return Response.json(
        { error: 'primaryBucketId is required when multiple buckets are selected' },
        { status: 400 }
      );
    }
    if (!allSelected.includes(body.primaryBucketId)) {
      return Response.json(
        { error: 'primaryBucketId must be one of the selected bucket ids' },
        { status: 400 }
      );
    }
    primaryBucketId = body.primaryBucketId;
  }

  // Overlay = everything except the primary, capped at MAX_OVERLAY
  const overlayBucketIds = allSelected
    .filter((id) => id !== primaryBucketId)
    .slice(0, MAX_OVERLAY);

  // Persist
  const { data: matchSession, error: insertErr } = await db
    .from('audience_match_sessions')
    .insert({
      quiz_session_id:                  body.quizSessionId,
      matcher_version:                  body.matcherVersion ?? '1',
      selected_identity_bucket_ids_json: identityBuckets,
      selected_context_bucket_ids_json:  contextBuckets,
      selected_bucket_ids_json:          allSelected,
      primary_bucket_id:                 primaryBucketId,
      overlay_bucket_ids_json:           overlayBucketIds,
    })
    .select('id')
    .single();

  if (insertErr) {
    console.error('audience_match_sessions insert error', insertErr);
    return Response.json({ error: 'Failed to save audience match' }, { status: 500 });
  }

  const response: AudienceMatchResponse = {
    audienceMatchSessionId: matchSession.id,
    selectedBucketIds:      allSelected.length ? allSelected : [FALLBACK_BUCKET],
    primaryBucketId,
    overlayBucketIds,
    fallbackUsed,
  };

  return Response.json(response, { status: 200 });
}
