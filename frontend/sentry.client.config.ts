// This file configures the initialization of Sentry on the client.
// The config you add here will be used whenever a user loads a page in their browser.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,

    // Performance Monitoring - sample 30% of transactions
    tracesSampleRate: 0.3,

    // Session Replay for error debugging
    replaysSessionSampleRate: 0.1, // Sample 10% of sessions
    replaysOnErrorSampleRate: 1.0, // Capture 100% of sessions with errors

    // Set environment
    environment: process.env.NODE_ENV,

    // Integrations
    integrations: [
      Sentry.replayIntegration({
        // Mask all text content for privacy
        maskAllText: true,
        // Block all media for privacy
        blockAllMedia: true,
      }),
    ],

    // Filter out noisy errors
    ignoreErrors: [
      // Browser extensions
      /top\.GLOBALS/,
      /originalCreateNotification/,
      /canvas\.contentDocument/,
      /MyApp_RemoveAllHighlights/,
      /http:\/\/tt\.telekomcdn\.com/,
      /java\.net\.(SocketException|ProtocolException)/,
      // Random errors from browser plugins
      /webkitExitFullScreen/,
      /chrome-extension:/,
      /moz-extension:/,
      // Network errors that are not actionable
      /Failed to fetch/,
      /NetworkError/,
      /AbortError/,
      // Clerk auth redirects (expected behavior)
      /NEXT_REDIRECT/,
    ],

    // Don't send events in development
    enabled: process.env.NODE_ENV === "production",

    // Filter sensitive data before sending
    beforeSend(event) {
      // Remove auth tokens from breadcrumbs
      if (event.breadcrumbs) {
        event.breadcrumbs = event.breadcrumbs.map((breadcrumb) => {
          if (breadcrumb.data?.url) {
            // Remove tokens from URLs
            breadcrumb.data.url = breadcrumb.data.url.replace(
              /token=[^&]+/g,
              "token=[FILTERED]"
            );
          }
          return breadcrumb;
        });
      }
      return event;
    },
  });
}
