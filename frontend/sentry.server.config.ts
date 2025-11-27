// This file configures the initialization of Sentry on the server.
// The config you add here will be used whenever the server handles a request.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,

    // Performance Monitoring - sample 30% of transactions
    tracesSampleRate: 0.3,

    // Set environment
    environment: process.env.NODE_ENV,

    // Don't send events in development
    enabled: process.env.NODE_ENV === "production",

    // Filter out noisy errors
    ignoreErrors: [
      // Expected Next.js behaviors
      /NEXT_REDIRECT/,
      /NEXT_NOT_FOUND/,
      // Auth redirects
      /clerk/i,
    ],
  });
}
