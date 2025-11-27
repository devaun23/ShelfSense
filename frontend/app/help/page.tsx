'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import HelpSection from '@/components/help/HelpSection';
import Accordion, { FAQItem } from '@/components/help/Accordion';
import KeyboardShortcutTable from '@/components/help/KeyboardShortcutTable';
import HelpSearch from '@/components/help/HelpSearch';

const FAQ_ITEMS: FAQItem[] = [
  // Scoring & Analytics
  {
    id: 'predicted-score',
    category: 'scoring',
    question: 'How is my predicted score calculated?',
    answer: (
      <>
        Your predicted Step 2 CK score is calculated using a weighted algorithm that considers your
        overall accuracy, performance on difficult questions, consistency over time, and how you
        compare to historical data from students who took the actual exam. The confidence interval
        (±) indicates the range where your true score is likely to fall.
      </>
    ),
  },
  {
    id: 'accuracy-vs-weighted',
    category: 'scoring',
    question: "What's the difference between accuracy and weighted accuracy?",
    answer: (
      <>
        <strong className="text-white">Accuracy</strong> is simply your correct answers divided by
        total questions. <strong className="text-white">Weighted accuracy</strong> gives more
        importance to harder questions and topics that appear more frequently on the actual exam.
        This provides a more realistic prediction of exam performance.
      </>
    ),
  },
  {
    id: 'weak-areas',
    category: 'scoring',
    question: 'How are weak areas identified?',
    answer: (
      <>
        Weak areas are identified by analyzing your accuracy by topic/specialty, question difficulty,
        and how recently you&apos;ve studied that material. Topics where you score below 60% accuracy
        with sufficient sample size are flagged as areas needing improvement. The priority score
        factors in how important that topic is for the exam.
      </>
    ),
  },
  {
    id: 'trend-meaning',
    category: 'scoring',
    question: 'What do the trend indicators mean?',
    answer: (
      <>
        <strong className="text-white">Improving (↑)</strong>: Your recent performance is better than
        your historical average. <strong className="text-white">Stable (→)</strong>: Your performance
        is consistent. <strong className="text-white">Declining (↓)</strong>: Your recent performance
        is below your average - consider reviewing weak areas or adjusting study strategies.
      </>
    ),
  },
  // Study Features
  {
    id: 'study-modes',
    category: 'study',
    question: 'How do the different study modes work?',
    answer: (
      <>
        <ul className="list-disc list-inside space-y-2 mt-2">
          <li>
            <strong className="text-white">Practice Mode</strong>: Free-form study with immediate
            feedback after each question
          </li>
          <li>
            <strong className="text-white">Timed Test</strong>: Simulates exam conditions with 40
            questions in 60 minutes
          </li>
          <li>
            <strong className="text-white">Tutor Mode</strong>: Get detailed explanations and hints
            as you study
          </li>
          <li>
            <strong className="text-white">Challenge Mode</strong>: Focus on difficult questions only
          </li>
          <li>
            <strong className="text-white">Review Mode</strong>: Spaced repetition for previously
            answered questions
          </li>
        </ul>
      </>
    ),
  },
  {
    id: 'flag-questions',
    category: 'study',
    question: 'Can I flag questions for later review?',
    answer: (
      <>
        Yes! Click the flag icon on any question to mark it for later. You can access all flagged
        questions from the Reviews section. This is useful for questions you want to revisit or
        discuss with classmates.
      </>
    ),
  },
  {
    id: 'ai-tutor',
    category: 'study',
    question: 'How does the AI tutoring feature work?',
    answer: (
      <>
        The AI tutor provides personalized explanations when you answer incorrectly. It analyzes your
        error type (knowledge gap, reasoning error, etc.) and provides targeted feedback. You can also
        ask follow-up questions to deepen your understanding of the concept.
      </>
    ),
  },
  {
    id: 'spaced-repetition',
    category: 'study',
    question: 'How does spaced repetition work?',
    answer: (
      <>
        Questions you answer are scheduled for review based on how well you knew them:
        <ul className="list-disc list-inside space-y-1 mt-2">
          <li>
            <strong className="text-white">New</strong>: First time seeing a question
          </li>
          <li>
            <strong className="text-white">Learning</strong>: Reviewed in 1-3 days
          </li>
          <li>
            <strong className="text-white">Review</strong>: Reviewed in 7-14 days
          </li>
          <li>
            <strong className="text-white">Mastered</strong>: Reviewed every 30+ days
          </li>
        </ul>
        Incorrect answers reset the interval. This optimizes long-term retention.
      </>
    ),
  },
  // Account & Technical
  {
    id: 'progress-sync',
    category: 'account',
    question: "Why won't my progress sync across devices?",
    answer: (
      <>
        Progress syncs automatically when you&apos;re logged in. If you&apos;re having issues: (1)
        Make sure you&apos;re signed into the same account on both devices. (2) Check your internet
        connection. (3) Try refreshing the page. (4) Clear your browser cache and log in again.
        Contact support if issues persist.
      </>
    ),
  },
  {
    id: 'browsers',
    category: 'account',
    question: 'Which browsers are supported?',
    answer: (
      <>
        ShelfSense works best on modern browsers: Chrome (recommended), Firefox, Safari, and Edge. We
        recommend keeping your browser updated to the latest version for the best experience. Mobile
        browsers are supported but the desktop experience is optimized for study sessions.
      </>
    ),
  },
  {
    id: 'reset-password',
    category: 'account',
    question: 'How do I reset my password?',
    answer: (
      <>
        Click your profile icon in the sidebar, then select &quot;Manage Account&quot; to access your
        account settings through Clerk. From there you can update your password, email, or other
        account details.
      </>
    ),
  },
  {
    id: 'delete-account',
    category: 'account',
    question: 'How do I delete my account and data?',
    answer: (
      <>
        To delete your account and all associated data, please contact us at{' '}
        <a
          href="mailto:devaun0506@gmail.com?subject=Account Deletion Request"
          className="text-[#4169E1] hover:text-[#5B7FE8] transition-colors"
        >
          devaun0506@gmail.com
        </a>{' '}
        with the subject &quot;Account Deletion Request&quot;. We&apos;ll process your request within
        7 days.
      </>
    ),
  },
];

