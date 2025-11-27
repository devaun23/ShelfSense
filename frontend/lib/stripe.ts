/**
 * Stripe Utility Functions
 *
 * Handles Stripe checkout and portal session creation
 */

import { loadStripe } from '@stripe/stripe-js';

const stripePublishableKey = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;

// Initialize Stripe
export const stripePromise = stripePublishableKey
  ? loadStripe(stripePublishableKey)
  : null;

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types
export interface CheckoutSessionResponse {
  checkout_url: string;
  session_id: string;
}

export interface PortalSessionResponse {
  portal_url: string;
}

export interface PaymentStatus {
  tier: string;
  stripe_status: string | null;
  payment_status: string;
  billing_cycle: string | null;
  expires_at: string | null;
  cancelled_at: string | null;
  grace_period_ends_at: string | null;
  in_grace_period: boolean;
  days_remaining_in_grace: number | null;
}

/**
 * Create a Stripe Checkout session for subscription purchase
 */
export async function createCheckoutSession(
  userId: string,
  tier: 'student' | 'premium',
  billingCycle: 'monthly' | 'yearly',
  token?: string
): Promise<CheckoutSessionResponse> {
  const response = await fetch(
    `${API_URL}/api/payments/create-checkout-session?user_id=${userId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        tier,
        billing_cycle: billingCycle,
      }),
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create checkout session');
  }

  return response.json();
}

/**
 * Create a Stripe Customer Portal session for subscription management
 */
export async function createPortalSession(
  userId: string,
  token?: string
): Promise<PortalSessionResponse> {
  const response = await fetch(
    `${API_URL}/api/payments/create-portal-session?user_id=${userId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create portal session');
  }

  return response.json();
}

/**
 * Get current payment status
 */
export async function getPaymentStatus(
  userId: string,
  token?: string
): Promise<PaymentStatus> {
  const response = await fetch(
    `${API_URL}/api/payments/status?user_id=${userId}`,
    {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get payment status');
  }

  return response.json();
}

/**
 * Verify a checkout session completed successfully
 */
export async function verifyCheckoutSession(
  sessionId: string,
  userId: string,
  token?: string
): Promise<{
  success: boolean;
  status: string;
  tier?: string;
  billing_cycle?: string;
  message?: string;
}> {
  const response = await fetch(
    `${API_URL}/api/payments/verify-session/${sessionId}?user_id=${userId}`,
    {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to verify session');
  }

  return response.json();
}

/**
 * Redirect to Stripe Checkout
 */
export async function redirectToCheckout(
  userId: string,
  tier: 'student' | 'premium',
  billingCycle: 'monthly' | 'yearly',
  token?: string
): Promise<void> {
  const { checkout_url } = await createCheckoutSession(userId, tier, billingCycle, token);
  window.location.href = checkout_url;
}

/**
 * Redirect to Stripe Customer Portal
 */
export async function redirectToPortal(
  userId: string,
  token?: string
): Promise<void> {
  const { portal_url } = await createPortalSession(userId, token);
  window.location.href = portal_url;
}
