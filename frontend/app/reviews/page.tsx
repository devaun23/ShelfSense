'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useUser } from '@/contexts/UserContext';
import CalendarHeatmap from '@/components/CalendarHeatmap';
import { Button, Badge } from '@/components/ui';

// Dynamically import Sidebar to avoid useSearchParams SSR issues
const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });

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

interface HeatmapData {
  date: string;
  count: number;
  accuracy?: number;
}

interface HeatmapResponse {
  data: HeatmapData[];
  summary: {
    total_days_active: number;
    total_questions: number;
    avg_per_active_day: number;
    longest_streak: number;
    current_streak: number;
    date_range: {
      start: string;
      end: string;
    };
  };
}

export default function ReviewsPage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  // Start with sidebar closed on narrow viewports
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 900;
    }
    return true;
  });
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [upcoming, setUpcoming] = useState<DayReviews[]>([]);
  const [heatmapData, setHeatmapData] = useState<HeatmapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [daysToShow, setDaysToShow] = useState(7);
  const [activeTab, setActiveTab] = useState<'upcoming' | 'activity'>('upcoming');

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

      // Load all data in parallel
      const [statsResponse, upcomingResponse, heatmapResponse] = await Promise.all([
        fetch(`${apiUrl}/api/reviews/stats?user_id=${user.userId}`),
        fetch(`${apiUrl}/api/reviews/upcoming?user_id=${user.userId}&days=${daysToShow}`),
        fetch(`${apiUrl}/api/analytics/activity-heatmap?user_id=${user.userId}&days=365`)
      ]);

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }

      if (upcomingResponse.ok) {
        const upcomingData = await upcomingResponse.json();
        setUpcoming(upcomingData.days || []);
      }

      if (heatmapResponse.ok) {
        const heatmapDataRes = await heatmapResponse.json();
        setHeatmapData(heatmapDataRes);
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

  const getStageVariant = (stage: string): 'info' | 'warning' | 'success' | 'purple' | 'default' => {
    switch (stage) {
      case 'New': return 'info';
      case 'Learning': return 'warning';
      case 'Review': return 'success';
      case 'Mastered': return 'purple';
      default: return 'default';
    }
  };

  // Stable heatmap click handler (prevents CalendarHeatmap re-renders)
  const handleHeatmapClick = useCallback((date: string, data: { count: number; accuracy?: number } | null) => {
    if (data && data.count > 0) {
      console.log(`Clicked ${date}: ${data.count} questions, ${data.accuracy}% accuracy`);
    }
  }, []);

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
        <div className="max-w-6xl mx-auto px-4 md:px-8 py-6 md:py-8 pt-14 md:pt-20">
          {/* Header */}
          <div className="mb-6 md:mb-8">
            <h1 className="text-3xl md:text-4xl font-bold mb-2" style={{ fontFamily: 'var(--font-serif)' }}>
              Review Calendar
            </h1>
            <p className="text-gray-400 text-sm md:text-base">
              Spaced repetition keeps questions fresh in your memory
            </p>
          </div>

          {/* Stats Overview */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-6 md:mb-8">
              {/* Due Today */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 md:p-6">
                <div className="text-2xl md:text-3xl font-bold text-emerald-400 mb-1 md:mb-2">
                  {stats.total_due_today}
                </div>
                <div className="text-xs md:text-sm text-gray-400">Due Today</div>
              </div>

              {/* Upcoming */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 md:p-6">
                <div className="text-2xl md:text-3xl font-bold text-blue-400 mb-1 md:mb-2">
                  {stats.total_upcoming}
                </div>
                <div className="text-xs md:text-sm text-gray-400">Upcoming</div>
              </div>

              {/* Learning */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 md:p-6">
                <div className="text-2xl md:text-3xl font-bold text-yellow-400 mb-1 md:mb-2">
                  {stats.by_stage.Learning + stats.by_stage.New}
                </div>
                <div className="text-xs md:text-sm text-gray-400">Learning</div>
              </div>

              {/* Mastered */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 md:p-6">
                <div className="text-2xl md:text-3xl font-bold text-purple-400 mb-1 md:mb-2">
                  {stats.by_stage.Mastered}
                </div>
                <div className="text-xs md:text-sm text-gray-400">Mastered</div>
              </div>
            </div>
          )}

          {/* Start Reviews Button */}
          {stats && stats.total_due_today > 0 && (
            <div className="mb-6 md:mb-8">
              <Button
                variant="primary"
                size="lg"
                onClick={startReviews}
                className="w-full md:w-auto bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-600"
              >
                Start Today&apos;s Reviews ({stats.total_due_today})
              </Button>
            </div>
          )}

          {/* Tab Navigation */}
          <div className="flex gap-2 mb-6">
            <Button
              variant={activeTab === 'upcoming' ? 'primary' : 'ghost'}
              rounded="full"
              onClick={() => setActiveTab('upcoming')}
            >
              Upcoming Reviews
            </Button>
            <Button
              variant={activeTab === 'activity' ? 'primary' : 'ghost'}
              rounded="full"
              onClick={() => setActiveTab('activity')}
            >
              Activity Heatmap
            </Button>
          </div>

          {/* Activity Heatmap Tab */}
          {activeTab === 'activity' && (
            <div className="mb-8">
              {/* Heatmap Summary Stats */}
              {heatmapData?.summary && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-emerald-400">
                      {heatmapData.summary.current_streak}
                    </div>
                    <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Current Streak</div>
                  </div>
                  <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-purple-400">
                      {heatmapData.summary.longest_streak}
                    </div>
                    <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Longest Streak</div>
                  </div>
                  <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-blue-400">
                      {heatmapData.summary.total_days_active}
                    </div>
                    <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Days Active</div>
                  </div>
                  <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-white">
                      {heatmapData.summary.avg_per_active_day}
                    </div>
                    <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Avg/Day</div>
                  </div>
                </div>
              )}

              {/* Calendar Heatmap */}
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                <h3 className="text-lg font-semibold mb-4" style={{ fontFamily: 'var(--font-serif)' }}>
                  Study Activity (Past Year)
                </h3>
                {heatmapData?.data ? (
                  <CalendarHeatmap
                    data={heatmapData.data}
                    colorScheme="green"
                    onClick={handleHeatmapClick}
                  />
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <p>No activity data yet</p>
                    <p className="text-sm mt-2">Start answering questions to build your activity history!</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Upcoming Reviews Tab */}
          {activeTab === 'upcoming' && (
            <>
              {/* Days Filter */}
              <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <h2 className="text-lg md:text-xl font-bold" style={{ fontFamily: 'var(--font-serif)' }}>
                  Scheduled Reviews
                </h2>
                <div className="flex gap-2">
                  <button
                    onClick={() => setDaysToShow(7)}
                    className={`px-3 md:px-4 py-1.5 md:py-2 text-sm rounded-lg transition-colors ${
                      daysToShow === 7 ? 'bg-[#1E3A5F] text-white' : 'bg-gray-900 text-gray-400 hover:text-white'
                    }`}
                  >
                    7d
                  </button>
                  <button
                    onClick={() => setDaysToShow(14)}
                    className={`px-3 md:px-4 py-1.5 md:py-2 text-sm rounded-lg transition-colors ${
                      daysToShow === 14 ? 'bg-[#1E3A5F] text-white' : 'bg-gray-900 text-gray-400 hover:text-white'
                    }`}
                  >
                    14d
                  </button>
                  <button
                    onClick={() => setDaysToShow(30)}
                    className={`px-3 md:px-4 py-1.5 md:py-2 text-sm rounded-lg transition-colors ${
                      daysToShow === 30 ? 'bg-[#1E3A5F] text-white' : 'bg-gray-900 text-gray-400 hover:text-white'
                    }`}
                  >
                    30d
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
                    className="bg-gray-900 border border-gray-800 rounded-lg p-4 md:p-6 hover:border-gray-700 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-3 md:mb-4">
                      <div>
                        <div className="text-base md:text-lg font-semibold">{formatDate(day.date)}</div>
                        <div className="text-xs md:text-sm text-gray-400">
                          {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </div>
                      </div>
                      <div className="text-2xl md:text-3xl font-bold text-blue-400">
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
                        <Badge key={stage} variant={getStageVariant(stage)}>
                          {stage}: {count}
                        </Badge>
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
                    <Badge variant="info" className="mb-2">New</Badge>
                    <p className="text-sm text-gray-400">First time seeing this question</p>
                  </div>
                  <div>
                    <Badge variant="warning" className="mb-2">Learning</Badge>
                    <p className="text-sm text-gray-400">Building memory (1-3 day intervals)</p>
                  </div>
                  <div>
                    <Badge variant="success" className="mb-2">Review</Badge>
                    <p className="text-sm text-gray-400">Reinforcing knowledge (7-14 day intervals)</p>
                  </div>
                  <div>
                    <Badge variant="purple" className="mb-2">Mastered</Badge>
                    <p className="text-sm text-gray-400">Long-term retention (30+ day intervals)</p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </>
  );
}
