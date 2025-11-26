'use client';

import { useEffect } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { UserButton } from '@clerk/nextjs';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

// Simple specialty list - no colors, no emojis
const SHELF_EXAMS = [
  { id: 'im', name: 'Internal Medicine', apiName: 'Internal Medicine' },
  { id: 'surgery', name: 'Surgery', apiName: 'Surgery' },
  { id: 'peds', name: 'Pediatrics', apiName: 'Pediatrics' },
  { id: 'psych', name: 'Psychiatry', apiName: 'Psychiatry' },
  { id: 'obgyn', name: 'OB-GYN', apiName: 'Obstetrics and Gynecology' },
  { id: 'fm', name: 'Family Medicine', apiName: 'Family Medicine' },
  { id: 'em', name: 'Emergency', apiName: 'Emergency Medicine' },
  { id: 'neuro', name: 'Neurology', apiName: 'Neurology' },
];

export default function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user } = useUser();

  // Get current specialty from URL
  const currentSpecialty = searchParams.get('specialty');

  // Auto-close sidebar on mobile when navigating
  useEffect(() => {
    // Close on route change for mobile
    if (typeof window !== 'undefined' && window.innerWidth < 768 && isOpen) {
      // Small delay to allow navigation to start
      const timer = setTimeout(() => {
        if (window.innerWidth < 768) {
          onToggle();
        }
      }, 100);
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, searchParams]);

  const handleSpecialtyClick = (apiName: string | null) => {
    if (apiName) {
      router.push(`/study?specialty=${encodeURIComponent(apiName)}`);
    } else {
      router.push('/study');
    }
    if (window.innerWidth < 768) {
      onToggle();
    }
  };

  return (
    <>
      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-full bg-gray-950 border-r border-gray-900 transition-all duration-300 z-50 flex flex-col ${
          isOpen ? 'w-64' : 'w-0'
        } overflow-hidden`}
      >
        {/* Top Section - Logo */}
        <div className="p-4 flex-shrink-0">
          <button
            onClick={() => router.push('/')}
            className="text-xl font-semibold text-white hover:text-gray-300 transition-colors block"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            ShelfSense
          </button>
        </div>

        {/* Step 2 CK Prep Title */}
        <div className="px-4 py-3 flex-shrink-0">
          <button
            onClick={() => handleSpecialtyClick(null)}
            className={`text-lg font-medium transition-colors ${
              pathname === '/study' && !currentSpecialty
                ? 'text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Step 2 CK Prep
          </button>
        </div>

        {/* Shelf Exams Section */}
        <div className="px-4 flex-shrink-0">
          <div className="space-y-1">
            {SHELF_EXAMS.map((shelf) => (
              <button
                key={shelf.id}
                onClick={() => handleSpecialtyClick(shelf.apiName)}
                className={`w-full text-left px-3 py-2 text-base rounded-lg transition-colors ${
                  currentSpecialty === shelf.apiName
                    ? 'text-white bg-gray-800'
                    : 'text-gray-400 hover:text-white hover:bg-gray-900'
                }`}
              >
                {shelf.name}
              </button>
            ))}
          </div>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Quick Links - at bottom */}
        <nav className="flex-shrink-0 px-3 pb-3">
          <div className="border-t border-gray-900 pt-4">
            <button
              onClick={() => router.push('/analytics')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors ${
                pathname === '/analytics'
                  ? 'text-white bg-gray-900'
                  : 'text-gray-400 hover:text-white hover:bg-gray-900'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span>Analytics</span>
            </button>
            <button
              onClick={() => router.push('/reviews')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors ${
                pathname === '/reviews'
                  ? 'text-white bg-gray-900'
                  : 'text-gray-400 hover:text-white hover:bg-gray-900'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="3" y1="10" x2="21" y2="10" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="16" y1="2" x2="16" y2="6" />
              </svg>
              <span>Reviews</span>
            </button>
            <button
              onClick={() => router.push('/analytics?view=weak')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors ${
                pathname === '/analytics' && searchParams.get('view') === 'weak'
                  ? 'text-white bg-gray-900'
                  : 'text-gray-400 hover:text-white hover:bg-gray-900'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Weak Areas</span>
            </button>
          </div>
        </nav>

        {/* Bottom Section - User Profile */}
        {user && (
          <div className="flex-shrink-0 border-t border-gray-900 p-3">
            <div className="flex items-center gap-3 px-2 py-2">
              {/* Clerk UserButton */}
              <UserButton
                appearance={{
                  elements: {
                    avatarBox: 'w-8 h-8',
                  },
                }}
                afterSignOutUrl="/sign-in"
              />

              {/* Name */}
              <span className="text-sm text-gray-300 truncate flex-1 text-left">
                {user.firstName}
              </span>

              {/* Feedback button */}
              <div className="relative group">
                <button
                  onClick={() => window.location.href = 'mailto:devaun0506@gmail.com?subject=ShelfSense Feedback'}
                  className="p-1.5 text-gray-600 hover:text-gray-300 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                  </svg>
                </button>
                <span className="absolute right-full top-1/2 -translate-y-1/2 mr-2 px-2 py-1 text-xs text-white bg-gray-800 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                  Feedback
                </span>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Toggle Button - better mobile positioning */}
      <button
        onClick={onToggle}
        className={`fixed top-4 z-[60] p-2.5 text-gray-400 hover:text-white hover:bg-gray-900 rounded-lg transition-all ${
          isOpen ? 'left-[17rem]' : 'left-3 md:left-4'
        }`}
        aria-label={isOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {isOpen ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        )}
      </button>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden"
          onClick={onToggle}
        />
      )}
    </>
  );
}
