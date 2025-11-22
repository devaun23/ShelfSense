'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  isHomePage?: boolean;
}

const clerkships = [
  { name: 'Internal Medicine', available: true },
  { name: 'Surgery', available: false },
  { name: 'Pediatrics', available: false },
  { name: 'Obstetrics & Gynecology', available: false },
  { name: 'Family Medicine', available: false },
  { name: 'Emergency Medicine', available: false },
  { name: 'Neurology', available: false },
  { name: 'Psychiatry', available: false },
];

export default function Sidebar({ isOpen, onToggle, isHomePage = false }: SidebarProps) {
  const [selectedSpecialty, setSelectedSpecialty] = useState<string>('Internal Medicine');
  const [showFeedback, setShowFeedback] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);
  const [emailCopied, setEmailCopied] = useState(false);
  const router = useRouter();
  const { user } = useUser();

  const copyEmail = async () => {
    try {
      await navigator.clipboard.writeText('devaun0506@gmail.com');
      setEmailCopied(true);
      setTimeout(() => setEmailCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy email:', err);
    }
  };

  // Swipe detection - minimum swipe distance (in px)
  const minSwipeDistance = 50;

  const onTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;

    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;

    // Close sidebar on left swipe
    if (isLeftSwipe && isOpen) {
      onToggle();
    }

    setTouchStart(null);
    setTouchEnd(null);
  };

  return (
    <>
      {/* Sidebar - Full width on mobile, 256px on desktop */}
      <div
        className={`fixed left-0 top-0 h-full bg-black border-r border-gray-800 transition-all duration-300 z-50 ${
          isOpen ? 'w-full md:w-64' : 'w-0'
        } overflow-hidden`}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <div className="p-6 pt-16 h-full flex flex-col">
          <div className={`mb-6 transition-all duration-300 ${isOpen ? 'ml-8' : 'ml-0'}`}>
            <button
              onClick={() => router.push('/')}
              className="text-xl font-semibold hover:text-gray-300 transition-colors"
              style={{ fontFamily: 'var(--font-cormorant)' }}
            >
              ShelfSense
            </button>
          </div>

          <nav className="space-y-3 flex-1 overflow-y-auto">
            {/* Feedback Section */}
            <div className="px-3 py-2 mb-4">
              <button
                onClick={() => setShowFeedback(!showFeedback)}
                className="text-lg font-semibold text-white hover:text-gray-300 transition-colors"
                style={{ fontFamily: 'var(--font-cormorant)' }}
              >
                Feedback
              </button>
              {showFeedback && (
                <div className="mt-3 text-sm text-gray-400 leading-relaxed">
                  <p>Please email me at anytime for feedback on this product.</p>
                  <div className="mt-2 flex items-center gap-2">
                    <a href="mailto:devaun0506@gmail.com" className="text-blue-400 hover:text-blue-300 underline">
                      devaun0506@gmail.com
                    </a>
                    <button
                      onClick={copyEmail}
                      className="p-1 hover:bg-gray-800 rounded transition-colors"
                      title="Copy email address"
                    >
                      {emailCopied ? (
                        <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* About ShelfSense Section */}
            <div className="px-3 py-2 mb-4">
              <button
                onClick={() => setShowAbout(!showAbout)}
                className="text-lg font-semibold text-white hover:text-gray-300 transition-colors"
                style={{ fontFamily: 'var(--font-cormorant)' }}
              >
                About ShelfSense
              </button>
              {showAbout && (
                <p className="mt-3 text-sm text-gray-400 leading-relaxed">
                  Master Step 2 CK with intelligent, adaptive learning that focuses on your weak areas.
                  Our platform analyzes your performance in real time and delivers high quality practice
                  questions that mirror the exam. Study smarter, not harder. Every question is tailored
                  to maximize your score potential.
                </p>
              )}
            </div>

            {/* Step 2 CK Header */}
            <div className="px-3 py-2 border-t border-gray-800 pt-4">
              <h3 className="text-lg font-semibold text-gray-400" style={{ fontFamily: 'var(--font-cormorant)' }}>
                Step 2 CK
              </h3>
            </div>

            {/* Clerkships Section */}
            <div className="border-t border-gray-800 pt-3">
              <div className="px-3 pb-2">
                <p className="text-sm text-gray-500 uppercase tracking-wide">Clerkships</p>
              </div>

              <div className="space-y-1">
                {clerkships.filter(c => c.available).map((clerkship) => (
                  <button
                    key={clerkship.name}
                    onClick={() => setSelectedSpecialty(clerkship.name)}
                    className={`w-full text-left px-3 py-2 rounded transition-colors text-lg font-semibold ${
                      selectedSpecialty === clerkship.name
                        ? 'bg-gray-900 text-white'
                        : 'text-gray-400 hover:text-white hover:bg-gray-900'
                    }`}
                    style={{ fontFamily: 'var(--font-cormorant)' }}
                  >
                    {clerkship.name}
                  </button>
                ))}
              </div>
            </div>
          </nav>

          {/* User Profile Section at bottom */}
          {user && (
            <div className="mt-auto pt-4 border-t border-gray-800">
              <div className="px-3 py-3">
                <div className="text-sm text-gray-400 mb-1">Logged in as</div>
                <div className="text-white font-semibold mb-3">{user.firstName} {user.lastName}</div>
                <button
                  onClick={() => {
                    localStorage.removeItem('user');
                    router.push('/login');
                  }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-900 hover:bg-gray-800 text-red-400 hover:text-red-300 rounded-lg transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  <span>Logout</span>
                </button>
              </div>
            </div>
          )}

          {/* Home Icon at bottom right - only shown when NOT on home page */}
          {!isHomePage && (
            <div className="pt-4 flex justify-end px-3 pb-4">
              <button
                onClick={() => router.push('/')}
                className="flex items-center gap-2 px-3 py-2 text-gray-400 hover:text-white hover:bg-gray-900 rounded-lg transition-colors"
                aria-label="Go to home page"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span className="text-sm font-medium">Home</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Visual indicator line when sidebar is closed */}
      {!isOpen && (
        <div className="fixed left-0 top-0 h-full w-[1px] bg-gray-700 z-40" />
      )}

      {/* Toggle Button - Thicker and more visible */}
      <button
        onClick={onToggle}
        className="fixed left-4 top-4 z-[60] px-3 py-2 text-gray-300 hover:text-white transition-colors duration-200 text-2xl font-bold"
        style={{ lineHeight: '1' }}
        aria-label={isOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {isOpen ? '←' : '→'}
      </button>

      {/* Overlay when sidebar is open (mobile) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={onToggle}
        />
      )}
    </>
  );
}
