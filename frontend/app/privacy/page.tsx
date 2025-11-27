import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Privacy Policy - ShelfSense',
  description: 'Privacy Policy for ShelfSense, an adaptive learning platform for USMLE Step 2 CK preparation.',
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <h1
          className="text-4xl md:text-5xl font-semibold mb-4"
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          Privacy Policy
        </h1>
        <p className="text-gray-400 mb-12">Last updated: November 2024</p>

        <div className="space-y-10 text-gray-300 leading-relaxed">
          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              1. Introduction
            </h2>
            <p>
              ShelfSense (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) is committed to protecting
              your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard
              your information when you use our adaptive learning platform for USMLE Step 2 CK preparation.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              2. Information We Collect
            </h2>
            <p className="mb-4">We collect information in the following ways:</p>

            <h3 className="text-lg font-semibold text-white mt-6 mb-3">Account Information</h3>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Name and email address</li>
              <li>Authentication credentials (managed by our authentication provider)</li>
              <li>Profile information you choose to provide</li>
            </ul>

            <h3 className="text-lg font-semibold text-white mt-6 mb-3">Study Performance Data</h3>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Answers to practice questions</li>
              <li>Time spent on questions and study sessions</li>
              <li>Performance metrics and progress tracking</li>
              <li>Flagged questions and notes</li>
            </ul>

            <h3 className="text-lg font-semibold text-white mt-6 mb-3">Usage Information</h3>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Device and browser information</li>
              <li>IP address and general location</li>
              <li>Pages visited and features used</li>
              <li>Session duration and frequency</li>
            </ul>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              3. How We Use Your Information
            </h2>
            <p className="mb-4">We use the information we collect to:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Provide and maintain the Service</li>
              <li>Personalize your learning experience with adaptive algorithms</li>
              <li>Track your progress and generate performance analytics</li>
              <li>Process payments and manage subscriptions</li>
              <li>Send important updates about the Service</li>
              <li>Improve and optimize the platform</li>
              <li>Respond to your inquiries and support requests</li>
            </ul>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              4. Data Storage and Security
            </h2>
            <p className="mb-4">
              We implement appropriate technical and organizational security measures to protect your
              personal information, including:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Encryption of data in transit and at rest</li>
              <li>Secure authentication through industry-leading providers</li>
              <li>Regular security assessments and updates</li>
              <li>Access controls limiting who can view your data</li>
            </ul>
            <p className="mt-4">
              While we strive to protect your information, no method of transmission over the Internet
              is 100% secure. We cannot guarantee absolute security.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              5. Third-Party Services
            </h2>
            <p className="mb-4">We use trusted third-party services to operate ShelfSense:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>
                <strong className="text-white">Authentication:</strong> We use Clerk for secure user
                authentication and account management
              </li>
              <li>
                <strong className="text-white">Payment Processing:</strong> Payments are processed
                through secure, PCI-compliant payment processors
              </li>
              <li>
                <strong className="text-white">Hosting:</strong> Our application is hosted on secure
                cloud infrastructure
              </li>
            </ul>
            <p className="mt-4">
              These providers have their own privacy policies governing their use of your information.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              6. Cookies and Tracking
            </h2>
            <p className="mb-4">
              We use cookies and similar technologies to:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Keep you signed in to your account</li>
              <li>Remember your preferences</li>
              <li>Understand how you use the Service</li>
              <li>Improve your experience</li>
            </ul>
            <p className="mt-4">
              You can control cookies through your browser settings, but disabling them may affect
              Service functionality.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              7. Data Retention
            </h2>
            <p>
              We retain your personal information for as long as your account is active or as needed
              to provide you with the Service. Study performance data is retained to maintain your
              progress history. You may request deletion of your data at any time by contacting us.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              8. Your Rights
            </h2>
            <p className="mb-4">You have the right to:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Access the personal information we hold about you</li>
              <li>Request correction of inaccurate information</li>
              <li>Request deletion of your personal information</li>
              <li>Export your study data</li>
              <li>Opt out of marketing communications</li>
            </ul>
            <p className="mt-4">
              To exercise these rights, please contact us at the email address below.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              9. Children&apos;s Privacy
            </h2>
            <p>
              ShelfSense is intended for medical students and professionals. We do not knowingly
              collect information from children under 13 years of age. If you believe we have
              collected such information, please contact us immediately.
            </p>
          </section>

          <section>
            <h2
              className="text-2xl font-semibold text-white mb-4"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              10. Changes to This Policy
            </h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of any changes
              by posting the new Privacy Policy on this page and updating the &quot;Last updated&quot;
              date. Your continued use of the Service after changes constitutes acceptance of the
              updated policy.
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
              If you have questions about this Privacy Policy or our data practices, please contact us at{' '}
              <a
                href="mailto:privacy@shelfsense.app"
                className="text-[#4169E1] hover:text-[#5B7FE8] transition-colors"
              >
                privacy@shelfsense.app
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
            href="/terms"
            className="text-[#4169E1] hover:text-[#5B7FE8] transition-colors"
          >
            Terms of Service &rarr;
          </Link>
        </div>
      </div>
    </main>
  );
}
