/**
 * Guide viewer page.
 *
 * Fetches markdown content from the CCE backend, converts to HTML,
 * and renders in Ask Anyway's dark theme. Loaded inside the iframe
 * guide drawer from the chat UI.
 *
 * URL: /guides/{guideId}?audience={bucketId}
 */

const CCE_URL = process.env.CCE_BACKEND_URL || 'http://localhost:8000';

/** Minimal markdown to HTML (handles what our guides use). */
function mdToHtml(md: string): string {
  let html = md
    // Escape HTML entities first
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Headings (## before #)
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold and italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Links [text](url)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    // Horizontal rules
    .replace(/^---+$/gm, '<hr>')
    // Blockquotes
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    // Unordered lists
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    // Ordered lists
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

  // Wrap consecutive <li> in <ul>
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
  // Merge consecutive <blockquote>
  html = html.replace(/<\/blockquote>\n<blockquote>/g, '<br>');

  // Paragraphs: wrap lines that aren't already wrapped
  const lines = html.split('\n');
  const result: string[] = [];
  let inParagraph = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (inParagraph) {
        result.push('</p>');
        inParagraph = false;
      }
      continue;
    }
    if (/^<(?:h[1-4]|ul|ol|li|hr|blockquote|div)/.test(trimmed)) {
      if (inParagraph) {
        result.push('</p>');
        inParagraph = false;
      }
      result.push(trimmed);
    } else {
      if (!inParagraph) {
        result.push('<p>');
        inParagraph = true;
      }
      result.push(trimmed);
    }
  }
  if (inParagraph) result.push('</p>');

  return result.join('\n');
}

interface PageProps {
  params: Promise<{ guideId: string }>;
  searchParams: Promise<{ audience?: string }>;
}

export default async function GuidePage({ params, searchParams }: PageProps) {
  const { guideId } = await params;
  const { audience } = await searchParams;
  const bucket = audience || 'general-mental-health';

  let title = 'Guide';
  let contentHtml = '';
  let error = '';

  try {
    const res = await fetch(
      `${CCE_URL}/guides/${encodeURIComponent(guideId)}?audience=${encodeURIComponent(bucket)}`,
      { cache: 'no-store' }
    );

    if (!res.ok) {
      error = res.status === 404 ? 'Guide not found.' : `Error loading guide (${res.status}).`;
    } else {
      const data = await res.json();
      title = data.title || guideId;
      contentHtml = mdToHtml(data.content || '');
    }
  } catch {
    error = 'Could not connect to the server.';
  }

  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{title}</title>
        <style dangerouslySetInnerHTML={{ __html: `
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body {
            background: #0d0d0d;
            color: #e8e0d6;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 17px;
            line-height: 1.65;
            padding: 24px 20px 60px;
            max-width: 680px;
            margin: 0 auto;
            -webkit-font-smoothing: antialiased;
          }
          h1 { font-size: 1.8rem; margin: 0 0 20px; color: #f0ece4; line-height: 1.2; }
          h2 { font-size: 1.4rem; margin: 32px 0 12px; color: #f0ece4; border-bottom: 1px solid #2a2a2a; padding-bottom: 6px; }
          h3 { font-size: 1.15rem; margin: 24px 0 8px; color: #d4ccc2; }
          h4 { font-size: 1rem; margin: 20px 0 6px; color: #c9c1b7; }
          p { margin: 0 0 14px; }
          strong { color: #f0ece4; }
          em { color: #c9c1b7; font-style: italic; }
          a { color: #7eb8da; text-decoration: underline; }
          a:hover { color: #a8d4f0; }
          ul, ol { margin: 0 0 14px 24px; }
          li { margin-bottom: 6px; }
          blockquote {
            border-left: 3px solid #444;
            padding: 10px 16px;
            margin: 16px 0;
            background: #1a1a1a;
            color: #c9c1b7;
            border-radius: 4px;
          }
          hr { border: none; height: 1px; background: #333; margin: 28px 0; }
          .error {
            color: #f87171;
            text-align: center;
            padding: 40px 20px;
            font-size: 1.1rem;
          }
          .crisis-footer {
            margin-top: 40px;
            padding: 16px;
            background: #1a1a1a;
            border-radius: 8px;
            border: 1px solid #333;
            font-size: .9rem;
            color: #999;
            text-align: center;
          }
          .crisis-footer a { color: #7eb8da; }
        `}} />
      </head>
      <body>
        {error ? (
          <div className="error">{error}</div>
        ) : (
          <>
            <div dangerouslySetInnerHTML={{ __html: contentHtml }} />
            <div className="crisis-footer">
              If you or someone you know is in crisis, call or text{' '}
              <a href="tel:988">988</a> (Suicide &amp; Crisis Lifeline) or text{' '}
              <a href="sms:741741">HOME to 741741</a> (Crisis Text Line).
            </div>
          </>
        )}
      </body>
    </html>
  );
}
