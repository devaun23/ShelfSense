'use client';

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

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
    <html>
      <body className="bg-black text-white min-h-screen flex items-center justify-center">
        <div className="text-center p-8 max-w-md">
          <h2 className="text-2xl font-semibold mb-4">Something went wrong!</h2>
          <p className="text-gray-400 mb-6">
            We've been notified and are working to fix the issue.
          </p>
          <button
            onClick={() => reset()}
            className="px-6 py-2.5 bg-[#4169E1] hover:bg-[#5B7FE8] text-white rounded-lg transition-colors"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
