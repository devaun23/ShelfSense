'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { useUser } from '@/contexts/UserContext';

interface ReviewStats {
  total_due_today: number;
  total_upcoming: number;
  by_stage: {
    New: number;
    Learning: number;
    Review: number;
    Mastered: number;
  };
  by_interval: Record<string, number>;
}

interface DayReviews {
  date: string;
  count: number;
  questions: Array<{
    id: string;
    scheduled_for: string;
    learning_stage: string;
    review_interval: string;
  }>;
}

export default function ReviewsPage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [upcoming, setUpcoming] = useState<DayReviews[]>([]);
  const [loading, setLoading] = useState(true);
  const [daysToShow, setDaysToShow] = useState(7);

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      loadReviewData();
    }
  }, [user, userLoading, router, daysToShow]);

  const loadReviewData = async () => {
    if (!user) return;

    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Load stats
      const statsResponse = await fetch(`${apiUrl}/api/reviews/stats?user_id=${user.userId}`);
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }

      // Load upcoming reviews
      const upcomingResponse = await fetch(`${apiUrl}/api/reviews/upcoming?user_id=${user.userId}&days=${daysToShow}`);
      if (upcomingResponse.ok) {
        const upcomingData = await upcomingResponse.json();
        setUpcoming(upcomingData.days || []);
      }
    } catch (error) {
      console.error('Error loading review data:', error);
    } finally {
      setLoading(false);
    }
  };

  const startReviews = () => {
    router.push('/study?mode=review');
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === tomorrow.toDateString()) {
      return 'Tomorrow';
    } else {
      return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    }
  };

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'New': return 'text-blue-400 bg-blue-400/10';
      case 'Learning': return 'text-yellow-400 bg-yellow-400/10';
      case 'Review': return 'text-green-400 bg-green-400/10';
      case 'Mastered': return 'text-purple-400 bg-purple-400/10';
      default: return 'text-gray-400 bg-gray-400/10';
    }
  };

  if (loading) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="flex items-center justify-center min-h-screen">
            <p className="text-gray-400">Loading reviews...</p>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        <div className="max-w-6xl mx-auto px-8 py-8 pt-20">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'var(--font-cormorant)' }}>
              Review Calendar
            </h1>
            <p className="text-gray-400">
              Spaced repetition keeps questions fresh in your memory
            </p>
          </div>

          {/* Stats Overview */}
          {stats && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              {/* Due Today */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                <div className="text-3xl font-bold text-emerald-400 mb-2">
                  {stats.total_due_today}
                </div>
                <div className="text-sm text-gray-400">Due Today</div>
              </div>

              {/* Upcoming */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                <div className="text-3xl font-bold text-blue-400 mb-2">
                  {stats.total_upcoming}
                </div>
                <div className="text-sm text-gray-400">Upcoming</div>
              </div>

              {/* Learning */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                <div className="text-3xl font-bold text-yellow-400 mb-2">
                  {stats.by_stage.Learning + stats.by_stage.New}
                </div>
                <div className="text-sm text-gray-400">Learning</div>
              </div>

              {/* Mastered */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                <div className="text-3xl font-bold text-purple-400 mb-2">
                  {stats.by_stage.Mastered}
                </div>
                <div className="text-sm text-gray-400">Mastered</div>
              </div>
            </div>
          )}

          {/* Start Reviews Button */}
          {stats && stats.total_due_today > 0 && (
            <div className="mb-8">
              <button
                onClick={startReviews}
                className="px-8 py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors duration-200 text-lg font-semibold"
              >
                Start Today's Reviews ({stats.total_due_today})
              </button>
            </div>
          )}

          {/* Upcoming Calendar */}
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-2xl font-bold" style={{ fontFamily: 'var(--font-cormorant)' }}>
              Upcoming Reviews
            </h2>
            <div className="flex gap-2">
              <button
                onClick={() => setDaysToShow(7)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  daysToShow === 7 ? 'bg-[#1E3A5F] text-white' : 'bg-gray-900 text-gray-400 hover:text-white'
                }`}
              >
                7 days
              </button>
              <button
                onClick={() => setDaysToShow(14)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  daysToShow === 14 ? 'bg-[#1E3A5F] text-white' : 'bg-gray-900 text-gray-400 hover:text-white'
                }`}
              >
                14 days
              </button>
              <button
                onClick={() => setDaysToShow(30)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  daysToShow === 30 ? 'bg-[#1E3A5F] text-white' : 'bg-gray-900 text-gray-400 hover:text-white'
                }`}
              >
                30 days
              </button>
            </div>
          </div>

          {/* Calendar View */}
          <div className="space-y-3">
            {upcoming.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                <p className="text-xl mb-2">No reviews scheduled yet</p>
                <p className="text-sm">Start answering questions to build your review schedule!</p>
              </div>
            )}
            {upcoming.map((day) => (
              <div
                key={day.date}
                className="bg-gray-900 border border-gray-800 rounded-lg p-6 hover:border-gray-700 transition-colors"
              >
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <div className="text-lg font-semibold">{formatDate(day.date)}</div>
                    <div className="text-sm text-gray-400">
                      {new Date(day.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                    </div>
                  </div>
                  <div className="text-3xl font-bold text-blue-400">
                    {day.count}
                  </div>
                </div>

                {/* Stage breakdown */}
                <div className="flex flex-wrap gap-2">
                  {Object.entries(
                    day.questions.reduce((acc, q) => {
                      acc[q.learning_stage] = (acc[q.learning_stage] || 0) + 1;
                      return acc;
                    }, {} as Record<string, number>)
                  ).map(([stage, count]) => (
                    <span
                      key={stage}
                      className={`px-3 py-1 rounded-full text-xs font-semibold ${getStageColor(stage)}`}
                    >
                      {stage}: {count}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Learning Stages Legend */}
          <div className="mt-8 p-6 bg-gray-900 border border-gray-800 rounded-lg">
            <h3 className="text-lg font-semibold mb-4">Learning Stages</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getStageColor('New')} mb-2`}>
                  New
                </span>
                <p className="text-sm text-gray-400">First time seeing this question</p>
              </div>
              <div>
                <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getStageColor('Learning')} mb-2`}>
                  Learning
                </span>
                <p className="text-sm text-gray-400">Building memory (1-3 day intervals)</p>
              </div>
              <div>
                <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getStageColor('Review')} mb-2`}>
                  Review
                </span>
                <p className="text-sm text-gray-400">Reinforcing knowledge (7-14 day intervals)</p>
              </div>
              <div>
                <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getStageColor('Mastered')} mb-2`}>
                  Mastered
                </span>
                <p className="text-sm text-gray-400">Long-term retention (30+ day intervals)</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
