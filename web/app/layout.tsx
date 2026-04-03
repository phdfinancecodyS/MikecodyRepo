import type { Metadata } from 'next';
import './globals.css';
import Analytics from './analytics';

export const metadata: Metadata = {
  title: 'Ask Anyway',
  description: 'Mental health check-in quiz',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}