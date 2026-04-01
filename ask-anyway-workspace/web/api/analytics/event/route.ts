// POST /api/analytics/event
// Persists supporting analytics events not already captured by core workflow writes.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 7
//
// This route inserts into product_clicks for CTA events and is a no-op sink
// for other event types (accepted and logged, not stored in a separate table yet).
// Extend the STORED_EVENTS set or add routing logic as the analytics layer grows.

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

  // Persist CTA click events to product_clicks
  if (CTA_CLICK_EVENTS.has(body.eventName)) {
    const payload = body.payload ?? {};
    const productId = payload['productId'] as string | undefined;
    const guideId   = payload['guideId']   as string | undefined;

    if (productId) {
      const db = createSupabaseServerClient();
      const { error } = await db.from('product_clicks').insert({
        quiz_session_id:        body.sessionId,
        guide_recommendation_id: null,        // supplied if available in payload
        product_id:             productId,
        click_location:         payload['location'] as string ?? null,
      });

      if (error) {
        // Log and continue — analytics should not block UX
        console.error('product_clicks insert error', error);
      }
    }
  }

  // All other events: accepted and logged to stdout for now.
  // TODO: route to a dedicated analytics events table or third-party sink.
  console.info('analytics_event', {
    sessionId: body.sessionId,
    eventName: body.eventName,
    payload:   body.payload,
    timestamp: body.timestamp ?? new Date().toISOString(),
  });

  return Response.json({ accepted: true }, { status: 200 });
}
