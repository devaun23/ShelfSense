'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { redirectToPortal, getPaymentStatus, PaymentStatus } from '@/lib/stripe';

interface SubscriptionManagerProps {
  className?: string;
}

export default function SubscriptionManager({ className = '' }: SubscriptionManagerProps) {
  const { user, getAccessToken } = useUser();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [subscription, setSubscription] = useState<PaymentStatus | null>(null);

  useEffect(() => {
    if (user) {
      fetchSubscriptionStatus();
    } else {
      setLoading(false);
    }
  }, [user]);

  const fetchSubscriptionStatus = async () => {
    if (!user) return;

    try {
      const token = await getAccessToken();
      const status = await getPaymentStatus(user.userId, token || undefined);
      setSubscription(status);
    } catch (err) {
      console.error('Error fetching subscription:', err);
      setError('Failed to load subscription status');
    } finally {
      setLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    if (!user) return;

    setPortalLoading(true);
    setError(null);

    try {
      const token = await getAccessToken();
      await redirectToPortal(user.userId, token || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open subscription manager');
      setPortalLoading(false);
    }
  };

  if (loading) {
    return (
      <div className={`bg-gray-900 rounded-lg p-6 border border-gray-800 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-700 rounded w-1/3 mb-4" />
          <div className="h-4 bg-gray-700 rounded w-2/3" />
        </div>
      </div>
    );
  }

  if (!subscription || subscription.tier === 'free') {
    return (
      <div className={`bg-gray-900 rounded-lg p-6 border border-gray-800 ${className}`}>
        <h3 className="text-lg font-semibold text-white mb-2">Free Plan</h3>
        <p className="text-gray-400 mb-4">
          Upgrade to unlock unlimited questions and advanced features.
        </p>
        <button
          onClick={() => router.push('/pricing')}
          className="bg-[#4169E1] text-white px-4 py-2 rounded-lg hover:bg-[#3558c0] transition-colors"
        >
          View Plans
        </button>
      </div>
    );
  }

  const tierName = subscription.tier === 'premium' ? 'Premium' : 'Student';
  const billingLabel = subscription.billing_cycle === 'yearly' ? 'Annual' : 'Monthly';

  return (
    <div className={`bg-gray-900 rounded-lg p-6 border border-gray-800 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white capitalize">
            {tierName} Plan
          </h3>
          <p className="text-gray-400 text-sm">
            {billingLabel} billing
          </p>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-sm ${
            subscription.in_grace_period
              ? 'bg-yellow-500/20 text-yellow-500'
              : subscription.cancelled_at
              ? 'bg-orange-500/20 text-orange-500'
              : subscription.stripe_status === 'active'
              ? 'bg-green-500/20 text-green-500'
              : 'bg-gray-500/20 text-gray-400'
          }`}
        >
          {subscription.in_grace_period
            ? 'Payment Issue'
            : subscription.cancelled_at
            ? 'Cancelling'
            : subscription.stripe_status === 'active'
            ? 'Active'
            : subscription.stripe_status || 'Unknown'}
        </span>
      </div>

      {/* Grace Period Warning */}
      {subscription.in_grace_period && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-4">
          <p className="text-yellow-500 text-sm">
            Your payment failed. Please update your payment method within{' '}
            <strong>{subscription.days_remaining_in_grace} days</strong> to avoid losing access.
          </p>
        </div>
      )}

      {/* Cancellation Notice */}
      {subscription.cancelled_at && !subscription.in_grace_period && (
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4 mb-4">
          <p className="text-orange-400 text-sm">
            Your subscription will end on{' '}
            <strong>
              {subscription.expires_at
                ? new Date(subscription.expires_at).toLocaleDateString()
                : 'the end of the billing period'}
            </strong>
            . You&apos;ll keep access until then.
          </p>
        </div>
      )}

      {/* Renewal Info */}
      {subscription.expires_at && !subscription.cancelled_at && !subscription.in_grace_period && (
        <p className="text-gray-400 text-sm mb-4">
          Renews on {new Date(subscription.expires_at).toLocaleDateString()}
        </p>
      )}

      {/* Error */}
      {error && (
        <p className="text-red-500 text-sm mb-4">{error}</p>
      )}

      {/* Manage Button */}
      <button
        onClick={handleManageSubscription}
        disabled={portalLoading}
        className={`w-full bg-gray-700 text-white px-4 py-2 rounded-lg hover:bg-gray-600 transition-colors ${
          portalLoading ? 'opacity-50 cursor-wait' : ''
        }`}
      >
        {portalLoading ? 'Opening...' : 'Manage Subscription'}
      </button>

      <p className="text-gray-500 text-xs mt-4 text-center">
        Update payment method, change plan, or cancel
      </p>
    </div>
  );
}
