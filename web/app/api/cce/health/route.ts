const DEFAULT_CCE_BACKEND_URL = 'http://localhost:8000';

function getBackendBaseUrl(): string {
  const configured = process.env.CCE_BACKEND_URL?.trim();
  return (configured && configured.length > 0 ? configured : DEFAULT_CCE_BACKEND_URL).replace(/\/+$/, '');
}

export async function GET(): Promise<Response> {
  const upstreamUrl = `${getBackendBaseUrl()}/health`;

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    const upstream = await fetch(upstreamUrl, {
      method: 'GET',
      cache: 'no-store',
      signal: controller.signal,
    });
    clearTimeout(timeout);

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
  } catch {
    return Response.json(
      { status: 'down', ready: false, checks: [] },
      { status: 502 }
    );
  }
}
