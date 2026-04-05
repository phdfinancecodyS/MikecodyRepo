// POST /api/webhooks/stripe
// Receives Stripe events, verifies the signature, and triggers fulfillment.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 6
// Fulfillment rules: quiz/fulfillment-config.json
//
// Required environment variables:
//   STRIPE_SECRET_KEY: sk_live_... / sk_test_...
//   STRIPE_WEBHOOK_SECRET: whsec_...  (signing secret from Stripe dashboard)
//
// IMPORTANT: this route must receive the raw request body (not parsed JSON).
// In Next.js App Router, that is the default. Do NOT call req.json() here.

import Stripe from 'stripe';
import fs from 'fs';
import path from 'path';
import { createSupabaseServerClient } from '../../_lib/supabase';

interface LeadContact {
  email: string | null;
  phone: string | null;
  first_name: string | null;
  email_opted_in: boolean;
  sms_opted_in: boolean;
}

interface GuideCatalogEntry {
  guide_id: string;
  base_path?: string;
}

interface BaseGuideCatalog {
  guides: GuideCatalogEntry[];
}

function resolveQuizFile(fileName: string): string {
  const cwd = process.cwd();
  const candidates = [
    path.resolve(cwd, 'quiz', fileName),
    path.resolve(cwd, '..', 'quiz', fileName),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  throw new Error(`Quiz config not found: ${fileName}`);
}

const baseGuideCatalog: BaseGuideCatalog = JSON.parse(
  fs.readFileSync(resolveQuizFile('base-guide-catalog.json'), 'utf8'),
);

const GUIDE_BY_ID = new Map<string, GuideCatalogEntry>(
  baseGuideCatalog.guides.map((guide) => [guide.guide_id, guide]),
);

// ─────────────────────────────────────────────────────────────────────────────
// Fulfillment action map: derived from quiz/fulfillment-config.json.
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
  return new Stripe(key, { apiVersion: '2024-04-10' });
}

function buildAudienceVariantPath(guideId: string, audienceBucket: string): string {
  const guide = GUIDE_BY_ID.get(guideId);
  if (!guide?.base_path) {
    return `content/topic-guides/audience-slants/${audienceBucket}/${guideId}.md`;
  }

  return `content/topic-guides/audience-slants/${audienceBucket}/${path.basename(guide.base_path)}`;
}

async function sendTransactionalEmail(params: {
  action: 'guide_delivery' | 'kit_delivery';
  lead: LeadContact;
  guideId: string;
  audienceBucket: string;
  audienceVariantPath: string;
  productId: string;
}): Promise<void> {
  const sendgridApiKey = process.env.SENDGRID_API_KEY;
  if (!sendgridApiKey || !params.lead.email) {
    console.warn(`[fulfillment] ${params.action} skipped - missing SENDGRID_API_KEY or lead email`);
    return;
  }

  const sendgridFrom = process.env.SENDGRID_FROM_EMAIL ?? 'hello@askanyway.com';
  const templateId = params.action === 'guide_delivery'
    ? (process.env.SENDGRID_TEMPLATE_GUIDE_DELIVERY ?? process.env.SENDGRID_GUIDE_TEMPLATE_ID)
    : (process.env.SENDGRID_TEMPLATE_KIT_DELIVERY ?? process.env.SENDGRID_KIT_TEMPLATE_ID);

  const body = templateId
    ? {
        personalizations: [
          {
            to: [{ email: params.lead.email, name: params.lead.first_name ?? '' }],
            dynamic_template_data: {
              first_name: params.lead.first_name ?? '',
              guide_id: params.guideId,
              audience_bucket: params.audienceBucket,
              audience_variant_path: params.audienceVariantPath,
              product_id: params.productId,
            },
          },
        ],
        from: { email: sendgridFrom, name: 'Ask Anyway' },
        template_id: templateId,
      }
    : {
        personalizations: [{ to: [{ email: params.lead.email }] }],
        from: { email: sendgridFrom, name: 'Ask Anyway' },
        subject: params.action === 'guide_delivery' ? 'Your Ask Anyway guide is ready' : 'Your Ask Anyway kit is ready',
        content: [
          {
            type: 'text/plain',
            value: `Hi ${params.lead.first_name ?? 'there'}, your ${params.action === 'guide_delivery' ? 'guide' : 'kit'} (${params.guideId}) is ready. Audience track: ${params.audienceBucket}. Asset path: ${params.audienceVariantPath}`,
          },
        ],
      };

  const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${sendgridApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`SendGrid ${params.action} failed (${response.status}): ${await response.text()}`);
  }
}

