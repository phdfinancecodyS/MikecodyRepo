// POST /api/checkout/session
// Creates a Stripe Checkout session for a paid product, persists a purchases row
// with status=pending, and returns the checkout URL.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 5
//
// Required environment variables:
//   STRIPE_SECRET_KEY   — sk_live_... / sk_test_...
//   STRIPE_PRICE_IDS    — JSON object mapping product_id → Stripe Price id
//                         e.g. {"guide":"price_xxx","kit":"price_yyy","sms":"price_zzz","bundle":"price_aaa"}

import Stripe from 'stripe';
import { createSupabaseServerClient } from '../../_lib/supabase';
import type { CheckoutSessionRequest, CheckoutSessionResponse } from '../../_lib/types';

const PAID_PRODUCTS = new Set(['guide', 'kit', 'sms', 'bundle']);

function getStripe(): Stripe {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) throw new Error('Missing STRIPE_SECRET_KEY');
  return new Stripe(key, { apiVersion: '2024-06-20' });
}

function getPriceId(productId: string): string {
  const raw = process.env.STRIPE_PRICE_IDS;
  if (!raw) throw new Error('Missing STRIPE_PRICE_IDS');
  const map: Record<string, string> = JSON.parse(raw);
  const priceId = map[productId];
  if (!priceId) throw new Error(`No Stripe Price id configured for product: ${productId}`);
  return priceId;
}

export async function POST(req: Request): Promise<Response> {
  let body: CheckoutSessionRequest;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  // Validate required fields
  const required: (keyof CheckoutSessionRequest)[] = [
    'leadId', 'quizSessionId', 'guideRecommendationId',
    'productId', 'guideId', 'audienceBucketId', 'successUrl', 'cancelUrl',
  ];
  for (const field of required) {
    if (!body[field]) {
      return Response.json({ error: `${field} is required` }, { status: 400 });
    }
  }

  // Free product: no checkout session
  if (body.productId === 'free_crisis_resources') {
    return Response.json(
      { error: 'free_crisis_resources does not require a checkout session' },
      { status: 400 }
    );
  }

  if (!PAID_PRODUCTS.has(body.productId)) {
    return Response.json({ error: `Unknown productId: ${body.productId}` }, { status: 400 });
  }

  const db = createSupabaseServerClient();

  // Verify lead exists
  const { data: lead } = await db
    .from('leads')
    .select('id, email')
    .eq('id', body.leadId)
    .single();
  if (!lead) {
    return Response.json({ error: 'lead not found' }, { status: 404 });
  }

  let stripe: Stripe;
  let priceId: string;
  try {
    stripe  = getStripe();
    priceId = getPriceId(body.productId);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error('Stripe config error', msg);
    return Response.json({ error: 'Payment provider not configured' }, { status: 500 });
  }

  // Create Stripe checkout session
  let stripeSession: Stripe.Checkout.Session;
  try {
    stripeSession = await stripe.checkout.sessions.create({
      mode:           body.productId === 'sms' ? 'subscription' : 'payment',
      line_items:     [{ price: priceId, quantity: 1 }],
      customer_email: lead.email ?? undefined,
      success_url:    body.successUrl,
      cancel_url:     body.cancelUrl,
      metadata: {
        lead_id:                  body.leadId,
        quiz_session_id:          body.quizSessionId,
        guide_recommendation_id:  body.guideRecommendationId,
        guide_id:                 body.guideId,
        audience_bucket_id:       body.audienceBucketId,
        product_id:               body.productId,
      },
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error('Stripe session creation error', msg);
    return Response.json({ error: 'Failed to create checkout session' }, { status: 500 });
  }

  // Persist purchase intent (pending)
  const { data: purchase, error: purchaseErr } = await db
    .from('purchases')
    .insert({
      lead_id:                  body.leadId,
      quiz_session_id:          body.quizSessionId,
      product_id:               body.productId,
      guide_id:                 body.guideId,
      audience_bucket_id:       body.audienceBucketId,
      amount_cents:             stripeSession.amount_total ?? 0,
      currency:                 stripeSession.currency?.toUpperCase() ?? 'USD',
      stripe_session_id:        stripeSession.id,
      fulfillment_status:       'pending',
    })
    .select('id')
    .single();

  if (purchaseErr) {
    console.error('purchases insert error', purchaseErr);
    // Session was created in Stripe; log for reconciliation but still return URL
    console.warn('Stripe session created but purchase row not saved; stripe_session_id:', stripeSession.id);
  }

  const response: CheckoutSessionResponse = {
    purchaseIntentId:  purchase?.id ?? '',
    stripeCheckoutUrl: stripeSession.url ?? '',
  };

  return Response.json(response, { status: 200 });
}
