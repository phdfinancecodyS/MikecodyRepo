// POST /api/webhooks/stripe
// Receives Stripe events, verifies the signature, and triggers fulfillment.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 6
// Fulfillment rules: quiz/fulfillment-config.json
//
// Required environment variables:
//   STRIPE_SECRET_KEY                  — sk_live_... / sk_test_...
//   STRIPE_WEBHOOK_SECRET              — whsec_... (signing secret from Stripe dashboard)
//   SENDGRID_API_KEY                   — SG...
//   SENDGRID_FROM_EMAIL                — e.g. hello@askanyway.com
//   SENDGRID_TEMPLATE_GUIDE_DELIVERY   — SendGrid dynamic template ID (optional)
//   SENDGRID_TEMPLATE_KIT_DELIVERY     — SendGrid dynamic template ID (optional)
//   SENDGRID_POST_PURCHASE_LIST_ID     — SendGrid Marketing list UUID (optional)
//   TWILIO_ACCOUNT_SID                 — ACxxx
//   TWILIO_AUTH_TOKEN                  — ...
//   TWILIO_FROM_NUMBER                 — +1...
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

  // Load lead contact details for provider dispatch
  const { data: lead } = await db
    .from('leads')
    .select('email, phone, first_name, sms_opt_in')
    .eq('id', leadId)
    .single();

  // ── Provider dispatch ──────────────────────────────────────────────────────
  // Reference: quiz/fulfillment-config.json § providerPlaceholders

  const sendgridApiKey = process.env.SENDGRID_API_KEY;
  const sendgridFrom   = process.env.SENDGRID_FROM_EMAIL ?? 'hello@askanyway.com';

  const twilioSid   = process.env.TWILIO_ACCOUNT_SID;
  const twilioToken = process.env.TWILIO_AUTH_TOKEN;
  const twilioFrom  = process.env.TWILIO_FROM_NUMBER;

  for (const action of actions) {
    // ── guide_delivery / kit_delivery: SendGrid transactional email ─────────
    if (action === 'guide_delivery' || action === 'kit_delivery') {
      if (!sendgridApiKey || !lead?.email) {
        console.warn(`[fulfillment] ${action} skipped — missing SENDGRID_API_KEY or lead email`);
        continue;
      }

      const templateEnvKey = action === 'guide_delivery'
        ? 'SENDGRID_TEMPLATE_GUIDE_DELIVERY'
        : 'SENDGRID_TEMPLATE_KIT_DELIVERY';
      const templateId = process.env[templateEnvKey];

      const sgBody = templateId
        ? // Dynamic template path
          {
            personalizations: [
              {
                to: [{ email: lead.email, name: lead.first_name ?? '' }],
                dynamic_template_data: {
                  first_name:            lead.first_name ?? '',
                  guide_id:              guideId,
                  audience_bucket:       audienceBucket,
                  audience_variant_path: audienceVariantPath,
                  product_id:            productId,
                },
              },
            ],
            from:        { email: sendgridFrom, name: 'Ask Anyway' },
            template_id: templateId,
          }
        : // Plain-text fallback when no template is configured yet
          {
            personalizations: [{ to: [{ email: lead.email }] }],
            from:    { email: sendgridFrom, name: 'Ask Anyway' },
            subject: action === 'guide_delivery' ? 'Your guide is ready' : 'Your kit is ready',
            content: [
              {
                type:  'text/plain',
                value: `Hi ${lead.first_name ?? 'there'}, your ${action === 'guide_delivery' ? 'guide' : 'kit'} (${guideId}) is ready — audience: ${audienceBucket}.`,
              },
            ],
          };

      const sgRes = await fetch('https://api.sendgrid.com/v3/mail/send', {
        method:  'POST',
        headers: { Authorization: `Bearer ${sendgridApiKey}`, 'Content-Type': 'application/json' },
        body:    JSON.stringify(sgBody),
      });

      if (!sgRes.ok) {
        console.error(`[fulfillment] SendGrid ${action} failed (${sgRes.status}): ${await sgRes.text()}`);
      } else {
        console.info(`[fulfillment] SendGrid ${action} sent to ${lead.email}`);
      }
    }

    // ── sms_enrollment: Twilio ───────────────────────────────────────────────
    if (action === 'sms_enrollment') {
      // TCPA: never send without confirmed SMS opt-in
      if (!lead?.sms_opt_in) {
        console.warn(`[fulfillment] sms_enrollment skipped — lead ${leadId} has no SMS opt-in`);
        continue;
      }
      if (!twilioSid || !twilioToken || !twilioFrom || !lead.phone) {
        console.warn('[fulfillment] sms_enrollment skipped — missing Twilio config or lead phone');
        continue;
      }

      const enrollBody = new URLSearchParams({
        To:   lead.phone,
        From: twilioFrom,
        Body: `Hey${lead.first_name ? ` ${lead.first_name}` : ''}! You're now enrolled in Check On Me — weekly check-ins from Ask Anyway. Reply STOP anytime to cancel.`,
      });

      const twilioRes = await fetch(
        `https://api.twilio.com/2010-04-01/Accounts/${twilioSid}/Messages.json`,
        {
          method:  'POST',
          headers: {
            Authorization:  `Basic ${Buffer.from(`${twilioSid}:${twilioToken}`).toString('base64')}`,
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: enrollBody.toString(),
        },
      );

      if (!twilioRes.ok) {
        console.error(`[fulfillment] Twilio sms_enrollment failed (${twilioRes.status}): ${await twilioRes.text()}`);
      } else {
        console.info(`[fulfillment] Twilio sms_enrollment sent to ${lead.phone}`);
      }
    }

    // ── email_sequence_trigger: SendGrid Marketing Contacts ─────────────────
    if (action === 'email_sequence_trigger') {
      if (!sendgridApiKey || !lead?.email) {
        console.warn('[fulfillment] email_sequence_trigger skipped — missing SENDGRID_API_KEY or lead email');
        continue;
      }

      const listId = process.env.SENDGRID_POST_PURCHASE_LIST_ID;
      const upsertPayload: Record<string, unknown> = {
        contacts: [
          {
            email:      lead.email,
            first_name: lead.first_name ?? '',
            custom_fields: { guide_id: guideId, audience_bucket: audienceBucket, product_id: productId },
          },
        ],
        ...(listId ? { list_ids: [listId] } : {}),
      };

      const seqRes = await fetch('https://api.sendgrid.com/v3/marketing/contacts', {
        method:  'PUT',
        headers: { Authorization: `Bearer ${sendgridApiKey}`, 'Content-Type': 'application/json' },
        body:    JSON.stringify(upsertPayload),
      });

      if (!seqRes.ok) {
        console.error(`[fulfillment] SendGrid email_sequence_trigger failed (${seqRes.status}): ${await seqRes.text()}`);
      } else {
        console.info(`[fulfillment] email_sequence_trigger upserted ${lead.email} to SendGrid Marketing`);
      }
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