async function sendSmsEnrollment(params: { lead: LeadContact }): Promise<void> {
  if (!params.lead.sms_opted_in) {
    console.warn('[fulfillment] sms_enrollment skipped - lead has no SMS opt-in');
    return;
  }

  const twilioSid = process.env.TWILIO_ACCOUNT_SID;
  const twilioToken = process.env.TWILIO_AUTH_TOKEN;
  const twilioFrom = process.env.TWILIO_FROM_NUMBER;
  if (!twilioSid || !twilioToken || !twilioFrom || !params.lead.phone) {
    console.warn('[fulfillment] sms_enrollment skipped - missing Twilio config or lead phone');
    return;
  }

  const body = new URLSearchParams({
    To: params.lead.phone,
    From: twilioFrom,
    Body: `Hey${params.lead.first_name ? ` ${params.lead.first_name}` : ''}! You're now enrolled in Check On Me from Ask Anyway. Reply STOP anytime to cancel.`,
  });

  const response = await fetch(
    `https://api.twilio.com/2010-04-01/Accounts/${twilioSid}/Messages.json`,
    {
      method: 'POST',
      headers: {
        Authorization: `Basic ${Buffer.from(`${twilioSid}:${twilioToken}`).toString('base64')}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: body.toString(),
    },
  );

  if (!response.ok) {
    throw new Error(`Twilio sms_enrollment failed (${response.status}): ${await response.text()}`);
  }
}

async function triggerEmailSequence(params: {
  lead: LeadContact;
  guideId: string;
  audienceBucket: string;
  productId: string;
}): Promise<void> {
  if (!params.lead.email_opted_in) {
    console.warn('[fulfillment] email_sequence_trigger skipped - lead has no email opt-in');
    return;
  }

  const sendgridApiKey = process.env.SENDGRID_API_KEY;
  if (!sendgridApiKey || !params.lead.email) {
    console.warn('[fulfillment] email_sequence_trigger skipped - missing SENDGRID_API_KEY or lead email');
    return;
  }

  const listId = process.env.SENDGRID_POST_PURCHASE_LIST_ID;
  const body: Record<string, unknown> = {
    contacts: [
      {
        email: params.lead.email,
        first_name: params.lead.first_name ?? '',
      },
    ],
  };

  if (listId) {
    body['list_ids'] = [listId];
  }

  const response = await fetch('https://api.sendgrid.com/v3/marketing/contacts', {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${sendgridApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`SendGrid email_sequence_trigger failed (${response.status}): ${await response.text()}`);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Fulfillment dispatcher: called after a payment succeeds.
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
  const audienceVariantPath = buildAudienceVariantPath(guideId, audienceBucket);

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

  const { data: lead } = await db
    .from('leads')
    .select('email, phone, first_name, email_opted_in, sms_opted_in')
    .eq('id', leadId)
    .single();

  const leadContact: LeadContact = {
    email: lead?.email ?? null,
    phone: lead?.phone ?? null,
    first_name: lead?.first_name ?? null,
    email_opted_in: lead?.email_opted_in ?? false,
    sms_opted_in: lead?.sms_opted_in ?? false,
  };

  let fulfillmentFailed = false;

  for (const action of actions) {
    try {
      if (action === 'guide_delivery' || action === 'kit_delivery') {
        await sendTransactionalEmail({
          action,
          lead: leadContact,
          guideId,
          audienceBucket,
          audienceVariantPath,
          productId,
        });
      }

      if (action === 'sms_enrollment') {
        await sendSmsEnrollment({ lead: leadContact });
      }

      if (action === 'email_sequence_trigger') {
        await triggerEmailSequence({
          lead: leadContact,
          guideId,
          audienceBucket,
          productId,
        });
      }
    } catch (error: unknown) {
      fulfillmentFailed = true;
      console.error(`[fulfillment] ${action} failed`, error);
    }
  }

  await db
    .from('purchases')
    .update({ fulfillment_status: fulfillmentFailed ? 'failed' : 'fulfilled' })
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
      // Purchase row missing: log for manual reconciliation and return 200 so Stripe
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
