'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';

export default function LoginPage() {
  const router = useRouter();
  const { loginSimple, user, isLoading: userLoading } = useUser();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Redirect to home if already logged in (returning user)
  useEffect(() => {
    if (!userLoading && user) {
      router.replace('/');
    }
  }, [user, userLoading, router]);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    if (!fullName.trim() || !email.trim()) {
      setError('Please fill in all fields');
      setIsLoading(false);
      return;
    }

    if (!validateEmail(email)) {
      setError('Please enter a valid email address');
      setIsLoading(false);
      return;
    }

    try {
      await loginSimple(fullName, email);
      router.replace('/');
    } catch (err) {
      setError('Failed to register. Please try again.');
      setIsLoading(false);
    }
  };

  // Show loading state while checking authentication
  if (userLoading) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="animate-pulse">
          <h1 className="text-4xl font-light" style={{ fontFamily: 'var(--font-cormorant)' }}>
            ShelfSense
          </h1>
        </div>
      </main>
    );
  }

  // If user exists, show loading while redirecting
  if (user) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="animate-pulse">
          <h1 className="text-4xl font-light" style={{ fontFamily: 'var(--font-cormorant)' }}>
            ShelfSense
          </h1>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black text-white flex items-center justify-center px-6">
      <div className="max-w-md w-full space-y-8">
        {/* ShelfSense branding */}
        <div className="text-center">
          <h1 className="text-5xl tracking-wide font-light mb-3" style={{ fontFamily: 'var(--font-cormorant)' }}>
            ShelfSense
          </h1>
          <p className="text-gray-500 text-sm">
            Adaptive learning for Step 2 CK
          </p>
        </div>

        {/* Welcome message */}
        <div className="text-center py-4">
          <h2 className="text-xl text-gray-300 mb-2" style={{ fontFamily: 'var(--font-cormorant)' }}>
            Welcome
          </h2>
          <p className="text-sm text-gray-600">
            Enter your details to get started
          </p>
        </div>

        {/* Login form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="fullName" className="block text-sm text-gray-400 mb-2">
              Full Name
            </label>
            <input
              id="fullName"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-4 py-3 bg-gray-950 border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-[#4169E1] transition-colors"
              placeholder="Your name"
              disabled={isLoading}
              autoFocus
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm text-gray-400 mb-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 bg-gray-950 border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-[#4169E1] transition-colors"
              placeholder="you@example.com"
              disabled={isLoading}
            />
          </div>

          {error && (
            <p className="text-red-500 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full px-6 py-3 bg-[#4169E1] hover:bg-[#5B7FE8] disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors duration-200 text-base font-medium"
          >
            {isLoading ? 'Getting started...' : 'Continue'}
          </button>
        </form>

        <p className="text-center text-xs text-gray-600 pt-4">
          Your information is saved locally to personalize your experience
        </p>
      </div>
    </main>
  );
}
