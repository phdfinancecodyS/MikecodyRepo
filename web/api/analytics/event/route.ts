// POST /api/analytics/event
// Persists supporting analytics events not already captured by core workflow writes.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 7
//
// This route inserts into product_clicks for CTA events and stores all events
// in analytics_events for internal analysis.

import { createSupabaseServerClient } from '../../_lib/supabase';
import type { AnalyticsEventRequest } from '../../_lib/types';

// Events that should be stored in the product_clicks table
const CTA_CLICK_EVENTS = new Set([
  'product_cta_clicked',
  'cta_clicked',
]);

export async function POST(req: Request): Promise<Response> {
  let body: AnalyticsEventRequest;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  if (!body.sessionId) {
    return Response.json({ error: 'sessionId is required' }, { status: 400 });
  }
  if (!body.eventName) {
    return Response.json({ error: 'eventName is required' }, { status: 400 });
  }

  const db = createSupabaseServerClient();
  const payload = body.payload ?? {};
  const timestamp = body.timestamp ?? new Date().toISOString();

  // Persist CTA click events to product_clicks
  if (CTA_CLICK_EVENTS.has(body.eventName)) {
    const productId = payload['productId'] as string | undefined;
    const guideRecommendationId = payload['guideRecommendationId'] as string | undefined;

    if (productId) {
      const { error } = await db.from('product_clicks').insert({
        quiz_session_id:        body.sessionId,
        guide_recommendation_id: guideRecommendationId ?? null,
        product_id:             productId,
        click_location:         payload['location'] as string ?? null,
      });

      if (error) {
        // Log and continue: analytics should not block UX
        console.error('product_clicks insert error', error);
      }
    }
  }

  const { error: analyticsError } = await db.from('analytics_events').insert({
    quiz_session_id: body.sessionId,
    event_name: body.eventName,
    payload_json: payload,
    event_timestamp: timestamp,
  });

  if (analyticsError) {
    console.error('analytics_events insert error', analyticsError);
  }

  console.info('analytics_event', {
    sessionId: body.sessionId,
    eventName: body.eventName,
    payload,
    timestamp,
  });

  return Response.json({ accepted: true }, { status: 200 });
}
