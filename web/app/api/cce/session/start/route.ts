const DEFAULT_CCE_BACKEND_URL = 'http://localhost:8000';

function getBackendBaseUrl(): string {
  const configured = process.env.CCE_BACKEND_URL?.trim();
  return (configured && configured.length > 0 ? configured : DEFAULT_CCE_BACKEND_URL).replace(/\/+$/, '');
}

export async function POST(req: Request): Promise<Response> {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const upstreamUrl = `${getBackendBaseUrl()}/session/start`;

  try {
    const upstream = await fetch(upstreamUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
    });

    const contentType = upstream.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await upstream.json();
      return Response.json(data, { status: upstream.status });
    }

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: { 'Content-Type': contentType || 'text/plain; charset=utf-8' },
    });
  } catch (error) {
    console.error('CCE /session/start proxy error', error);
    return Response.json({ error: 'CCE backend unavailable' }, { status: 502 });
  }
}
