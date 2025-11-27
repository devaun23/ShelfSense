'use client';

import { useEffect, useRef, useCallback } from 'react';
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
  { id: 'obgyn', name: 'OBGYN', apiName: 'Obstetrics and Gynecology' },
  { id: 'fm', name: 'Family Medicine', apiName: 'Family Medicine' },
  { id: 'em', name: 'Emergency Medicine', apiName: 'Emergency Medicine' },
  { id: 'neuro', name: 'Neurology', apiName: 'Neurology' },
];

export default function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user } = useUser();
  const sidebarRef = useRef<HTMLElement>(null);
  const firstFocusableRef = useRef<HTMLButtonElement>(null);
  const lastFocusableRef = useRef<HTMLButtonElement>(null);

  // Get current specialty from URL
  const currentSpecialty = searchParams.get('specialty');

  // Handle ESC key to close sidebar
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && isOpen) {
      onToggle();
    }

    // Focus trap for mobile
    if (e.key === 'Tab' && isOpen && window.innerWidth < 768) {
      const focusableElements = sidebarRef.current?.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!focusableElements || focusableElements.length === 0) return;

      const firstElement = focusableElements[0] as HTMLElement;
      const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    }
  }, [isOpen, onToggle]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Focus first element when sidebar opens on mobile
  useEffect(() => {
    if (isOpen && window.innerWidth < 768 && firstFocusableRef.current) {
      firstFocusableRef.current.focus();
    }
  }, [isOpen]);

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
        ref={sidebarRef}
        className={`fixed left-0 top-0 h-full bg-gray-950 border-r border-gray-900 transition-all duration-300 z-50 flex flex-col ${
          isOpen ? 'w-64' : 'w-0'
        } overflow-hidden`}
        role="navigation"
        aria-label="Main navigation"
        aria-hidden={!isOpen}
      >
        {/* Top Section - Logo */}
        <div className="p-4 flex-shrink-0">
          <button
            ref={firstFocusableRef}
            onClick={() => router.push('/')}
            className="text-xl font-semibold text-white hover:text-gray-300 transition-colors block focus:outline-none focus:ring-2 focus:ring-[#4169E1] focus:ring-offset-2 focus:ring-offset-gray-950 rounded"
            style={{ fontFamily: 'var(--font-serif)' }}
            tabIndex={isOpen ? 0 : -1}
          >
            ShelfSense
          </button>
        </div>

        {/* Step 2 CK Prep - separate tab */}
        <div className="px-4 pb-2 flex-shrink-0">
          <button
            onClick={() => handleSpecialtyClick(null)}
            className={`w-full text-left px-3 py-2 text-lg rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[#4169E1] ${
              pathname === '/study' && !currentSpecialty
                ? 'text-white bg-gray-800'
                : 'text-gray-200 hover:text-white hover:bg-gray-900'
            }`}
            style={{ fontFamily: 'var(--font-serif)' }}
            tabIndex={isOpen ? 0 : -1}
            aria-current={pathname === '/study' && !currentSpecialty ? 'page' : undefined}
          >
            Step 2 CK Prep
          </button>
        </div>

        {/* Shelf Exams Section */}
        <div className="px-4 flex-shrink-0" role="group" aria-labelledby="shelf-exams-label">
          <div id="shelf-exams-label" className="px-3 py-2 text-xs text-gray-600 font-medium uppercase tracking-wider">
            Shelf Exams
          </div>
          <div className="space-y-1">
            {SHELF_EXAMS.map((shelf) => (
              <button
                key={shelf.id}
                onClick={() => handleSpecialtyClick(shelf.apiName)}
                className={`w-full text-left px-3 py-2 text-lg rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[#4169E1] ${
                  currentSpecialty === shelf.apiName
                    ? 'text-white bg-gray-800'
                    : 'text-gray-200 hover:text-white hover:bg-gray-900'
                }`}
                style={{ fontFamily: 'var(--font-serif)' }}
                tabIndex={isOpen ? 0 : -1}
                aria-current={currentSpecialty === shelf.apiName ? 'page' : undefined}
              >
                {shelf.name}
              </button>
            ))}
          </div>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Quick Links - at bottom */}
        <nav className="flex-shrink-0 px-3 pb-3" aria-label="Quick links">
          <div className="border-t border-gray-900 pt-4">
            <button
              onClick={() => router.push('/analytics')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[#4169E1] ${
                pathname === '/analytics' && searchParams.get('view') !== 'weak'
                  ? 'text-white bg-gray-900'
                  : 'text-gray-400 hover:text-white hover:bg-gray-900'
              }`}
              tabIndex={isOpen ? 0 : -1}
              aria-current={pathname === '/analytics' && searchParams.get('view') !== 'weak' ? 'page' : undefined}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span>Analytics</span>
            </button>
            <button
              onClick={() => router.push('/reviews')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[#4169E1] ${
                pathname === '/reviews'
                  ? 'text-white bg-gray-900'
                  : 'text-gray-400 hover:text-white hover:bg-gray-900'
              }`}
              tabIndex={isOpen ? 0 : -1}
              aria-current={pathname === '/reviews' ? 'page' : undefined}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="3" y1="10" x2="21" y2="10" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="16" y1="2" x2="16" y2="6" />
              </svg>
              <span>Reviews</span>
            </button>
            <button
              onClick={() => router.push('/analytics?view=weak')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[#4169E1] ${
                pathname === '/analytics' && searchParams.get('view') === 'weak'
                  ? 'text-white bg-gray-900'
                  : 'text-gray-400 hover:text-white hover:bg-gray-900'
              }`}
              tabIndex={isOpen ? 0 : -1}
              aria-current={pathname === '/analytics' && searchParams.get('view') === 'weak' ? 'page' : undefined}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Weak Areas</span>
            </button>
            <button
              ref={user?.isAdmin ? undefined : lastFocusableRef}
              onClick={() => router.push('/help')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[#4169E1] ${
                pathname === '/help'
                  ? 'text-white bg-gray-900'
                  : 'text-gray-400 hover:text-white hover:bg-gray-900'
              }`}
              tabIndex={isOpen ? 0 : -1}
              aria-current={pathname === '/help' ? 'page' : undefined}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Help</span>
            </button>
            {user?.isAdmin && (
              <button
                ref={lastFocusableRef}
                onClick={() => router.push('/admin')}
                className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[#4169E1] ${
                  pathname.startsWith('/admin')
                    ? 'text-white bg-gray-900'
                    : 'text-gray-400 hover:text-white hover:bg-gray-900'
                }`}
                tabIndex={isOpen ? 0 : -1}
                aria-current={pathname.startsWith('/admin') ? 'page' : undefined}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span>Admin</span>
              </button>
            )}
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
          aria-hidden="true"
        />
      )}
    </>
  );
}
