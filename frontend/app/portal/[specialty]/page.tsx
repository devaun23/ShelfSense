'use client';

import { useEffect, useState, use } from 'react';
import Link from 'next/link';
import { useUser } from '@/contexts/UserContext';
import { getSpecialtyBySlug } from '@/lib/specialties';

interface PortalDashboardProps {
  params: Promise<{ specialty: string }>;
}

interface PortalStats {
  totalQuestions: number;
  accuracy: number;
  predictedScore: number | null;
  scoreConfidence: number | null;
  streak: number;
  reviewsDue: number;
  weakAreas: number;
}

export default function PortalDashboard({ params }: PortalDashboardProps) {
  const { user, isLoading } = useUser();
  const resolvedParams = use(params);
  const specialty = getSpecialtyBySlug(resolvedParams.specialty);
  const [stats, setStats] = useState<PortalStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.userId && specialty) {
      fetchPortalStats();
    }
  }, [user?.userId, specialty?.apiName]);

  const fetchPortalStats = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const specialtyParam = specialty?.apiName ? `&specialty=${encodeURIComponent(specialty.apiName)}` : '';

      // Fetch multiple stats in parallel
      const [dashboardRes, reviewsRes] = await Promise.all([
        fetch(`${apiUrl}/api/analytics/dashboard?user_id=${user?.userId}${specialtyParam}`),
        fetch(`${apiUrl}/api/reviews/stats?user_id=${user?.userId}${specialtyParam}`),
      ]);

      const dashboardData = dashboardRes.ok ? await dashboardRes.json() : {};
      const reviewsData = reviewsRes.ok ? await reviewsRes.json() : {};

      setStats({
        totalQuestions: dashboardData.total_questions || 0,
        accuracy: dashboardData.overall_accuracy || 0,
        predictedScore: dashboardData.predicted_score || null,
        scoreConfidence: dashboardData.score_confidence || null,
        streak: dashboardData.current_streak || 0,
        reviewsDue: reviewsData.due_today || 0,
        weakAreas: dashboardData.weak_areas_count || 0,
      });
    } catch (error) {
      console.error('Error fetching portal stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (isLoading || !specialty) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  const basePath = `/portal/${specialty.slug}`;

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-4xl">{specialty.icon}</span>
          <h1 className="text-3xl font-bold text-white">{specialty.name}</h1>
        </div>
        {specialty.description && (
          <p className="text-gray-400">{specialty.description}</p>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* Predicted Score */}
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <div className="text-gray-400 text-sm mb-1">Predicted Score</div>
          {loading ? (
            <div className="h-8 bg-gray-800 rounded animate-pulse" />
          ) : stats?.predictedScore ? (
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-bold text-white">{stats.predictedScore}</span>
              {stats.scoreConfidence && (
                <span className="text-gray-500 text-sm">+/- {stats.scoreConfidence}</span>
              )}
            </div>
          ) : (
            <span className="text-2xl text-gray-600">--</span>
          )}
        </div>

        {/* Accuracy */}
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <div className="text-gray-400 text-sm mb-1">Accuracy</div>
          {loading ? (
            <div className="h-8 bg-gray-800 rounded animate-pulse" />
          ) : (
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-bold text-white">
                {stats?.totalQuestions ? `${Math.round(stats.accuracy * 100)}%` : '--'}
              </span>
            </div>
          )}
        </div>

        {/* Questions */}
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <div className="text-gray-400 text-sm mb-1">Questions Done</div>
          {loading ? (
            <div className="h-8 bg-gray-800 rounded animate-pulse" />
          ) : (
            <span className="text-3xl font-bold text-white">{stats?.totalQuestions || 0}</span>
          )}
        </div>

        {/* Streak */}
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <div className="text-gray-400 text-sm mb-1">Day Streak</div>
          {loading ? (
            <div className="h-8 bg-gray-800 rounded animate-pulse" />
          ) : (
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-bold text-white">{stats?.streak || 0}</span>
              <span className="text-orange-500">days</span>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <h2 className="text-xl font-semibold text-white mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {/* Start Practice */}
        <Link
          href={`${basePath}/study`}
          className="bg-blue-600 hover:bg-blue-700 rounded-xl p-6 transition-colors group"
        >
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">📝</span>
            <h3 className="text-lg font-semibold text-white">Start Practice</h3>
          </div>
          <p className="text-blue-200 text-sm">Begin an adaptive study session</p>
        </Link>

        {/* Reviews Due */}
        <Link
          href={`${basePath}/reviews`}
          className={`rounded-xl p-6 transition-colors group ${
            stats?.reviewsDue
              ? 'bg-emerald-600 hover:bg-emerald-700'
              : 'bg-gray-800 hover:bg-gray-700'
          }`}
        >
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">🔄</span>
            <h3 className="text-lg font-semibold text-white">Reviews</h3>
            {stats?.reviewsDue ? (
              <span className="bg-white/20 text-white text-sm font-medium px-2 py-0.5 rounded-full">
                {stats.reviewsDue} due
              </span>
            ) : null}
          </div>
          <p className={stats?.reviewsDue ? 'text-emerald-200' : 'text-gray-400'} >
            {stats?.reviewsDue ? 'Questions ready for review' : 'No reviews due today'}
          </p>
        </Link>

        {/* Weak Areas */}
        <Link
          href={`${basePath}/weak-areas`}
          className="bg-gray-800 hover:bg-gray-700 rounded-xl p-6 transition-colors group"
        >
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">🎯</span>
            <h3 className="text-lg font-semibold text-white">Weak Areas</h3>
          </div>
          <p className="text-gray-400 text-sm">Focus on topics needing improvement</p>
        </Link>
      </div>

      {/* Progress Section */}
      {stats?.totalQuestions && stats.totalQuestions > 0 && (
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <h2 className="text-lg font-semibold text-white mb-4">Your Progress</h2>
          <div className="space-y-4">
            {/* Accuracy bar */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">Overall Accuracy</span>
                <span className="text-white">{Math.round((stats.accuracy || 0) * 100)}%</span>
              </div>
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all duration-500"
                  style={{ width: `${(stats.accuracy || 0) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
