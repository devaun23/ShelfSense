'use client';

import { useState, useEffect, Suspense, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useUser } from '@/contexts/UserContext';
import { SPECIALTIES } from '@/lib/specialties';
import { Button, Badge, CollapsibleSection } from '@/components/ui';

// Dynamically import Sidebar to avoid useSearchParams SSR issues
const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });
const PeerComparison = dynamic(() => import('@/components/PeerComparison'), { ssr: false });
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface SpecialtyStats {
  total: number;
  correct: number;
  accuracy: number;
  predicted_score: number | null;
}

interface SpecialtyBreakdown {
  specialties: Record<string, SpecialtyStats>;
  total_answered: number;
  overall_accuracy: number;
}

interface DashboardData {
  summary: {
    total_questions: number;
    correct_count: number;
    overall_accuracy: number;
    weighted_accuracy: number;
    predicted_score: number | null;
    confidence_interval: number | null;
    streak: number;
  };
  score_details: {
    current_score: number | null;
    weighted_accuracy: number;
    confidence_interval: number | null;
    score_trajectory: string;
    breakdown: Record<string, { score: number; accuracy: number; weight_contribution: number }>;
    total_questions: number;
  };
  weak_areas: Array<{
    source: string;
    total_questions: number;
    correct: number;
    accuracy: number;
    avg_time_seconds: number;
    priority_score: number;
  }>;
  strong_areas: Array<{
    source: string;
    total_questions: number;
    correct: number;
    accuracy: number;
  }>;
  focus_recommendation: string[];
  trends: {
    daily_data: Array<{
      date: string;
      questions_answered: number;
      correct: number;
      accuracy: number;
      predicted_score: number | null;
    }>;
    weekly_summary: { weeks: Array<{ week_start: string; questions_answered: number; accuracy: number }> };
    overall_trend: string;
  };
  behavioral_insights: {
    time_analysis: {
      avg_time_correct: number;
      avg_time_incorrect: number;
      avg_time_overall: number;
      time_distribution: Record<string, number>;
    };
    confidence_analysis: {
      correlation: string;
      by_level: Record<string, { accuracy: number; count: number }>;
    };
    optimal_conditions: {
      best_hours: Array<{ hour: number; accuracy: number; sample_size: number }>;
    };
  };
  error_distribution: {
    error_counts: Record<string, number>;
    most_common: string | null;
    total_errors: number;
    improvement_over_time: Record<string, string>;
  };
}

const ERROR_TYPE_LABELS: Record<string, string> = {
  knowledge_gap: 'Knowledge Gap',
  premature_closure: 'Premature Closure',
  misread_stem: 'Misread Vignette',
  faulty_reasoning: 'Faulty Reasoning',
  test_taking_error: 'Test-Taking Error',
  time_pressure: 'Time Pressure'
};

type TabType = 'performance' | 'specialties' | 'insights' | 'peers';

