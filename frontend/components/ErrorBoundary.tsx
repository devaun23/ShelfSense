"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import * as Sentry from "@sentry/nextjs";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to console in development
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    // Report to Sentry in production
    if (process.env.NODE_ENV === "production") {
      Sentry.withScope((scope) => {
        scope.setTag("error_boundary", "true");
        scope.setExtra("componentStack", errorInfo.componentStack);
        Sentry.captureException(error);
      });
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      // Render custom fallback UI or default
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-black flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
            <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-red-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            <h2 className="text-xl font-semibold text-white mb-2">
              Something went wrong
            </h2>

            <p className="text-gray-400 mb-6">
              We encountered an unexpected error. Please try again.
            </p>

            {process.env.NODE_ENV !== "production" && this.state.error && (
              <div className="bg-gray-950 border border-gray-800 rounded p-3 mb-6 text-left overflow-auto max-h-32">
                <code className="text-xs text-red-400 whitespace-pre-wrap">
                  {this.state.error.message}
                </code>
              </div>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleRetry}
                className="px-4 py-2 bg-[#4169E1] hover:bg-[#5B7FE8] text-white rounded-md transition-colors"
              >
                Try again
              </button>

              <button
                onClick={() => (window.location.href = "/")}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-md transition-colors"
              >
                Go home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
