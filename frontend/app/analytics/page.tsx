'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { useUser } from '@/contexts/UserContext';
import { SPECIALTIES } from '@/lib/specialties';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
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

const COLORS = ['#4169E1', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

const ERROR_TYPE_LABELS: Record<string, string> = {
  knowledge_gap: 'Knowledge Gap',
  premature_closure: 'Premature Closure',
  misread_stem: 'Misread Vignette',
  faulty_reasoning: 'Faulty Reasoning',
  test_taking_error: 'Test-Taking Error',
  time_pressure: 'Time Pressure'
};

export default function AnalyticsPage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [specialtyData, setSpecialtyData] = useState<SpecialtyBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

      // Fetch both endpoints in parallel
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
          <div className="flex items-center justify-center min-h-screen">
            <div className="text-center">
              <p className="text-gray-400 mb-4">{error || 'No analytics data available'}</p>
              <button
                onClick={fetchDashboardData}
                className="px-4 py-2 bg-[#4169E1] text-white rounded-lg hover:bg-[#5B7FE8]"
              >
                Retry
              </button>
            </div>
          </div>
        </main>
      </>
    );
  }

  const { summary, score_details, weak_areas, strong_areas, trends, behavioral_insights, error_distribution } = dashboardData;

  // Prepare chart data
  const trendChartData = trends.daily_data.map(d => ({
    ...d,
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }));

  const errorPieData = Object.entries(error_distribution.error_counts).map(([type, count]) => ({
    name: ERROR_TYPE_LABELS[type] || type,
    value: count
  }));

  const specialtyBarData = Object.entries(score_details.breakdown || {}).map(([source, data]) => ({
    name: source.split(' - ')[0].slice(0, 15),
    accuracy: data.accuracy,
    score: data.score
  }));

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${sidebarOpen ? 'md:ml-64' : 'ml-0'}`}>
        <div className="max-w-7xl mx-auto px-6 py-8 pt-16">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-white" style={{ fontFamily: 'var(--font-cormorant)' }}>
              Analytics Dashboard
            </h1>
            <p className="text-gray-500 text-sm mt-1">Your performance insights and progress tracking</p>
          </div>

          {/* Score Card - Hero */}
          <div className="mb-8 p-6 bg-gray-900/50 border border-gray-800 rounded-2xl">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="text-center md:text-left">
                <p className="text-gray-500 text-sm mb-1">Predicted Step 2 CK Score</p>
                <div className="flex items-baseline gap-2">
                  <span className="text-5xl font-bold text-[#4169E1]">
                    {summary.predicted_score || '---'}
                  </span>
                  {summary.confidence_interval && (
                    <span className="text-gray-500 text-lg">±{summary.confidence_interval}</span>
                  )}
                </div>
                <div className={`flex items-center gap-2 mt-2 ${getTrendColor(score_details.score_trajectory)}`}>
                  <span className="text-xl">{getTrendIcon(score_details.score_trajectory)}</span>
                  <span className="text-sm capitalize">{score_details.score_trajectory.replace('_', ' ')}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
                <div>
                  <p className="text-2xl font-semibold text-white">{summary.total_questions}</p>
                  <p className="text-gray-500 text-xs">Questions</p>
                </div>
                <div>
                  <p className={`text-2xl font-semibold ${getAccuracyColor(summary.overall_accuracy)}`}>
                    {summary.overall_accuracy}%
                  </p>
                  <p className="text-gray-500 text-xs">Accuracy</p>
                </div>
                <div>
                  <p className="text-2xl font-semibold text-white">{summary.streak}</p>
                  <p className="text-gray-500 text-xs">Day Streak</p>
                </div>
                <div>
                  <p className="text-2xl font-semibold text-gray-400">
                    {summary.weighted_accuracy}%
                  </p>
                  <p className="text-gray-500 text-xs">Weighted</p>
                </div>
              </div>
            </div>
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Accuracy Trend Chart */}
            <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl">
              <h3 className="text-lg font-medium text-white mb-4">Performance Trend</h3>
              {trendChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={trendChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="date" stroke="#6B7280" fontSize={12} />
                    <YAxis stroke="#6B7280" fontSize={12} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                      labelStyle={{ color: '#9CA3AF' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="accuracy"
                      stroke="#4169E1"
                      strokeWidth={2}
                      dot={{ fill: '#4169E1', strokeWidth: 0, r: 3 }}
                      name="Accuracy %"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[250px] flex items-center justify-center text-gray-500">
                  Not enough data to show trends
                </div>
              )}
            </div>

            {/* Questions Per Day Chart */}
            <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl">
              <h3 className="text-lg font-medium text-white mb-4">Daily Activity</h3>
              {trendChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={trendChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="date" stroke="#6B7280" fontSize={12} />
                    <YAxis stroke="#6B7280" fontSize={12} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                      labelStyle={{ color: '#9CA3AF' }}
                    />
                    <Bar dataKey="questions_answered" fill="#4169E1" name="Questions" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[250px] flex items-center justify-center text-gray-500">
                  Start answering questions to see activity
                </div>
              )}
            </div>
          </div>

          {/* Specialty Performance & Error Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Specialty Bar Chart */}
            <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl">
              <h3 className="text-lg font-medium text-white mb-4">Performance by Specialty</h3>
              {specialtyBarData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={specialtyBarData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis type="number" stroke="#6B7280" fontSize={12} domain={[0, 100]} />
                    <YAxis type="category" dataKey="name" stroke="#6B7280" fontSize={11} width={100} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                      labelStyle={{ color: '#9CA3AF' }}
                    />
                    <Bar dataKey="accuracy" fill="#4169E1" name="Accuracy %" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-gray-500">
                  No specialty data yet
                </div>
              )}
            </div>

            {/* Error Distribution Pie Chart */}
            <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl">
              <h3 className="text-lg font-medium text-white mb-4">Error Analysis</h3>
              {errorPieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={errorPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {errorPieData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: '12px', color: '#9CA3AF' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-gray-500">
                  No error analysis data yet
                </div>
              )}
            </div>
          </div>

          {/* Weak & Strong Areas */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Weak Areas */}
            <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl">
              <h3 className="text-lg font-medium text-white mb-4">
                Areas to Improve
                <span className="text-gray-500 text-sm font-normal ml-2">(&lt;60% accuracy)</span>
              </h3>
              {weak_areas.length > 0 ? (
                <div className="space-y-3">
                  {weak_areas.slice(0, 5).map((area, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                      <div>
                        <p className="text-white text-sm">{area.source}</p>
                        <p className="text-gray-500 text-xs">{area.total_questions} questions</p>
                      </div>
                      <div className="text-right">
                        <p className={`font-medium ${getAccuracyColor(area.accuracy)}`}>
                          {area.accuracy}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No weak areas identified yet</p>
              )}
            </div>

            {/* Strong Areas */}
            <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl">
              <h3 className="text-lg font-medium text-white mb-4">
                Strengths
                <span className="text-gray-500 text-sm font-normal ml-2">(&gt;75% accuracy)</span>
              </h3>
              {strong_areas.length > 0 ? (
                <div className="space-y-3">
                  {strong_areas.slice(0, 5).map((area, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                      <div>
                        <p className="text-white text-sm">{area.source}</p>
                        <p className="text-gray-500 text-xs">{area.total_questions} questions</p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-emerald-400">
                          {area.accuracy}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">Keep studying to build mastery</p>
              )}
            </div>
          </div>

          {/* Specialty Breakdown Grid */}
          {specialtyData && (
            <div className="mb-8">
              <h3 className="text-lg font-medium text-white mb-4">Performance by Shelf Exam</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {SPECIALTIES.map((specialty) => {
                  const stats = specialtyData.specialties[specialty.apiName];
                  if (!stats) return null;

                  return (
                    <button
                      key={specialty.id}
                      onClick={() => router.push(`/study?specialty=${encodeURIComponent(specialty.apiName)}`)}
                      className={`p-4 rounded-xl border ${specialty.borderColor} ${specialty.bgColor} text-left transition-all hover:scale-[1.02]`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xl">{specialty.icon}</span>
                        <span className={`text-sm font-medium ${specialty.color}`}>{specialty.shortName}</span>
                      </div>

                      {stats.total > 0 ? (
                        <>
                          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden mb-2">
                            <div
                              className={`h-full ${stats.accuracy >= 70 ? 'bg-emerald-500' : stats.accuracy >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                              style={{ width: `${stats.accuracy}%` }}
                            />
                          </div>
                          <div className="flex justify-between text-xs">
                            <span className="text-gray-500">{stats.total} Qs</span>
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
            </div>
          )}

          {/* Behavioral Insights */}
          <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl mb-8">
            <h3 className="text-lg font-medium text-white mb-4">Study Behavior Insights</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center p-4 bg-gray-800/50 rounded-lg">
                <p className="text-2xl font-semibold text-white">
                  {Math.round(behavioral_insights.time_analysis.avg_time_overall || 0)}s
                </p>
                <p className="text-gray-500 text-xs">Avg Time/Question</p>
              </div>
              <div className="text-center p-4 bg-gray-800/50 rounded-lg">
                <p className="text-2xl font-semibold text-emerald-400">
                  {Math.round(behavioral_insights.time_analysis.avg_time_correct || 0)}s
                </p>
                <p className="text-gray-500 text-xs">Avg Time (Correct)</p>
              </div>
              <div className="text-center p-4 bg-gray-800/50 rounded-lg">
                <p className="text-2xl font-semibold text-red-400">
                  {Math.round(behavioral_insights.time_analysis.avg_time_incorrect || 0)}s
                </p>
                <p className="text-gray-500 text-xs">Avg Time (Incorrect)</p>
              </div>
              <div className="text-center p-4 bg-gray-800/50 rounded-lg">
                <p className="text-2xl font-semibold text-[#4169E1]">
                  {behavioral_insights.optimal_conditions.best_hours?.[0]
                    ? formatHour(behavioral_insights.optimal_conditions.best_hours[0].hour)
                    : '---'}
                </p>
                <p className="text-gray-500 text-xs">Best Study Time</p>
              </div>
            </div>

            {/* Confidence Calibration */}
            {behavioral_insights.confidence_analysis.correlation && (
              <div className="mt-6 p-4 bg-gray-800/30 rounded-lg">
                <p className="text-sm text-gray-400">
                  <span className="text-white font-medium">Confidence Calibration: </span>
                  {behavioral_insights.confidence_analysis.correlation === 'well_calibrated'
                    ? 'Your confidence matches your accuracy well'
                    : behavioral_insights.confidence_analysis.correlation === 'overconfident'
                    ? 'You may be overconfident - high confidence doesnt always mean correct'
                    : 'Work on calibrating your confidence with your actual performance'}
                </p>
              </div>
            )}
          </div>

          {/* Back to Study Button */}
          <div className="text-center pb-8">
            <button
              onClick={() => router.push('/study')}
              className="px-8 py-3 bg-[#4169E1] hover:bg-[#5B7FE8] text-white rounded-full transition-colors text-base font-medium"
            >
              Back to Studying
            </button>
          </div>
        </div>
      </main>
    </>
  );
}
