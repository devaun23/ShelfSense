import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Security headers for all pages
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://clerk.shelfsense.com https://*.clerk.accounts.dev",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https:",
              "font-src 'self' data:",
              "connect-src 'self' https://shelfsense-production-d135.up.railway.app https://clerk.shelfsense.com https://*.clerk.accounts.dev https://api.stripe.com https://vitals.vercel-insights.com",
              "frame-src 'self' https://js.stripe.com https://clerk.shelfsense.com https://*.clerk.accounts.dev",
              "frame-ancestors 'none'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

// Wrap with Sentry if installed
let config = nextConfig;

try {
  const { withSentryConfig } = require("@sentry/nextjs");
  config = withSentryConfig(nextConfig, {
    silent: true,
    hideSourceMaps: true,
    disableLogger: true,
  });
} catch {
  // Sentry not installed, use base config
}

export default config;
