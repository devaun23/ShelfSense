'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { verifyCheckoutSession } from '@/lib/stripe';

function SuccessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = searchParams.get('session_id');
  const { user, getAccessToken, isLoading: userLoading } = useUser();

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [subscriptionInfo, setSubscriptionInfo] = useState<{
    tier?: string;
    billing_cycle?: string;
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    async function verify() {
      if (!sessionId) {
        setStatus('error');
        setErrorMessage('No session ID found');
        return;
      }

      if (userLoading) return;

      if (!user) {
        setStatus('error');
        setErrorMessage('Please sign in to verify your subscription');
        return;
      }

      try {
        const token = await getAccessToken();
        const result = await verifyCheckoutSession(
          sessionId,
          user.userId,
          token || undefined
        );

        if (result.success) {
          setStatus('success');
          setSubscriptionInfo({
            tier: result.tier,
            billing_cycle: result.billing_cycle,
          });
        } else {
          setStatus('error');
          setErrorMessage(result.message || 'Verification failed');
        }
      } catch (err) {
        console.error('Verification error:', err);
        setStatus('error');
        setErrorMessage(err instanceof Error ? err.message : 'Failed to verify subscription');
      }
    }

    verify();
  }, [sessionId, user, userLoading, getAccessToken]);

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#4169E1] mx-auto mb-4" />
          <p className="text-gray-400">Verifying your subscription...</p>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white mb-4">
            Something went wrong
          </h1>
          <p className="text-gray-400 mb-8">
            {errorMessage || 'We could not verify your subscription. Please contact support if you were charged.'}
          </p>
          <div className="space-y-4">
            <button
              onClick={() => router.push('/')}
              className="block w-full bg-[#4169E1] text-white px-6 py-3 rounded-lg hover:bg-[#3558c0] transition-colors"
            >
              Go to Dashboard
            </button>
            <a
              href="mailto:support@shelfsense.com"
              className="block w-full bg-gray-800 text-white px-6 py-3 rounded-lg hover:bg-gray-700 transition-colors"
            >
              Contact Support
            </a>
          </div>
        </div>
      </div>
    );
  }

  const tierName = subscriptionInfo?.tier === 'premium' ? 'Premium' : 'Student';

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg className="w-8 h-8 text-green-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-white mb-4">
          Welcome to {tierName}!
        </h1>

        <p className="text-gray-400 mb-2">
          Your subscription is now active.
        </p>
        <p className="text-gray-400 mb-8">
          You have full access to all {tierName.toLowerCase()} features.
        </p>

        {subscriptionInfo?.billing_cycle && (
          <p className="text-gray-500 text-sm mb-8">
            Billed {subscriptionInfo.billing_cycle === 'yearly' ? 'annually' : 'monthly'}
          </p>
        )}

        <div className="space-y-4">
          <button
            onClick={() => router.push('/')}
            className="block w-full bg-[#4169E1] text-white px-6 py-3 rounded-lg font-medium hover:bg-[#3558c0] transition-colors"
          >
            Start Studying
          </button>
          <button
            onClick={() => router.push('/analytics')}
            className="block w-full bg-gray-800 text-white px-6 py-3 rounded-lg font-medium hover:bg-gray-700 transition-colors"
          >
            View Analytics
          </button>
        </div>
      </div>
    </div>
  );
}

export default function SubscriptionSuccessPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-black flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#4169E1]" />
        </div>
      }
    >
      <SuccessContent />
    </Suspense>
  );
}
