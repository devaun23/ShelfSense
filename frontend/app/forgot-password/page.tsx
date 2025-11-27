'use client';

import { useState } from 'react';
import Link from 'next/link';
import ShelfSenseLogo from '@/components/icons/ShelfSenseLogo';

const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const response = await fetch(`${getApiUrl()}/api/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (response.ok) {
        setSubmitted(true);
      } else {
        const data = await response.json();
        setError(data.detail || 'Something went wrong. Please try again.');
      }
    } catch {
      setError('Unable to connect. Please try again later.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <main className="min-h-screen bg-black flex flex-col items-center justify-center px-6">
        <div className="flex flex-col items-center mb-8">
          <ShelfSenseLogo size={48} animate={false} className="mb-4" />
          <h1
            className="text-4xl tracking-normal font-semibold text-white"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Check your email
          </h1>
        </div>

        <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          <p className="text-gray-300 mb-6">
            If an account exists for <span className="font-medium text-white">{email}</span>,
            we&apos;ve sent password reset instructions.
          </p>
          <p className="text-gray-400 text-sm mb-6">
            Didn&apos;t receive an email? Check your spam folder or try again.
          </p>
          <button
            onClick={() => {
              setSubmitted(false);
              setEmail('');
            }}
            className="text-indigo-400 hover:text-indigo-300 text-sm font-medium"
          >
            Try another email
          </button>
        </div>

        <Link
          href="/sign-in"
          className="mt-6 text-gray-400 hover:text-white text-sm"
        >
          Back to sign in
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black flex flex-col items-center justify-center px-6">
      <div className="flex flex-col items-center mb-8">
        <ShelfSenseLogo size={48} animate={false} className="mb-4" />
        <h1
          className="text-4xl tracking-normal font-semibold text-white"
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          Reset Password
        </h1>
      </div>

      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-lg p-8">
        <p className="text-gray-300 text-center mb-6">
          Enter your email address and we&apos;ll send you instructions to reset your password.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
              Email address
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="you@example.com"
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 px-4 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Sending...' : 'Send reset link'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-400">
          Remember your password?{' '}
          <Link href="/sign-in" className="text-indigo-400 hover:text-indigo-300">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
