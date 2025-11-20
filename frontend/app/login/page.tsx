'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';

export default function LoginPage() {
  const router = useRouter();
  const { login, user, isLoading: userLoading } = useUser();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Redirect to home if already logged in
  useEffect(() => {
    if (!userLoading && user) {
      router.push('/');
    }
  }, [user, userLoading, router]);

  const validateEmail = (email: string): boolean => {
    // Basic email validation regex
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
      await login(fullName, email);
      router.push('/');
    } catch (err) {
      setError('Failed to register. Please try again.');
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-black text-white flex items-center justify-center px-6">
      <div className="max-w-md w-full space-y-8">
        {/* ShelfSense branding */}
        <div className="text-center">
          <h1 className="text-6xl tracking-wide font-light mb-4" style={{ fontFamily: 'var(--font-cormorant)' }}>
            ShelfSense
          </h1>
        </div>

        {/* Login form */}
        <form onSubmit={handleSubmit} className="space-y-6 bg-gray-900/50 p-8 rounded-lg border border-gray-800">
          <div>
            <label htmlFor="fullName" className="block text-sm font-medium text-gray-300 mb-2">
              Full Name
            </label>
            <input
              id="fullName"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder=""
              className="w-full px-4 py-3 bg-black border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#4169E1] transition-colors"
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder=""
              className="w-full px-4 py-3 bg-black border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#4169E1] transition-colors"
              disabled={isLoading}
            />
          </div>

          {error && (
            <p className="text-red-500 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full px-6 py-3 bg-[#1E3A5F] hover:bg-[#2C5282] disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors duration-200 text-lg font-semibold"
            style={{ fontFamily: 'var(--font-cormorant)' }}
          >
            {isLoading ? 'Getting Started...' : 'Get Started'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500">
          Your information is saved locally and used to personalize your experience
        </p>
      </div>
    </main>
  );
}
