// POST /api/analytics/event
// Persists supporting analytics events not already captured by core workflow writes.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 7
//
// This route inserts into product_clicks for CTA events and forwards all events
// to Mixpanel and/or PostHog when the relevant env vars are set.
// Both providers are optional and may be active simultaneously.
//
// Optional environment variables:
//   MIXPANEL_TOKEN        — Mixpanel project token
//   POSTHOG_API_KEY       — PostHog project API key
//   POSTHOG_HOST          — PostHog instance host (default: https://app.posthog.com)

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

  // ── Forward all events to Mixpanel and/or PostHog ───────────────────────
  // Fire-and-forget: providers are called async so the client response
  // is not blocked by third-party latency.  Any failure is logged but
  // does not affect the 200 response to the caller.

  const eventTimestamp = body.timestamp ?? new Date().toISOString();
  const canonicalEvent = {
    sessionId:  body.sessionId,
    eventName:  body.eventName,
    payload:    body.payload ?? {},
    timestamp:  eventTimestamp,
  };

  const dispatchPromises: Promise<void>[] = [];

  // ── Mixpanel ─────────────────────────────────────────────────────────────
  const mixpanelToken = process.env.MIXPANEL_TOKEN;
  if (mixpanelToken) {
    dispatchPromises.push(
      (async () => {
        const data = [
          {
            event:       body.eventName,
            properties: {
              token:       mixpanelToken,
              distinct_id: body.sessionId,
              time:        Math.floor(new Date(eventTimestamp).getTime() / 1000),
              ...body.payload,
            },
          },
        ];
        const encoded = Buffer.from(JSON.stringify(data)).toString('base64');
        const res = await fetch(
          `https://api.mixpanel.com/track?data=${encodeURIComponent(encoded)}`,
          { method: 'GET' },
        );
        if (!res.ok) {
          console.error(`[analytics] Mixpanel forward failed (${res.status}): ${await res.text()}`);
        }
      })(),
    );
  }

  // ── PostHog ──────────────────────────────────────────────────────────────
  const posthogKey  = process.env.POSTHOG_API_KEY;
  const posthogHost = process.env.POSTHOG_HOST ?? 'https://app.posthog.com';
  if (posthogKey) {
    dispatchPromises.push(
      (async () => {
        const res = await fetch(`${posthogHost}/capture/`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            api_key:     posthogKey,
            event:       body.eventName,
            distinct_id: body.sessionId,
            timestamp:   eventTimestamp,
            properties:  body.payload ?? {},
          }),
        });
        if (!res.ok) {
          console.error(`[analytics] PostHog forward failed (${res.status}): ${await res.text()}`);
        }
      })(),
    );
  }

  // Always log locally as a baseline / fallback
  console.info('analytics_event', canonicalEvent);

  // Await all dispatch in parallel (still non-blocking from the client's view
  // because we respond immediately after dispatching).
  void Promise.all(dispatchPromises).catch((err) =>
    console.error('[analytics] dispatch error', err),
  );

  return Response.json({ accepted: true }, { status: 200 });
}
