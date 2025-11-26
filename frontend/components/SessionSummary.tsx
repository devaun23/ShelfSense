'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface SpecialtyBreakdown {
  correct: number;
  total: number;
  accuracy: number;
}

interface SessionSummaryData {
  session_id: string;
  mode: string;
  name: string;
  status: string;
  duration_minutes: number;
  questions_answered: number;
  questions_correct: number;
  questions_skipped: number;
  accuracy: number | null;
  score: number | null;
  avg_time_per_question: number | null;
  specialty_breakdown: Record<string, SpecialtyBreakdown>;
  started_at: string | null;
  ended_at: string | null;
}

interface SessionSummaryProps {
  sessionId: string;
  onClose?: () => void;
  onNewSession?: () => void;
}

export default function SessionSummary({ sessionId, onClose, onNewSession }: SessionSummaryProps) {
  const router = useRouter();
  const [summary, setSummary] = useState<SessionSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${API_URL}/api/study-modes/sessions/${sessionId}/summary`);

        if (!response.ok) {
          throw new Error('Failed to load session summary');
        }

        const data = await response.json();
        setSummary(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load summary');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
        <div className="bg-zinc-900 rounded-xl p-8 text-center">
          <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-white">Loading results...</p>
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
        <div className="bg-zinc-900 rounded-xl p-8 text-center">
          <p className="text-red-400 mb-4">{error || 'Failed to load summary'}</p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getModeIcon = (mode: string) => {
    const icons: Record<string, string> = {
      practice: '📚',
      timed: '⏱️',
      tutor: '🎓',
      challenge: '🔥',
      review: '🔄',
      weak_focus: '🎯'
    };
    return icons[mode] || '📝';
  };

  const specialties = Object.entries(summary.specialty_breakdown || {});

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-zinc-800">
        {/* Header */}
        <div className="p-6 border-b border-zinc-800 text-center">
          <div className="text-4xl mb-2">{getModeIcon(summary.mode)}</div>
          <h2 className="text-2xl font-bold text-white">Session Complete!</h2>
          <p className="text-zinc-400 mt-1">{summary.name}</p>
        </div>

        {/* Score Section */}
        <div className="p-6 border-b border-zinc-800">
          <div className="grid grid-cols-3 gap-4 text-center">
            {/* Accuracy */}
            <div className="bg-zinc-800 rounded-xl p-4">
              <p className="text-zinc-400 text-sm mb-1">Accuracy</p>
              <p className={`text-3xl font-bold ${getScoreColor(summary.accuracy || 0)}`}>
                {summary.accuracy?.toFixed(1)}%
              </p>
            </div>

            {/* Score */}
            <div className="bg-zinc-800 rounded-xl p-4">
              <p className="text-zinc-400 text-sm mb-1">Score</p>
              <p className={`text-3xl font-bold ${getScoreColor(summary.accuracy || 0)}`}>
                {summary.score || 0}
              </p>
            </div>

            {/* Questions */}
            <div className="bg-zinc-800 rounded-xl p-4">
              <p className="text-zinc-400 text-sm mb-1">Questions</p>
              <p className="text-3xl font-bold text-white">
                {summary.questions_correct}/{summary.questions_answered}
              </p>
            </div>
          </div>

          {/* Additional Stats */}
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="bg-zinc-800/50 rounded-lg p-3 flex items-center gap-3">
              <svg className="w-5 h-5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-zinc-400 text-xs">Duration</p>
                <p className="text-white font-medium">{summary.duration_minutes.toFixed(1)} min</p>
              </div>
            </div>

            <div className="bg-zinc-800/50 rounded-lg p-3 flex items-center gap-3">
              <svg className="w-5 h-5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <div>
                <p className="text-zinc-400 text-xs">Avg. Time/Question</p>
                <p className="text-white font-medium">
                  {summary.avg_time_per_question?.toFixed(1) || 0}s
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Specialty Breakdown */}
        {specialties.length > 0 && (
          <div className="p-6 border-b border-zinc-800">
            <h3 className="text-lg font-semibold text-white mb-4">Performance by Specialty</h3>
            <div className="space-y-3">
              {specialties.map(([specialty, stats]) => (
                <div key={specialty} className="flex items-center gap-4">
                  <div className="flex-1">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-zinc-300">{specialty}</span>
                      <span className={getScoreColor(stats.accuracy)}>
                        {stats.correct}/{stats.total} ({stats.accuracy.toFixed(0)}%)
                      </span>
                    </div>
                    <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          stats.accuracy >= 80
                            ? 'bg-green-500'
                            : stats.accuracy >= 60
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${stats.accuracy}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Performance Assessment */}
        <div className="p-6 border-b border-zinc-800">
          <h3 className="text-lg font-semibold text-white mb-3">Assessment</h3>
          <div className={`p-4 rounded-lg ${
            (summary.accuracy || 0) >= 80
              ? 'bg-green-500/20 border border-green-500/50'
              : (summary.accuracy || 0) >= 60
              ? 'bg-yellow-500/20 border border-yellow-500/50'
              : 'bg-red-500/20 border border-red-500/50'
          }`}>
            <p className={`font-medium ${
              (summary.accuracy || 0) >= 80
                ? 'text-green-400'
                : (summary.accuracy || 0) >= 60
                ? 'text-yellow-400'
                : 'text-red-400'
            }`}>
              {(summary.accuracy || 0) >= 80
                ? 'Excellent performance! Keep up the great work.'
                : (summary.accuracy || 0) >= 60
                ? 'Good effort! Some areas need more review.'
                : 'Needs improvement. Focus on weak areas.'}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="p-6 flex justify-center gap-4">
          <button
            onClick={() => router.push('/')}
            className="px-6 py-3 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg transition-colors"
          >
            Go Home
          </button>
          <button
            onClick={() => router.push('/analytics')}
            className="px-6 py-3 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg transition-colors"
          >
            View Analytics
          </button>
          {onNewSession && (
            <button
              onClick={onNewSession}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              New Session
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
