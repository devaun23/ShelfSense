'use client';

import { useState, useEffect } from 'react';
import { useUser } from '@/contexts/UserContext';
import { getPaymentStatus, redirectToPortal, PaymentStatus } from '@/lib/stripe';

interface PaymentStatusBannerProps {
  className?: string;
}

export default function PaymentStatusBanner({ className = '' }: PaymentStatusBannerProps) {
  const { user, getAccessToken } = useUser();
  const [subscription, setSubscription] = useState<PaymentStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (user) {
      fetchStatus();
    }
  }, [user]);

  const fetchStatus = async () => {
    if (!user) return;

    try {
      const token = await getAccessToken();
      const status = await getPaymentStatus(user.userId, token || undefined);
      setSubscription(status);
    } catch (err) {
      console.error('Error fetching payment status:', err);
    }
  };

  const handleUpdatePayment = async () => {
    if (!user) return;

    setLoading(true);
    try {
      const token = await getAccessToken();
      await redirectToPortal(user.userId, token || undefined);
    } catch (err) {
      console.error('Error opening portal:', err);
      setLoading(false);
    }
  };

  // Don't show banner if:
  // - No subscription data
  // - Not in grace period
  // - User dismissed it
  if (!subscription || !subscription.in_grace_period || dismissed) {
    return null;
  }

  const daysRemaining = subscription.days_remaining_in_grace || 0;

  return (
    <div className={`bg-yellow-500 text-black ${className}`}>
      <div className="max-w-7xl mx-auto px-4 py-2 flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span className="font-medium">
            Payment failed.{' '}
            {daysRemaining > 0 ? (
              <>You have <strong>{daysRemaining} day{daysRemaining !== 1 ? 's' : ''}</strong> to update your payment method.</>
            ) : (
              <>Please update your payment method to keep your subscription.</>
            )}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleUpdatePayment}
            disabled={loading}
            className="bg-black text-white px-4 py-1 rounded font-medium hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            {loading ? 'Opening...' : 'Update Payment'}
          </button>
          <button
            onClick={() => setDismissed(true)}
            className="text-black/70 hover:text-black p-1"
            aria-label="Dismiss"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
