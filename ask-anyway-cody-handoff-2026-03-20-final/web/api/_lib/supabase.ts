// ─────────────────────────────────────────────────────────────────────────────
// Supabase server client factory.
//
// Usage: only call createSupabaseServerClient() from within an API route,
// never from client-side code.
//
// Required environment variables:
//   SUPABASE_URL         — your project URL, e.g. https://xxx.supabase.co
//   SUPABASE_SERVICE_KEY — service_role key (never expose to the browser)
// ─────────────────────────────────────────────────────────────────────────────

import { createClient, SupabaseClient } from '@supabase/supabase-js';

let _client: SupabaseClient | null = null;

export function createSupabaseServerClient(): SupabaseClient {
  if (_client) return _client;

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_KEY;

  if (!url || !key) {
    throw new Error(
      'Missing required environment variables: SUPABASE_URL and/or SUPABASE_SERVICE_KEY'
    );
  }

  _client = createClient(url, key, {
    auth: { persistSession: false },
  });

  return _client;
}
