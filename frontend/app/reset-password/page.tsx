'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import ShelfSenseLogo from '@/components/icons/ShelfSenseLogo';

const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setError('Invalid reset link. Please request a new password reset.');
    }
  }, [token]);

  const validatePassword = (pwd: string): string | null => {
    if (pwd.length < 8) return 'Password must be at least 8 characters';
    if (!/[A-Z]/.test(pwd)) return 'Password must contain at least one uppercase letter';
    if (!/[a-z]/.test(pwd)) return 'Password must contain at least one lowercase letter';
    if (!/\d/.test(pwd)) return 'Password must contain at least one number';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Client-side validation
    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(`${getApiUrl()}/api/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token,
          new_password: password,
        }),
      });

      if (response.ok) {
        setSuccess(true);
        // Redirect to sign-in after 3 seconds
        setTimeout(() => {
          router.push('/sign-in');
        }, 3000);
      } else {
        const data = await response.json();
        setError(data.detail || 'Unable to reset password. The link may have expired.');
      }
    } catch {
      setError('Unable to connect. Please try again later.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (success) {
    return (
      <main className="min-h-screen bg-black flex flex-col items-center justify-center px-6">
        <div className="flex flex-col items-center mb-8">
          <ShelfSenseLogo size={48} animate={false} className="mb-4" />
          <h1
            className="text-4xl tracking-normal font-semibold text-white"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Password Reset
          </h1>
        </div>

        <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Success!</h2>
          <p className="text-gray-300 mb-4">
            Your password has been reset successfully.
          </p>
          <p className="text-gray-400 text-sm">
            Redirecting to sign in...
          </p>
        </div>
      </main>
    );
  }

  if (!token) {
    return (
      <main className="min-h-screen bg-black flex flex-col items-center justify-center px-6">
        <div className="flex flex-col items-center mb-8">
          <ShelfSenseLogo size={48} animate={false} className="mb-4" />
          <h1
            className="text-4xl tracking-normal font-semibold text-white"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Invalid Link
          </h1>
        </div>

        <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          <p className="text-gray-300 mb-6">
            This password reset link is invalid or has expired.
          </p>
          <Link
            href="/forgot-password"
            className="inline-block py-3 px-6 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-semibold rounded-lg transition-all duration-200"
          >
            Request new reset link
          </Link>
        </div>
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
          Create New Password
        </h1>
      </div>

      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-lg p-8">
        <p className="text-gray-300 text-center mb-6">
          Enter your new password below.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
              New password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="Enter new password"
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-2">
              Confirm password
            </label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="Confirm new password"
            />
          </div>

          <div className="text-sm text-gray-400 space-y-1">
            <p>Password must:</p>
            <ul className="list-disc list-inside space-y-0.5 text-gray-500">
              <li className={password.length >= 8 ? 'text-green-400' : ''}>
                Be at least 8 characters
              </li>
              <li className={/[A-Z]/.test(password) ? 'text-green-400' : ''}>
                Contain an uppercase letter
              </li>
              <li className={/[a-z]/.test(password) ? 'text-green-400' : ''}>
                Contain a lowercase letter
              </li>
              <li className={/\d/.test(password) ? 'text-green-400' : ''}>
                Contain a number
              </li>
            </ul>
          </div>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 px-4 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Resetting...' : 'Reset password'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-400">
          <Link href="/sign-in" className="text-indigo-400 hover:text-indigo-300">
            Back to sign in
          </Link>
        </p>
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-black flex flex-col items-center justify-center px-6">
        <ShelfSenseLogo size={48} animate={true} className="mb-4" />
        <p className="text-gray-400">Loading...</p>
      </main>
    }>
      <ResetPasswordForm />
    </Suspense>
  );
}
