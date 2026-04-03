'use client';

import * as Sentry from '@sentry/nextjs';
import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <main className="shell" style={{ textAlign: 'center', paddingTop: 80 }}>
          <h1>Something went wrong</h1>
          <p style={{ marginBottom: 20 }}>
            We hit an unexpected error. If you are in crisis, please call or text 988 now.
          </p>
          <button className="btn" onClick={reset} type="button">
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
