import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      allowedOrigins: ['*'],
    },
  },
  // Allow Replit proxy origins for development
  allowedDevOrigins: [
    '32d393b6-b863-4b99-af62-e405a60e5456-00-3eiosphurbiw5.sisko.replit.dev',
    'https://32d393b6-b863-4b99-af62-e405a60e5456-00-3eiosphurbiw5.sisko.replit.dev',
    'https://*.sisko.replit.dev',
    'https://*.replit.dev',
    'https://*.id.repl.co',
  ],
};

export default nextConfig;
