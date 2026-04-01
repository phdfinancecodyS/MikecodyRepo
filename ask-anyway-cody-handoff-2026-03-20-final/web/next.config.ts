import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Required for Netlify: output must be 'standalone' or undefined (not 'export')
  // Netlify's Next.js plugin handles edge/serverless routing automatically.
  reactStrictMode: true,
};

export default nextConfig;
