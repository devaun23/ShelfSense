'use client';

import { useRouter } from 'next/navigation';

export default function SubscriptionCancelPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>

        <h1 className="text-2xl font-bold text-white mb-4">
          Checkout Cancelled
        </h1>

        <p className="text-gray-400 mb-8">
          No worries! Your subscription was not processed.
          Feel free to continue exploring our free features or try again when you&apos;re ready.
        </p>

        <div className="space-y-4">
          <button
            onClick={() => router.push('/pricing')}
            className="block w-full bg-[#4169E1] text-white px-6 py-3 rounded-lg font-medium hover:bg-[#3558c0] transition-colors"
          >
            View Plans
          </button>
          <button
            onClick={() => router.push('/')}
            className="block w-full bg-gray-800 text-white px-6 py-3 rounded-lg font-medium hover:bg-gray-700 transition-colors"
          >
            Continue with Free
          </button>
        </div>

        <p className="text-gray-500 text-sm mt-8">
          Have questions? <a href="mailto:support@shelfsense.com" className="text-[#4169E1] hover:underline">Contact us</a>
        </p>
      </div>
    </div>
  );
}