const NAV_ITEMS = [
  { id: 'getting-started', label: 'Getting Started' },
  { id: 'study-modes', label: 'Study Modes' },
  { id: 'keyboard-shortcuts', label: 'Shortcuts' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'faq', label: 'FAQ' },
  { id: 'contact', label: 'Contact' },
];

export default function HelpPage() {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  return (
    <main className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-black/80 backdrop-blur-sm border-b border-gray-900">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="text-xl font-semibold text-white hover:text-gray-300 transition-colors"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            ShelfSense
          </Link>
          <Link
            href="/study"
            className="px-4 py-2 text-sm bg-[#4169E1] hover:bg-[#5B7FE8] text-white rounded-full transition-colors"
          >
            Start Studying
          </Link>
        </div>
      </header>

      {/* Quick Nav */}
      <nav className="sticky top-[65px] z-30 bg-black/80 backdrop-blur-sm border-b border-gray-900 overflow-x-auto">
        <div className="max-w-4xl mx-auto px-6">
          <div className="flex gap-6 py-3">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                className="text-sm text-gray-400 hover:text-white whitespace-nowrap transition-colors"
              >
                {item.label}
              </a>
            ))}
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <h1
            className="text-4xl md:text-5xl font-semibold mb-4"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Help Center
          </h1>
          <p className="text-gray-400 text-lg">
            Everything you need to know about using ShelfSense
          </p>
        </div>

        <div className="space-y-16">
          {/* Getting Started */}
          <HelpSection id="getting-started" title="Getting Started">
            <div className="space-y-4">
              <p>
                Welcome to ShelfSense! Here&apos;s how to get the most out of your study sessions:
              </p>
              <ol className="list-decimal list-inside space-y-3 ml-2">
                <li>
                  <strong className="text-white">Create your account</strong> - Sign up with your
                  email to track your progress across devices.
                </li>
                <li>
                  <strong className="text-white">Choose your focus</strong> - Select Step 2 CK for
                  comprehensive prep, or pick a specific shelf exam from the sidebar.
                </li>
                <li>
                  <strong className="text-white">Start a study session</strong> - Click
                  &quot;Practice&quot; for flexible studying, or &quot;Timed Test&quot; to simulate
                  exam conditions.
                </li>
                <li>
                  <strong className="text-white">Review your analytics</strong> - Check the Analytics
                  page to see your predicted score, weak areas, and progress over time.
                </li>
                <li>
                  <strong className="text-white">Use spaced repetition</strong> - Visit Reviews daily
                  to reinforce what you&apos;ve learned.
                </li>
              </ol>
            </div>
          </HelpSection>

          {/* Study Modes */}
          <HelpSection id="study-modes" title="Study Modes">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="p-4 bg-gray-900/50 border border-gray-800 rounded-xl">
                <h3 className="text-white font-medium mb-2">Practice Mode</h3>
                <p className="text-sm text-gray-400">
                  Free-form studying with immediate feedback. Great for learning new material.
                </p>
              </div>
              <div className="p-4 bg-gray-900/50 border border-gray-800 rounded-xl">
                <h3 className="text-white font-medium mb-2">Timed Test</h3>
                <p className="text-sm text-gray-400">
                  40 questions in 60 minutes. Simulates real exam pressure and pacing.
                </p>
              </div>
              <div className="p-4 bg-gray-900/50 border border-gray-800 rounded-xl">
                <h3 className="text-white font-medium mb-2">Tutor Mode</h3>
                <p className="text-sm text-gray-400">
                  Get AI-powered hints and explanations as you work through questions.
                </p>
              </div>
              <div className="p-4 bg-gray-900/50 border border-gray-800 rounded-xl">
                <h3 className="text-white font-medium mb-2">Challenge Mode</h3>
                <p className="text-sm text-gray-400">
                  Only high-difficulty questions. Test your knowledge at the edge of mastery.
                </p>
              </div>
              <div className="p-4 bg-gray-900/50 border border-gray-800 rounded-xl sm:col-span-2">
                <h3 className="text-white font-medium mb-2">Review Mode</h3>
                <p className="text-sm text-gray-400">
                  Spaced repetition system that schedules questions at optimal intervals for
                  long-term retention.
                </p>
              </div>
            </div>
          </HelpSection>

          {/* Keyboard Shortcuts */}
          <HelpSection id="keyboard-shortcuts" title="Keyboard Shortcuts">
            <p className="mb-4">Speed up your studying with these keyboard shortcuts:</p>
            <KeyboardShortcutTable />
          </HelpSection>

          {/* Analytics */}
          <HelpSection id="analytics" title="Understanding Your Analytics">
            <div className="space-y-6">
              <div>
                <h3 className="text-white font-medium mb-2">Predicted Score</h3>
                <p className="text-gray-400">
                  Your predicted Step 2 CK score is based on your performance compared to historical
                  data. The confidence interval (±) shows the range where your actual score is likely
                  to fall. This becomes more accurate as you answer more questions.
                </p>
              </div>
              <div>
                <h3 className="text-white font-medium mb-2">Accuracy Metrics</h3>
                <p className="text-gray-400">
                  <strong className="text-white">Overall Accuracy</strong> is your raw percentage
                  correct. <strong className="text-white">Weighted Accuracy</strong> adjusts for
                  question difficulty and topic importance, giving a more realistic exam prediction.
                </p>
              </div>
              <div>
                <h3 className="text-white font-medium mb-2">Weak Areas</h3>
                <p className="text-gray-400">
                  Topics where you score below 60% are highlighted as weak areas. Focus your studying
                  here for maximum improvement. The &quot;Weak Areas&quot; button in the sidebar takes you
                  directly to targeted practice.
                </p>
              </div>
              <div>
                <h3 className="text-white font-medium mb-2">Study Patterns</h3>
                <p className="text-gray-400">
                  The Insights tab shows your optimal study times, error patterns, and confidence
                  calibration. Use this data to optimize when and how you study.
                </p>
              </div>
            </div>
          </HelpSection>

          {/* FAQ */}
          <section id="faq" className="scroll-mt-24">
            <h2
              className="text-2xl font-semibold text-white mb-6"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              Frequently Asked Questions
            </h2>
            <div className="mb-6">
              <HelpSearch onSearch={handleSearch} placeholder="Search FAQs..." />
            </div>
            <Accordion items={FAQ_ITEMS} searchQuery={searchQuery} />
          </section>

          {/* Contact */}
          <HelpSection id="contact" title="Contact & Feedback">
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
              <p className="mb-4">
                Can&apos;t find what you&apos;re looking for? We&apos;re here to help!
              </p>
              <div className="flex flex-wrap gap-4">
                <a
                  href="mailto:devaun0506@gmail.com?subject=ShelfSense Support"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-[#4169E1] hover:bg-[#5B7FE8] text-white rounded-lg transition-colors"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                  Email Support
                </a>
                <a
                  href="mailto:devaun0506@gmail.com?subject=ShelfSense Feedback"
                  className="inline-flex items-center gap-2 px-4 py-2 border border-gray-700 hover:border-gray-600 text-gray-300 hover:text-white rounded-lg transition-colors"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
                    />
                  </svg>
                  Send Feedback
                </a>
              </div>
            </div>
          </HelpSection>
        </div>

        {/* Footer */}
        <div className="mt-16 pt-8 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Link
            href="/"
            className="text-[#4169E1] hover:text-[#5B7FE8] transition-colors"
          >
            &larr; Back to Home
          </Link>
          <div className="flex gap-6">
            <Link
              href="/terms"
              className="text-gray-500 hover:text-white transition-colors text-sm"
            >
              Terms
            </Link>
            <Link
              href="/privacy"
              className="text-gray-500 hover:text-white transition-colors text-sm"
            >
              Privacy
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
