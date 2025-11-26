'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { UserButton, SignOutButton } from '@clerk/nextjs';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

interface StudySession {
  id: string;
  date: string;
  questionsAnswered: number;
  correctCount: number;
  topic?: string;
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
  const [sessions, setSessions] = useState<StudySession[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user } = useUser();

  // Get current specialty from URL
  const currentSpecialty = searchParams.get('specialty');

  // Auto-close sidebar on mobile when navigating
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768 && isOpen) {
        onToggle();
      }
    };
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
  }, [pathname, searchParams]);

  // Get user initials for avatar
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  // Load session history
  useEffect(() => {
    if (user) {
      loadSessionHistory();
    }
  }, [user]);

  const loadSessionHistory = async () => {
    if (!user) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/analytics/sessions?user_id=${user.userId}`);
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
    }
  };

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


  // Group sessions by date
  const groupSessionsByDate = (sessions: StudySession[]) => {
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();

    const groups: { [key: string]: StudySession[] } = {
      'Today': [],
      'Yesterday': [],
      'Previous 7 Days': [],
      'Older': []
    };

    sessions.forEach(session => {
      const sessionDate = new Date(session.date).toDateString();
      const daysDiff = Math.floor((Date.now() - new Date(session.date).getTime()) / 86400000);

      if (sessionDate === today) {
        groups['Today'].push(session);
      } else if (sessionDate === yesterday) {
        groups['Yesterday'].push(session);
      } else if (daysDiff <= 7) {
        groups['Previous 7 Days'].push(session);
      } else {
        groups['Older'].push(session);
      }
    });

    return groups;
  };

  const groupedSessions = groupSessionsByDate(sessions);

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
            style={{ fontFamily: 'var(--font-cormorant)' }}
          >
            ShelfSense
          </button>
        </div>

        {/* Shelf Exams Section */}
        <div className="px-3 flex-shrink-0">
          <div className="px-2 py-2 text-xs text-gray-600 font-medium uppercase tracking-wider">
            Shelf Exams
          </div>
          <div className="flex flex-wrap gap-1.5 mb-4">
            {SHELF_EXAMS.map((shelf) => (
              <button
                key={shelf.id}
                onClick={() => handleSpecialtyClick(shelf.apiName)}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  currentSpecialty === shelf.apiName
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-500 hover:text-gray-300 hover:bg-gray-900'
                }`}
              >
                {shelf.name}
              </button>
            ))}
          </div>

          {/* Step 2 CK */}
          <button
            onClick={() => handleSpecialtyClick(null)}
            className={`w-full px-3 py-2 text-sm rounded-lg transition-colors text-left ${
              pathname === '/study' && !currentSpecialty
                ? 'bg-gray-800 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-900'
            }`}
          >
            Step 2 CK (All Topics)
          </button>
        </div>

        {/* Divider */}
        <div className="border-t border-gray-900 mx-3 my-3" />

        {/* Session History */}
        <nav className="flex-1 overflow-y-auto px-2 py-2">
          {Object.entries(groupedSessions).map(([period, periodSessions]) => {
            if (periodSessions.length === 0) return null;

            return (
              <div key={period} className="mb-4">
                <div className="px-3 py-2 text-xs text-gray-600 font-medium">
                  {period}
                </div>
                <div className="space-y-1">
                  {periodSessions.map((session) => (
                    <button
                      key={session.id}
                      className="w-full text-left px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-900 rounded-lg transition-colors truncate"
                    >
                      {session.topic || `${session.questionsAnswered} questions`}
                      <span className="text-gray-600 ml-2">
                        {Math.round((session.correctCount / session.questionsAnswered) * 100)}%
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}

          {/* Empty state */}
          {sessions.length === 0 && (
            <div className="px-3 py-8 text-center">
              <p className="text-sm text-gray-600">No study sessions yet</p>
              <p className="text-xs text-gray-700 mt-1">Start studying to see your history</p>
            </div>
          )}

          {/* Quick Links */}
          <div className="border-t border-gray-900 mt-4 pt-4">
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
              <button
                onClick={() => window.location.href = 'mailto:devaun0506@gmail.com?subject=ShelfSense Feedback'}
                className="p-1.5 text-gray-600 hover:text-gray-300 transition-colors"
                title="Send feedback"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
              </button>
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
