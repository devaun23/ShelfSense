'use client';

import { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { getSpecialtyBySlug } from '@/lib/specialties';
import EyeLogo from '@/components/icons/EyeLogo';
import SpecialtyIcon from '@/components/icons/SpecialtyIcon';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

interface PortalAnalyticsProps {
  params: Promise<{ specialty: string }>;
}

interface AnalyticsData {
  totalQuestions: number;
  accuracy: number;
  questionsToday: number;
  streak: number;
  topTopics: { topic: string; accuracy: number; count: number }[];
  recentSessions: { date: string; questions: number; accuracy: number }[];
}

export default function PortalAnalytics({ params }: PortalAnalyticsProps) {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const resolvedParams = use(params);
  const specialty = getSpecialtyBySlug(resolvedParams.specialty);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.userId && specialty) {
      fetchAnalytics();
    }
  }, [user?.userId, specialty?.apiName]);

  const fetchAnalytics = async () => {
    setError(null);
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const specialtyParam = specialty?.apiName
        ? `&specialty=${encodeURIComponent(specialty.apiName)}`
        : '';

      const response = await fetch(
        `${apiUrl}/api/analytics/dashboard?user_id=${user?.userId}${specialtyParam}`
      );

      if (!response.ok) {
        throw new Error(`Failed to load analytics (${response.status})`);
      }

      const data = await response.json();
      setAnalytics({
        totalQuestions: data.total_questions || 0,
        accuracy: data.overall_accuracy || 0,
        questionsToday: data.questions_today || 0,
        streak: data.current_streak || 0,
        topTopics: data.top_topics || [],
        recentSessions: data.recent_sessions || [],
      });
    } catch (err) {
      console.error('Error fetching analytics:', err);
      setError(err instanceof Error ? err.message : 'Unable to load analytics. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (userLoading || !specialty) {
    return (
      <main
        className="min-h-screen bg-black text-white flex items-center justify-center"
        role="status"
        aria-busy="true"
        aria-label="Loading analytics"
      >
        <LoadingSpinner size="lg" />
        <span className="sr-only">Loading analytics...</span>
      </main>
    );
  }

  const basePath = `/portal/${specialty.slug}`;

  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center px-4 py-12 animate-fade-in">
      {/* Header */}
      <div className="mb-8 animate-bounce-in" style={{ animationDelay: '0ms' }}>
        <EyeLogo size={40} />
      </div>

      {/* Title */}
      <h1
        className="text-2xl font-semibold text-white mb-2 text-center animate-bounce-in"
        style={{ fontFamily: 'var(--font-serif)', animationDelay: '100ms' }}
      >
        Your Progress
      </h1>
      <p
        className="text-gray-500 mb-8 text-center animate-bounce-in"
        style={{ animationDelay: '150ms' }}
      >
        {specialty.name}
      </p>

      {/* Error State */}
      {error && (
        <div className="max-w-sm w-full mb-8 p-4 bg-red-900/20 border border-red-800 rounded-xl text-center animate-bounce-in" style={{ animationDelay: '200ms' }}>
          <p className="text-red-400 mb-3">{error}</p>
          <button
            onClick={fetchAnalytics}
            className="px-4 py-2 bg-red-900/30 hover:bg-red-900/50 border border-red-800 rounded-lg text-red-300 text-sm transition-colors"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Stats Grid */}
      {loading ? (
        <div
          className="grid grid-cols-2 gap-4 max-w-sm w-full mb-8"
          role="status"
          aria-busy="true"
          aria-label="Loading statistics"
        >
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 animate-pulse"
            >
              <div className="h-8 bg-gray-800 rounded w-12 mb-2" />
              <div className="h-4 bg-gray-800 rounded w-16" />
            </div>
          ))}
          <span className="sr-only">Loading your progress statistics...</span>
        </div>
      ) : analytics && !error ? (
        <div className="grid grid-cols-2 gap-4 max-w-sm w-full mb-8">
          <StatCard
            value={analytics.totalQuestions.toString()}
            label="questions"
            delay={200}
          />
          <StatCard
            value={`${Math.round(analytics.accuracy * 100)}%`}
            label="accuracy"
            delay={280}
          />
          <StatCard
            value={analytics.questionsToday.toString()}
            label="today"
            delay={360}
          />
          <StatCard
            value={analytics.streak.toString()}
            label="day streak"
            delay={440}
          />
        </div>
      ) : (
        <div className="text-center py-8 animate-bounce-in" style={{ animationDelay: '200ms' }}>
          <p className="text-gray-500" style={{ fontFamily: 'var(--font-serif)' }}>
            Complete some questions to see your progress.
          </p>
        </div>
      )}

      {/* Back Button */}
      <button
        onClick={() => router.push(basePath)}
        className="text-gray-600 hover:text-gray-400 text-sm transition-colors animate-bounce-in"
        style={{ animationDelay: '520ms' }}
      >
        Back to {specialty.name}
      </button>

      {/* Animation styles */}
      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes bounceIn {
          0% {
            opacity: 0;
            transform: scale(0.3) translateY(20px);
          }
          50% { transform: scale(1.05) translateY(-5px); }
          70% { transform: scale(0.95) translateY(2px); }
          100% {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        .animate-fade-in {
          animation: fadeIn 0.3s ease-out forwards;
        }
        .animate-bounce-in {
          opacity: 0;
          animation: bounceIn 0.5s ease-out forwards;
        }
      `}</style>
    </main>
  );
}

function StatCard({
  value,
  label,
  delay,
}: {
  value: string;
  label: string;
  delay: number;
}) {
  return (
    <div
      className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 text-center animate-bounce-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
}