export default function AnalyticsPage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  // Start with sidebar closed on mobile
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768;
    }
    return true;
  });
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [specialtyData, setSpecialtyData] = useState<SpecialtyBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tab and collapsible state
  const [activeTab, setActiveTab] = useState<TabType>('performance');
  const [showTrendChart, setShowTrendChart] = useState(true);
  const [showActivityChart, setShowActivityChart] = useState(true);
  const [showWeakAreas, setShowWeakAreas] = useState(true);
  const [showStrongAreas, setShowStrongAreas] = useState(false);

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      fetchDashboardData();
    }
  }, [user, userLoading, router]);

  const fetchDashboardData = async () => {
    if (!user) return;

    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const [dashboardRes, specialtyRes] = await Promise.all([
        fetch(`${apiUrl}/api/analytics/dashboard?user_id=${user.userId}`),
        fetch(`${apiUrl}/api/analytics/specialty-breakdown?user_id=${user.userId}`)
      ]);

      if (dashboardRes.ok) {
        const data = await dashboardRes.json();
        setDashboardData(data);
        setError(null);
      } else {
        setError('Failed to load analytics data');
      }

      if (specialtyRes.ok) {
        const specData = await specialtyRes.json();
        setSpecialtyData(specData);
      }
    } catch (err) {
      console.error('Error fetching analytics:', err);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getTrendIcon = (trend: string) => {
    if (trend === 'improving') return '↑';
    if (trend === 'declining') return '↓';
    return '→';
  };

  const getTrendColor = (trend: string) => {
    if (trend === 'improving') return 'text-emerald-400';
    if (trend === 'declining') return 'text-red-400';
    return 'text-gray-400';
  };

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 75) return 'text-emerald-400';
    if (accuracy >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const formatHour = (hour: number) => {
    if (hour === 0) return '12 AM';
    if (hour === 12) return '12 PM';
    return hour > 12 ? `${hour - 12} PM` : `${hour} AM`;
  };

  if (loading) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${sidebarOpen ? 'md:ml-64' : 'ml-0'}`}>
          <div className="flex items-center justify-center min-h-screen">
            <div className="animate-pulse text-gray-500">Loading analytics...</div>
          </div>
        </main>
      </>
    );
  }

  if (!dashboardData) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${sidebarOpen ? 'md:ml-64' : 'ml-0'}`}>
          <div className="flex flex-col items-center justify-center min-h-screen gap-4">
            <p className="text-gray-400">{error || 'No analytics data available'}</p>
            <Button variant="primary" rounded="full" onClick={fetchDashboardData}>
              Retry
            </Button>
          </div>
        </main>
      </>
    );
  }

  const { summary, score_details, weak_areas, strong_areas, trends, behavioral_insights, error_distribution } = dashboardData;

  // Prepare chart data (memoized to prevent recomputation on every render)
  const trendChartData = useMemo(() =>
    trends.daily_data.map(d => ({
      ...d,
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    })),
    [trends.daily_data]
  );

  // Error distribution as array for horizontal bars (memoized)
  const errorBarData = useMemo(() =>
    Object.entries(error_distribution.error_counts)
      .map(([type, count]) => ({
        type,
        label: ERROR_TYPE_LABELS[type] || type,
        count
      }))
      .sort((a, b) => b.count - a.count),
    [error_distribution.error_counts]
  );

  const totalErrors = useMemo(() =>
    errorBarData.reduce((sum, e) => sum + e.count, 0),
    [errorBarData]
  );

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${sidebarOpen ? 'md:ml-64' : 'ml-0'}`}>
        <div className="max-w-4xl mx-auto px-4 md:px-6 py-6 md:py-8 pt-14 md:pt-16">

          {/* Hero Section - Predicted Score */}
          <div className="text-center mb-8 md:mb-10">
            <p className="text-gray-500 text-xs md:text-sm mb-2 uppercase tracking-wider">
              Predicted Step 2 CK Score
            </p>
            <div className="flex items-baseline justify-center gap-2 md:gap-3 mb-3">
              <span
                className="text-5xl md:text-7xl font-semibold text-white"
                style={{ fontFamily: 'var(--font-serif)' }}
              >
                {summary.predicted_score || '---'}
              </span>
              {summary.confidence_interval && (
                <span className="text-xl md:text-2xl text-gray-600">±{summary.confidence_interval}</span>
              )}
            </div>
            <div className={`flex items-center justify-center gap-2 text-sm ${getTrendColor(score_details.score_trajectory)}`}>
              <span className="text-lg">{getTrendIcon(score_details.score_trajectory)}</span>
              <span className="capitalize">{score_details.score_trajectory.replace('_', ' ')}</span>
            </div>
          </div>

          {/* Stats Row */}
          <div className="flex flex-wrap justify-center gap-6 md:gap-10 border-t border-gray-900 pt-6 md:pt-8 mb-8 md:mb-10">
            <div className="text-center">
              <p className="text-2xl font-semibold text-white" style={{ fontFamily: 'var(--font-serif)' }}>
                {summary.total_questions}
              </p>
              <p className="text-xs text-gray-600 uppercase tracking-wider">Questions</p>
            </div>
            <div className="text-center">
              <p className={`text-2xl font-semibold ${getAccuracyColor(summary.overall_accuracy)}`} style={{ fontFamily: 'var(--font-serif)' }}>
                {summary.overall_accuracy}%
              </p>
              <p className="text-xs text-gray-600 uppercase tracking-wider">Accuracy</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-semibold text-[#4169E1]" style={{ fontFamily: 'var(--font-serif)' }}>
                {summary.streak}
              </p>
              <p className="text-xs text-gray-600 uppercase tracking-wider">Day Streak</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-semibold text-gray-400" style={{ fontFamily: 'var(--font-serif)' }}>
                {summary.weighted_accuracy}%
              </p>
              <p className="text-xs text-gray-600 uppercase tracking-wider">Weighted</p>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex justify-center gap-2 mb-8">
            {(['performance', 'specialties', 'insights', 'peers'] as TabType[]).map((tab) => (
              <Button
                key={tab}
                variant={activeTab === tab ? 'primary' : 'ghost'}
                rounded="full"
                onClick={() => setActiveTab(tab)}
                className="capitalize"
              >
                {tab}
              </Button>
            ))}
          </div>

          {/* Performance Tab */}
          {activeTab === 'performance' && (
            <div>
              {/* Accuracy Trend Chart */}
              <CollapsibleSection
                title="Performance Trend"
                isOpen={showTrendChart}
                onToggle={() => setShowTrendChart(!showTrendChart)}
              >
                {trendChartData.length > 0 ? (
                  <div className="pt-4">
                    <ResponsiveContainer width="100%" height={280}>
                      <LineChart data={trendChartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                        <XAxis dataKey="date" stroke="#6B7280" fontSize={12} />
                        <YAxis stroke="#6B7280" fontSize={12} domain={[0, 100]} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#111', border: '1px solid #374151', borderRadius: '12px' }}
                          labelStyle={{ color: '#9CA3AF' }}
                        />
                        <Line
                          type="monotone"
                          dataKey="accuracy"
                          stroke="#4169E1"
                          strokeWidth={2}
                          dot={{ fill: '#4169E1', strokeWidth: 0, r: 4 }}
                          name="Accuracy %"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="py-12 text-center text-gray-500">
                    Not enough data to show trends
                  </div>
                )}
              </CollapsibleSection>

              {/* Daily Activity Chart */}
              <CollapsibleSection
                title="Daily Activity"
                isOpen={showActivityChart}
                onToggle={() => setShowActivityChart(!showActivityChart)}
              >
                {trendChartData.length > 0 ? (
                  <div className="pt-4">
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={trendChartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                        <XAxis dataKey="date" stroke="#6B7280" fontSize={12} />
                        <YAxis stroke="#6B7280" fontSize={12} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#111', border: '1px solid #374151', borderRadius: '12px' }}
                          labelStyle={{ color: '#9CA3AF' }}
                        />
                        <Bar dataKey="questions_answered" fill="#4169E1" name="Questions" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="py-12 text-center text-gray-500">
                    Start answering questions to see activity
                  </div>
                )}
              </CollapsibleSection>

              {/* Weak Areas */}
              <CollapsibleSection
                title="Areas to Improve"
                isOpen={showWeakAreas}
                onToggle={() => setShowWeakAreas(!showWeakAreas)}
                badge={weak_areas.length > 0 ? (
                  <Badge variant="danger">{weak_areas.length} topics</Badge>
                ) : undefined}
              >
                {weak_areas.length > 0 ? (
                  <div className="pt-4 space-y-3">
                    {weak_areas.slice(0, 5).map((area, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-900/50 rounded-xl">
                        <div>
                          <p className="text-white text-sm">{area.source}</p>
                          <p className="text-gray-600 text-xs">{area.total_questions} questions</p>
                        </div>
                        <p className={`font-medium ${getAccuracyColor(area.accuracy)}`}>
                          {area.accuracy}%
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="py-8 text-center text-gray-500">No weak areas identified yet</p>
                )}
              </CollapsibleSection>

              {/* Strong Areas */}
              <CollapsibleSection
                title="Strengths"
                isOpen={showStrongAreas}
                onToggle={() => setShowStrongAreas(!showStrongAreas)}
                badge={strong_areas.length > 0 ? (
                  <Badge variant="success">{strong_areas.length} topics</Badge>
                ) : undefined}
              >
                {strong_areas.length > 0 ? (
                  <div className="pt-4 space-y-3">
                    {strong_areas.slice(0, 5).map((area, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-900/50 rounded-xl">
                        <div>
                          <p className="text-white text-sm">{area.source}</p>
                          <p className="text-gray-600 text-xs">{area.total_questions} questions</p>
                        </div>
                        <p className="font-medium text-emerald-400">
                          {area.accuracy}%
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="py-8 text-center text-gray-500">Keep studying to build mastery</p>
                )}
              </CollapsibleSection>
            </div>
          )}

          {/* Specialties Tab */}
          {activeTab === 'specialties' && specialtyData && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
              {SPECIALTIES.map((specialty) => {
                const stats = specialtyData.specialties[specialty.apiName];

                return (
                  <button
                    key={specialty.id}
                    onClick={() => router.push(`/study?specialty=${encodeURIComponent(specialty.apiName)}`)}
                    className={`p-5 rounded-2xl border ${specialty.borderColor} ${specialty.bgColor} text-left transition-all hover:scale-[1.02]`}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-2xl">{specialty.icon}</span>
                      <span className={`text-base font-medium ${specialty.color}`}>
                        {specialty.shortName}
                      </span>
                    </div>

                    {stats && stats.total > 0 ? (
                      <>
                        <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden mb-2">
                          <div
                            className={`h-full rounded-full ${
                              stats.accuracy >= 70 ? 'bg-emerald-500' : stats.accuracy >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${stats.accuracy}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-500">{stats.total} questions</span>
                          <span className={getAccuracyColor(stats.accuracy)}>{stats.accuracy}%</span>
                        </div>
                      </>
                    ) : (
                      <p className="text-xs text-gray-600">Not started</p>
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* Insights Tab */}
          {activeTab === 'insights' && (
            <div>
              {/* Behavioral Insights */}
              <div className="bg-gray-900/50 border border-gray-800 rounded-2xl p-6 mb-4">
                <h3 className="text-lg font-medium text-white mb-6" style={{ fontFamily: 'var(--font-serif)' }}>
                  Study Patterns
                </h3>

                <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4 mb-6">
                  <div className="text-center p-4 bg-gray-800/50 rounded-xl">
                    <p className="text-2xl font-semibold text-white">
                      {Math.round(behavioral_insights.time_analysis.avg_time_overall || 0)}s
                    </p>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">Avg Time</p>
                  </div>
                  <div className="text-center p-4 bg-gray-800/50 rounded-xl">
                    <p className="text-2xl font-semibold text-emerald-400">
                      {Math.round(behavioral_insights.time_analysis.avg_time_correct || 0)}s
                    </p>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">When Correct</p>
                  </div>
                  <div className="text-center p-4 bg-gray-800/50 rounded-xl">
                    <p className="text-2xl font-semibold text-red-400">
                      {Math.round(behavioral_insights.time_analysis.avg_time_incorrect || 0)}s
                    </p>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">When Wrong</p>
                  </div>
                  <div className="text-center p-4 bg-gray-800/50 rounded-xl">
                    <p className="text-2xl font-semibold text-[#4169E1]">
                      {behavioral_insights.optimal_conditions.best_hours?.[0]
                        ? formatHour(behavioral_insights.optimal_conditions.best_hours[0].hour)
                        : '---'}
                    </p>
                    <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">Best Time</p>
                  </div>
                </div>

                {/* Confidence Calibration */}
                {behavioral_insights.confidence_analysis.correlation && (
                  <div className="p-4 bg-[#4169E1]/10 border border-[#4169E1]/30 rounded-xl">
                    <p className="text-sm text-gray-300">
                      <span className="text-[#4169E1] font-medium">Confidence Calibration: </span>
                      {behavioral_insights.confidence_analysis.correlation === 'well_calibrated'
                        ? 'Your confidence matches your accuracy well'
                        : behavioral_insights.confidence_analysis.correlation === 'overconfident'
                        ? 'You may be overconfident - high confidence doesnt always mean correct'
                        : 'Work on calibrating your confidence with your actual performance'}
                    </p>
                  </div>
                )}
              </div>

              {/* Error Distribution - Horizontal Bars */}
              <div className="bg-gray-900/50 border border-gray-800 rounded-2xl p-6">
                <h3 className="text-lg font-medium text-white mb-6" style={{ fontFamily: 'var(--font-serif)' }}>
                  Error Patterns
                </h3>

                {errorBarData.length > 0 ? (
                  <div className="space-y-4">
                    {errorBarData.map((error) => (
                      <div key={error.type} className="flex items-center gap-4">
                        <span className="text-sm text-gray-400 w-36 truncate">{error.label}</span>
                        <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#4169E1] rounded-full transition-all"
                            style={{ width: `${totalErrors > 0 ? (error.count / totalErrors) * 100 : 0}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-500 w-8 text-right">{error.count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="py-8 text-center text-gray-500">No error analysis data yet</p>
                )}
              </div>
            </div>
          )}

          {/* Peers Tab */}
          {activeTab === 'peers' && user && (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-medium text-white mb-2" style={{ fontFamily: 'var(--font-serif)' }}>
                  Peer Comparison
                </h3>
                <p className="text-sm text-gray-500">
                  See how you compare to other ShelfSense users (anonymized data)
                </p>
              </div>
              <PeerComparison userId={user.userId} />
            </div>
          )}

          {/* Action Footer */}
          <div className="text-center pt-10 pb-8">
            <Button variant="primary" size="lg" rounded="full" onClick={() => router.push('/study')}>
              Continue Studying
            </Button>
          </div>
        </div>
      </main>
    </>
  );
}
