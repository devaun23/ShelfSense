'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { redirectToCheckout } from '@/lib/stripe';

interface Plan {
  tier: string;
  name: string;
  description: string;
  priceMonthly: number;
  priceYearly: number;
  yearlySavings?: number;
  features: string[];
  limitations?: string[];
  popular?: boolean;
}

const plans: Plan[] = [
  {
    tier: 'free',
    name: 'Free',
    description: 'Get started with basic features',
    priceMonthly: 0,
    priceYearly: 0,
    features: [
      '20 questions per day',
      '5 AI chat messages per day',
      '1 specialty (Internal Medicine)',
      'Basic analytics',
    ],
    limitations: [
      'No spaced repetition',
      'No error analysis',
      'No score prediction',
    ],
  },
  {
    tier: 'student',
    name: 'Student',
    description: 'Everything you need to ace Step 2 CK',
    priceMonthly: 29,
    priceYearly: 199,
    yearlySavings: 149,
    features: [
      'Unlimited questions',
      'Unlimited AI chat',
      'All 8 specialties',
      'Advanced analytics dashboard',
      'Full spaced repetition system',
      'Predicted score tracking',
      'Error analysis',
    ],
    popular: true,
  },
  {
    tier: 'premium',
    name: 'Premium',
    description: 'Maximum preparation with premium features',
    priceMonthly: 49,
    priceYearly: 349,
    yearlySavings: 239,
    features: [
      'Everything in Student',
      'Priority AI generation',
      'Personalized study plans',
      'Weekly progress reports',
      'Test simulation mode',
      'Priority support',
    ],
  },
];

export default function PricingPage() {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('yearly');
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const { user, isAuthenticated, getAccessToken } = useUser();

  const handleSubscribe = async (tier: 'student' | 'premium') => {
    if (!isAuthenticated || !user) {
      router.push('/sign-in?redirect_url=/pricing');
      return;
    }

    setLoading(tier);
    setError(null);

    try {
      const token = await getAccessToken();
      await redirectToCheckout(user.userId, tier, billingCycle, token || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start checkout');
      setLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white py-12 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">
            Choose Your Plan
          </h1>
          <p className="text-gray-400 text-lg mb-8">
            Unlock your full potential for Step 2 CK
          </p>

          {/* Billing Toggle */}
          <div className="flex items-center justify-center gap-4 mb-8">
            <span className={billingCycle === 'monthly' ? 'text-white' : 'text-gray-500'}>
              Monthly
            </span>
            <button
              onClick={() => setBillingCycle(prev => prev === 'monthly' ? 'yearly' : 'monthly')}
              className="relative w-14 h-7 bg-gray-700 rounded-full transition-colors"
            >
              <div
                className={`absolute top-1 w-5 h-5 bg-[#4169E1] rounded-full transition-transform ${
                  billingCycle === 'yearly' ? 'translate-x-7' : 'translate-x-1'
                }`}
              />
            </button>
            <span className={billingCycle === 'yearly' ? 'text-white' : 'text-gray-500'}>
              Yearly
              <span className="ml-2 text-green-500 text-sm">Save up to 43%</span>
            </span>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="max-w-md mx-auto mb-8 p-4 bg-red-500/10 border border-red-500 rounded-lg text-red-500 text-center">
            {error}
          </div>
        )}

        {/* Plans Grid */}
        <div className="grid md:grid-cols-3 gap-8">
          {plans.map((plan) => (
            <div
              key={plan.tier}
              className={`relative rounded-2xl border p-8 ${
                plan.popular
                  ? 'border-[#4169E1] bg-[#4169E1]/5'
                  : 'border-gray-800 bg-gray-900/50'
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#4169E1] text-white px-4 py-1 rounded-full text-sm font-medium">
                  Most Popular
                </div>
              )}

              <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
              <p className="text-gray-400 mb-6">{plan.description}</p>

              <div className="mb-6">
                <span className="text-4xl font-bold">
                  ${billingCycle === 'monthly' ? plan.priceMonthly : plan.priceYearly}
                </span>
                {plan.priceMonthly > 0 && (
                  <span className="text-gray-400">
                    /{billingCycle === 'monthly' ? 'mo' : 'yr'}
                  </span>
                )}
                {billingCycle === 'yearly' && plan.yearlySavings && (
                  <div className="text-green-500 text-sm mt-1">
                    Save ${plan.yearlySavings}/year
                  </div>
                )}
              </div>

              {plan.tier === 'free' ? (
                <button
                  onClick={() => router.push('/')}
                  className="w-full py-3 rounded-lg bg-gray-700 text-white hover:bg-gray-600 transition-colors"
                >
                  Get Started Free
                </button>
              ) : (
                <button
                  onClick={() => handleSubscribe(plan.tier as 'student' | 'premium')}
                  disabled={loading !== null}
                  className={`w-full py-3 rounded-lg font-medium transition-colors ${
                    plan.popular
                      ? 'bg-[#4169E1] hover:bg-[#3558c0] text-white'
                      : 'bg-gray-700 hover:bg-gray-600 text-white'
                  } ${loading === plan.tier ? 'opacity-50 cursor-wait' : ''} disabled:opacity-50`}
                >
                  {loading === plan.tier ? 'Redirecting...' : 'Subscribe'}
                </button>
              )}

              {/* Features */}
              <ul className="mt-8 space-y-3">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-gray-300">{feature}</span>
                  </li>
                ))}
                {plan.limitations?.map((limitation) => (
                  <li key={limitation} className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-gray-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                    <span className="text-gray-500">{limitation}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="text-center mt-12 space-y-4">
          <p className="text-gray-500">
            All plans include a 30-day money-back guarantee.
          </p>
          <p className="text-gray-500">
            Questions? <a href="mailto:support@shelfsense.com" className="text-[#4169E1] hover:underline">Contact us</a>
          </p>
        </div>
      </div>
    </div>
  );
}
