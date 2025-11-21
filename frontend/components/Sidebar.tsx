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
  const router = useRouter();
  const { user } = useUser();

  return (
    <>
      {/* Sidebar */}
      <div
        className={`fixed left-0 top-0 h-full bg-black border-r border-gray-800 transition-all duration-300 z-50 ${
          isOpen ? 'w-64' : 'w-0'
        } overflow-hidden`}
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
                <p className="mt-3 text-sm text-gray-400 leading-relaxed">
                  Please email me at <a href="mailto:devaun0506@gmail.com" className="text-blue-400 hover:text-blue-300 underline">devaun0506@gmail.com</a> at anytime for feedback on this product.
                </p>
              )}
            </div>

            {/* About Me Section */}
            <div className="px-3 py-2 mb-4">
              <button
                onClick={() => setShowAbout(!showAbout)}
                className="text-lg font-semibold text-white hover:text-gray-300 transition-colors"
                style={{ fontFamily: 'var(--font-cormorant)' }}
              >
                About Me
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
                {clerkships.map((clerkship) => (
                  <button
                    key={clerkship.name}
                    onClick={() => clerkship.available && setSelectedSpecialty(clerkship.name)}
                    disabled={!clerkship.available}
                    className={`w-full text-left px-3 py-2 rounded transition-colors text-lg font-semibold ${
                      clerkship.available
                        ? selectedSpecialty === clerkship.name
                          ? 'bg-gray-900 text-white'
                          : 'text-gray-400 hover:text-white hover:bg-gray-900'
                        : 'text-gray-700 cursor-not-allowed'
                    }`}
                    style={{ fontFamily: 'var(--font-cormorant)' }}
                  >
                    {clerkship.name}
                    {!clerkship.available && (
                      <span className="ml-2 text-xs text-gray-600 font-normal">(Coming Soon)</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </nav>

          {/* Exit Door Icon at bottom right - only shown when NOT on home page */}
          {!isHomePage && (
            <div className="mt-auto pt-4 flex justify-end px-3 pb-4">
              <button
                onClick={() => router.push('/')}
                className="flex items-center gap-2 p-2 text-white hover:bg-gray-900 rounded-lg transition-colors group"
                title="Exit Session"
              >
                <svg
                  className="w-5 h-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  {/* Door frame */}
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  {/* Door opening */}
                  <path d="M9 3v18" />
                  {/* Door handle */}
                  <circle cx="15" cy="12" r="1" fill="currentColor" />
                </svg>
                <span className="text-sm opacity-0 group-hover:opacity-100 transition-opacity">Exit</span>
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
        className="fixed left-4 top-4 z-[60] px-3 py-2 text-gray-300 hover:text-white transition-colors text-2xl font-bold"
        style={{ lineHeight: '1' }}
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
