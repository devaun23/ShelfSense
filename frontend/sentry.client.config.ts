import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Adjust this value in production
  tracesSampleRate: 0.1,

  // Only enable in production
  enabled: process.env.NODE_ENV === 'production',

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,

  // Capture unhandled promise rejections
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration({
      // Capture 10% of all sessions
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],

  // Session Replay
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
