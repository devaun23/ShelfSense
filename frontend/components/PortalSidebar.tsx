'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { useExam } from '@/contexts/ExamContext';
import { Specialty } from '@/lib/specialties';
import { UserButton } from '@clerk/nextjs';

interface PortalSidebarProps {
  specialty: Specialty;
}

export default function PortalSidebar({ specialty }: PortalSidebarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [reviewsDue, setReviewsDue] = useState(0);
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useUser();
  const { exitPortal } = useExam();

  const basePath = `/portal/${specialty.slug}`;

  // Fetch reviews due count
  useEffect(() => {
    if (user?.userId) {
      fetchReviewsDue();
    }
  }, [user?.userId, specialty.apiName]);

  const fetchReviewsDue = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      let url = `${apiUrl}/api/reviews/stats?user_id=${user?.userId}`;
      if (specialty.apiName) {
        url += `&specialty=${encodeURIComponent(specialty.apiName)}`;
      }
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setReviewsDue(data.due_today || 0);
      }
    } catch (error) {
      console.error('Error fetching reviews:', error);
    }
  };

  const handleExitPortal = () => {
    exitPortal();
    router.push('/');
  };

  const navItems = [
    { href: basePath, label: 'Dashboard', icon: '📊' },
    { href: `${basePath}/study`, label: 'Study Questions', icon: '📝' },
    { href: `${basePath}/analytics`, label: 'Analytics', icon: '📈' },
    { href: `${basePath}/reviews`, label: 'Reviews', icon: '🔄', badge: reviewsDue > 0 ? reviewsDue : undefined },
    { href: `${basePath}/weak-areas`, label: 'Weak Areas', icon: '🎯' },
  ];

  const isActive = (href: string) => {
    if (href === basePath) {
      return pathname === basePath;
    }
    return pathname.startsWith(href);
  };

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-gray-900 rounded-lg border border-gray-800"
        aria-label="Toggle menu"
      >
        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {isOpen ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          )}
        </svg>
      </button>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-40
          w-64 bg-gray-950 border-r border-gray-800
          transform transition-transform duration-200 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          flex flex-col
        `}
      >
        {/* Back button */}
        <div className="p-4 border-b border-gray-800">
          <button
            onClick={handleExitPortal}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors w-full"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            <span className="text-sm">Back to Exams</span>
          </button>
        </div>

        {/* Specialty header */}
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{specialty.icon}</span>
            <div>
              <h2 className="text-white font-semibold">{specialty.name}</h2>
              {specialty.description && (
                <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{specialty.description}</p>
              )}
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setIsOpen(false)}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors
                ${isActive(item.href)
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }
              `}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="flex-1">{item.label}</span>
              {item.badge && (
                <span className="bg-emerald-500 text-white text-xs font-medium px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          ))}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center gap-3">
            <UserButton
              afterSignOutUrl="/sign-in"
              appearance={{
                elements: {
                  avatarBox: 'w-8 h-8',
                },
              }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white truncate">{user?.firstName || 'User'}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
