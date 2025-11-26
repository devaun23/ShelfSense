'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useUser } from '@/contexts/UserContext';

// Dynamically import Sidebar to avoid useSearchParams SSR issues
const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });

export default function Home() {
  // Start with sidebar closed on mobile
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768;
    }
    return true;
  });
  const [predictedScore, setPredictedScore] = useState<number | null>(null);
  const [scoreConfidence, setScoreConfidence] = useState<number | null>(null);
  const [streak, setStreak] = useState(0);
  const [totalAttempts, setTotalAttempts] = useState(0);
  const [dueToday, setDueToday] = useState(0);
  const router = useRouter();
  const { user, isLoading } = useUser();

  useEffect(() => {
    // Middleware handles auth redirect - just load stats when user is available
    if (user) {
      loadUserStats();
    }
  }, [user]);

  const loadUserStats = async () => {
    if (!user) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Load analytics stats
      const statsResponse = await fetch(`${apiUrl}/api/analytics/stats?user_id=${user.userId}`);
      if (statsResponse.ok) {
        const data = await statsResponse.json();
        setStreak(data.streak || 0);
        setPredictedScore(data.predicted_score || null);
        setScoreConfidence(data.score_confidence || null);
        setTotalAttempts(data.total_questions_answered || 0);
      }

      // Load review stats
      const reviewsResponse = await fetch(`${apiUrl}/api/reviews/stats?user_id=${user.userId}`);
      if (reviewsResponse.ok) {
        const reviewData = await reviewsResponse.json();
        setDueToday(reviewData.total_due_today || 0);
      }
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  // Get time-based greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  if (isLoading) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="animate-pulse">
          <h1 className="text-4xl font-light" style={{ fontFamily: 'var(--font-serif)' }}>
            ShelfSense
          </h1>
        </div>
      </main>
    );
  }

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        {/* Centered content area */}
        <div className="flex flex-col items-center justify-center min-h-screen px-4 md:px-6 py-8 md:py-12">
          <div className="max-w-2xl w-full">
            {/* Greeting */}
            {user && (
              <h1 className="text-4xl md:text-5xl text-center text-white mb-4" style={{ fontFamily: 'var(--font-serif)' }}>
                {getGreeting()}, {user.firstName}
              </h1>
            )}

            {/* Subtitle in bubble */}
            <div className="flex justify-center mb-12">
              <div className="inline-flex items-center px-4 py-2.5 bg-gray-900/50 border border-gray-800 rounded-full">
                <span className="text-gray-400 text-sm">Select an exam from the sidebar to start studying</span>
              </div>
            </div>

            {/* Quick Action Buttons */}
            <div className="flex flex-wrap justify-center gap-2 mb-12">
              {/* Reviews Calendar */}
              <button
                onClick={() => router.push('/reviews')}
                className="flex items-center gap-2 px-4 py-2.5 bg-gray-950 border border-gray-800 rounded-full text-sm text-gray-400 hover:text-white hover:border-gray-700 hover:bg-gray-900 transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                </svg>
                <span>Reviews</span>
                {dueToday > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">
                    {dueToday}
                  </span>
                )}
              </button>

              {/* Analytics */}
              <button
                onClick={() => router.push('/analytics')}
                className="flex items-center gap-2 px-4 py-2.5 bg-gray-950 border border-gray-800 rounded-full text-sm text-gray-400 hover:text-white hover:border-gray-700 hover:bg-gray-900 transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span>Analytics</span>
              </button>

              {/* Weak Areas */}
              <button
                onClick={() => router.push('/study?mode=weak')}
                className="flex items-center gap-2 px-4 py-2.5 bg-gray-950 border border-gray-800 rounded-full text-sm text-gray-400 hover:text-white hover:border-gray-700 hover:bg-gray-900 transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>Weak Areas</span>
              </button>
            </div>

            {/* Stats section - minimal, centered */}
            {(predictedScore || totalAttempts > 0 || streak > 0) && (
              <div className="border-t border-gray-900 pt-8">
                <div className="flex flex-wrap justify-center gap-8 md:gap-12 text-center">
                  {/* Predicted Score */}
                  {predictedScore && (
                    <div>
                      <div className="text-3xl font-semibold text-white mb-1" style={{ fontFamily: 'var(--font-serif)' }}>
                        {predictedScore}
                        {scoreConfidence && (
                          <span className="text-lg text-gray-600 ml-1">±{scoreConfidence}</span>
                        )}
                      </div>
                      <div className="text-xs text-gray-600 uppercase tracking-wider">
                        Predicted Score
                      </div>
                    </div>
                  )}

                  {/* Streak */}
                  {streak > 0 && (
                    <div>
                      <div className="text-3xl font-semibold text-[#4169E1] mb-1" style={{ fontFamily: 'var(--font-serif)' }}>
                        {streak}
                      </div>
                      <div className="text-xs text-gray-600 uppercase tracking-wider">
                        Day Streak
                      </div>
                    </div>
                  )}

                  {/* Questions Completed */}
                  {totalAttempts > 0 && (
                    <div>
                      <div className="text-3xl font-semibold text-white mb-1" style={{ fontFamily: 'var(--font-serif)' }}>
                        {totalAttempts}
                      </div>
                      <div className="text-xs text-gray-600 uppercase tracking-wider">
                        Questions Done
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
