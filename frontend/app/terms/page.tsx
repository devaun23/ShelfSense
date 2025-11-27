import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Terms of Service - ShelfSense',
  description: 'Terms of Service for ShelfSense, an adaptive learning platform for USMLE Step 2 CK preparation.',
};

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <h1
          className="text-4xl md:text-5xl font-semibold mb-4"
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          Terms of Service
        </h1>
        <p className="text-gray-400 mb-12">Last updated: November 2024</p>

        <div className="space-y-10 text-gray-300 leading-relaxed">
          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              1. Acceptance of Terms
            </h2>
            <p>
              By accessing or using ShelfSense (&quot;the Service&quot;), you agree to be bound by these
              Terms of Service. If you do not agree to these terms, please do not use the Service.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              2. Description of Service
            </h2>
            <p>
              ShelfSense is an adaptive learning platform designed to help medical students prepare
              for USMLE Step 2 CK examinations. The Service provides practice questions, performance
              analytics, and personalized study recommendations.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              3. Account Registration
            </h2>
            <p className="mb-4">
              To use the Service, you must create an account. You agree to:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Provide accurate and complete registration information</li>
              <li>Maintain the security of your account credentials</li>
              <li>Accept responsibility for all activities under your account</li>
              <li>Notify us immediately of any unauthorized use of your account</li>
            </ul>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              4. Subscription and Payment
            </h2>
            <p className="mb-4">
              ShelfSense offers subscription-based access to premium features. By subscribing, you agree to:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Pay all applicable fees as described at the time of purchase</li>
              <li>Automatic renewal of your subscription unless cancelled before the renewal date</li>
              <li>Provide accurate billing information</li>
            </ul>
            <p className="mt-4">
              Refunds may be available in accordance with our refund policy. Contact us for details.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              5. Intellectual Property
            </h2>
            <p>
              All content on ShelfSense, including but not limited to questions, explanations, graphics,
              logos, and software, is the property of ShelfSense or its licensors and is protected by
              intellectual property laws. You may not copy, modify, distribute, or create derivative
              works without our express written permission.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              6. User Conduct
            </h2>
            <p className="mb-4">You agree not to:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Share your account credentials with others</li>
              <li>Copy, reproduce, or distribute any content from the Service</li>
              <li>Attempt to reverse engineer or extract source code from the Service</li>
              <li>Use the Service for any unlawful purpose</li>
              <li>Interfere with or disrupt the Service or its servers</li>
            </ul>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              7. Educational Disclaimer
            </h2>
            <p className="mb-4">
              <strong className="text-white">ShelfSense is an educational tool only.</strong> The content
              provided is for study and exam preparation purposes and should not be considered medical advice.
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Do not use this Service to make clinical decisions or treat patients</li>
              <li>Always consult qualified healthcare professionals for medical guidance</li>
              <li>We do not guarantee exam success or specific score improvements</li>
            </ul>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              8. Limitation of Liability
            </h2>
            <p>
              To the maximum extent permitted by law, ShelfSense and its affiliates shall not be liable
              for any indirect, incidental, special, consequential, or punitive damages, including loss
              of profits, data, or other intangible losses, resulting from your use or inability to use
              the Service.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              9. Termination
            </h2>
            <p>
              We reserve the right to suspend or terminate your account at any time for violation of
              these Terms or for any other reason at our sole discretion. Upon termination, your right
              to use the Service will immediately cease.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              10. Changes to Terms
            </h2>
            <p>
              We may modify these Terms at any time. We will notify users of significant changes via
              email or through the Service. Your continued use of the Service after changes constitutes
              acceptance of the modified Terms.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              11. Contact Us
            </h2>
            <p>
              If you have questions about these Terms, please contact us at{' '}
              <a
                href="mailto:support@shelfsense.app"
                className="text-[#4169E1] hover:text-[#5B7FE8] transition-colors"
              >
                support@shelfsense.app
              </a>
            </p>
          </section>
        </div>

        <div className="mt-16 pt-8 border-t border-gray-800 flex items-center justify-between">
          <Link
            href="/"
            className="text-[#4169E1] hover:text-[#5B7FE8] transition-colors"
          >
            &larr; Back to Home
          </Link>
          <Link
            href="/privacy"
            className="text-[#4169E1] hover:text-[#5B7FE8] transition-colors"
          >
            Privacy Policy &rarr;
          </Link>
        </div>
      </div>
    </main>
  );
}
