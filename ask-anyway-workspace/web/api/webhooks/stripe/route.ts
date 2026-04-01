// POST /api/webhooks/stripe
// Receives Stripe events, verifies the signature, and triggers fulfillment.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 6
// Fulfillment rules: quiz/fulfillment-config.json
//
// Required environment variables:
//   STRIPE_SECRET_KEY         — sk_live_... / sk_test_...
//   STRIPE_WEBHOOK_SECRET     — whsec_...  (signing secret from Stripe dashboard)
//
// IMPORTANT: this route must receive the raw request body (not parsed JSON).
// In Next.js App Router, that is the default — do NOT call req.json() here.

import Stripe from 'stripe';
import { createSupabaseServerClient } from '../../_lib/supabase';

// ─────────────────────────────────────────────────────────────────────────────
// Fulfillment action map — derived from quiz/fulfillment-config.json.
// Update here when quiz/fulfillment-config.json changes.
// ─────────────────────────────────────────────────────────────────────────────
const PRODUCT_FULFILLMENT_ACTIONS: Record<string, string[]> = {
  guide:  ['guide_delivery', 'email_sequence_trigger'],
  kit:    ['guide_delivery', 'kit_delivery', 'email_sequence_trigger'],
  sms:    ['sms_enrollment', 'email_sequence_trigger'],
  bundle: ['guide_delivery', 'kit_delivery', 'sms_enrollment', 'email_sequence_trigger'],
  free_crisis_resources: [],
};

const PROVIDER_BY_EVENT: Record<string, string> = {
  guide_delivery:         'email',
  kit_delivery:           'email',
  sms_enrollment:         'sms_platform',
  email_sequence_trigger: 'email_platform',
};

function getStripe(): Stripe {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) throw new Error('Missing STRIPE_SECRET_KEY');
  return new Stripe(key, { apiVersion: '2024-06-20' });
}

// ─────────────────────────────────────────────────────────────────────────────
// Fulfillment dispatcher — called after a payment succeeds.
// ─────────────────────────────────────────────────────────────────────────────
async function fulfillPurchase(purchaseId: string, metadata: Record<string, string>): Promise<void> {
  const db = createSupabaseServerClient();

  // Load purchase to get product context
  const { data: purchase } = await db
    .from('purchases')
    .select('product_id, guide_id, audience_bucket_id, lead_id')
    .eq('id', purchaseId)
    .single();

  const productId      = purchase?.product_id      ?? metadata['product_id'] ?? '';
  const guideId        = purchase?.guide_id         ?? metadata['guide_id']   ?? '';
  const audienceBucket = purchase?.audience_bucket_id ?? metadata['audience_bucket_id'] ?? 'general-mental-health';
  const leadId         = purchase?.lead_id          ?? metadata['lead_id']    ?? '';

  // Mark in-progress
  await db
    .from('purchases')
    .update({ fulfillment_status: 'processing' })
    .eq('id', purchaseId);

  const actions = PRODUCT_FULFILLMENT_ACTIONS[productId] ?? [];

  if (actions.length === 0) {
    // No fulfillment actions (e.g. free_crisis_resources)
    await db
      .from('purchases')
      .update({ fulfillment_status: 'fulfilled' })
      .eq('id', purchaseId);
    return;
  }

  // Build audience-specific asset path for guide/kit delivery
  const audienceVariantPath =
    `content/topic-guides/audience-slants/${audienceBucket}/${guideId}.md`;

  // Insert fulfillment_events row per action
  const events = actions.map((eventType) => ({
    purchase_id: purchaseId,
    event_type:  eventType,
    event_payload_json: {
      product_id:            productId,
      guide_id:              guideId,
      audience_bucket_id:    audienceBucket,
      lead_id:               leadId,
      audience_variant_path: audienceVariantPath,
    },
    provider: PROVIDER_BY_EVENT[eventType] ?? 'internal',
  }));

  const { error: eventsErr } = await db.from('fulfillment_events').insert(events);
  if (eventsErr) {
    console.error('fulfillment_events insert error', eventsErr);
    await db
      .from('purchases')
      .update({ fulfillment_status: 'failed' })
      .eq('id', purchaseId);
    return;
  }

  // ── Provider dispatch stubs ────────────────────────────────────────────────
  // Replace each stub with a real provider call before launch.
  // Reference: quiz/fulfillment-config.json § providerPlaceholders

  for (const action of actions) {
    if (action === 'guide_delivery' || action === 'kit_delivery') {
      // TODO: send transactional email via SendGrid / ConvertKit with asset link
      // Variables available: leadId, guideId, audienceBucket, audienceVariantPath
      console.info(`[fulfillment] ${action} pending for lead ${leadId}, guide ${guideId}`);
    }

    if (action === 'sms_enrollment') {
      // TODO: verify lead opt-in, then enroll via Twilio / sms_platform
      // TCPA compliance check required before sending any message
      console.info(`[fulfillment] sms_enrollment pending for lead ${leadId}`);
    }

    if (action === 'email_sequence_trigger') {
      // TODO: add lead to post-purchase nurture sequence in ConvertKit / ActiveCampaign
      console.info(`[fulfillment] email_sequence_trigger pending for lead ${leadId}`);
    }
  }

  await db
    .from('purchases')
    .update({ fulfillment_status: 'fulfilled' })
    .eq('id', purchaseId);
}

export async function POST(req: Request): Promise<Response> {
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!webhookSecret) {
    return Response.json({ error: 'Webhook secret not configured' }, { status: 500 });
  }

  const signature = req.headers.get('stripe-signature');
  if (!signature) {
    return Response.json({ error: 'Missing stripe-signature header' }, { status: 400 });
  }

  // Read raw body for signature verification
  const rawBody = await req.text();

  let event: Stripe.Event;
  try {
    const stripe = getStripe();
    event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error('Stripe webhook signature verification failed', msg);
    return Response.json({ error: 'Invalid webhook signature' }, { status: 400 });
  }

  // Handle payment success events
  if (
    event.type === 'checkout.session.completed' ||
    event.type === 'payment_intent.succeeded'
  ) {
    const session =
      event.type === 'checkout.session.completed'
        ? (event.data.object as Stripe.Checkout.Session)
        : null;

    const stripeSessionId =
      session?.id ??
      (event.data.object as Stripe.PaymentIntent).id;

    const metadata: Record<string, string> =
      (session?.metadata as Record<string, string>) ?? {};

    const db = createSupabaseServerClient();

    // Look up the purchase row by stripe_session_id or stripe_payment_intent_id
    const { data: purchase } = await db
      .from('purchases')
      .select('id, fulfillment_status')
      .or(
        `stripe_session_id.eq.${stripeSessionId},stripe_payment_intent_id.eq.${stripeSessionId}`
      )
      .single();

    if (!purchase) {
      // Purchase row missing — log for manual reconciliation; return 200 so Stripe
      // doesn't keep retrying an event we've acknowledged.
      console.warn('Stripe webhook: no matching purchase row for', stripeSessionId);
      return Response.json({ received: true }, { status: 200 });
    }

    // Idempotency: only fulfill once
    if (purchase.fulfillment_status !== 'pending') {
      return Response.json({ received: true }, { status: 200 });
    }

    await fulfillPurchase(purchase.id, metadata);
  }

  return Response.json({ received: true }, { status: 200 });
}
