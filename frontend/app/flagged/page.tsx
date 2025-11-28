'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useUser } from '@/contexts/UserContext';
import { LoadingSpinner } from '@/components/SkeletonLoader';
import { Button, Badge } from '@/components/ui';

const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });

interface FlaggedQuestion {
  id: string;
  question_id: string;
  flag_reason: string | null;
  custom_note: string | null;
  flagged_after_correct: boolean | null;
  folder: string | null;
  priority: number;
  times_reviewed: number;
  last_reviewed_at: string | null;
  review_mastered: boolean;
  flagged_at: string;
  question?: {
    id: string;
    vignette: string;
    source: string;
    specialty: string;
    difficulty_level: string;
  };
}

interface FlaggedStats {
  total_active: number;
  total_mastered: number;
  never_reviewed: number;
  high_priority: number;
  correct_when_flagged: number;
  incorrect_when_flagged: number;
  by_reason: Record<string, number>;
  by_specialty: Record<string, number>;
}

const FLAG_REASON_LABELS: Record<string, string> = {
  review_concept: 'Review Concept',
  tricky_wording: 'Tricky Wording',
  high_yield: 'High Yield',
  uncertain: 'Uncertain',
  custom: 'Custom Note',
  no_reason: 'No Reason',
};

const PRIORITY_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: 'Low', color: 'text-blue-400 bg-blue-500/10' },
  2: { label: 'Medium', color: 'text-amber-400 bg-amber-500/10' },
  3: { label: 'High', color: 'text-red-400 bg-red-500/10' },
};

function FlaggedContent() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  // Start with sidebar closed to avoid hydration mismatch
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Set initial sidebar state after mount
  useEffect(() => {
    setSidebarOpen(window.innerWidth >= 900);
  }, []);

  const [flagged, setFlagged] = useState<FlaggedQuestion[]>([]);
  const [stats, setStats] = useState<FlaggedStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterReason, setFilterReason] = useState<string | null>(null);
  const [filterPriority, setFilterPriority] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState('flagged_at');

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      loadFlagged();
      loadStats();
    }
  }, [user, userLoading, router, filterReason, filterPriority, sortBy]);

  const loadFlagged = async () => {
    if (!user) return;
    setLoading(true);

    try {
      let url = `${apiUrl}/api/flagged/list?user_id=${user.userId}&sort_by=${sortBy}&sort_order=desc&limit=100`;
      if (filterReason) url += `&reason=${filterReason}`;
      if (filterPriority) url += `&priority=${filterPriority}`;

      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setFlagged(data.flagged);
      }
    } catch (error) {
      console.error('Error loading flagged questions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    if (!user) return;

    try {
      const response = await fetch(`${apiUrl}/api/flagged/stats?user_id=${user.userId}`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleUnflag = async (questionId: string) => {
    if (!user) return;

    try {
      const response = await fetch(
        `${apiUrl}/api/flagged/unflag?user_id=${user.userId}&question_id=${questionId}`,
        { method: 'DELETE' }
      );

      if (response.ok) {
        setFlagged(flagged.filter(f => f.question_id !== questionId));
        loadStats();
      }
    } catch (error) {
      console.error('Error unflagging:', error);
    }
  };

  const handleMarkMastered = async (flagId: string) => {
    if (!user) return;

    try {
      const response = await fetch(
        `${apiUrl}/api/flagged/mark-reviewed/${flagId}?user_id=${user.userId}&mastered=true`,
        { method: 'POST' }
      );

      if (response.ok) {
        setFlagged(flagged.filter(f => f.id !== flagId));
        loadStats();
      }
    } catch (error) {
      console.error('Error marking mastered:', error);
    }
  };

  const startReviewSession = () => {
    // Navigate to a review session for flagged questions
    router.push('/flagged/review');
  };

  if (userLoading || loading) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="flex items-center justify-center min-h-screen">
            <LoadingSpinner size="lg" />
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
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-6 md:py-8 pt-14 md:pt-16">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
            <div>
              <h1 className="text-2xl font-semibold text-white mb-2">Flagged Questions</h1>
              <p className="text-gray-500 text-sm">
                Questions you've marked for later review
              </p>
            </div>

            {stats && stats.total_active > 0 && (
              <Button variant="warning" onClick={startReviewSession}>
                Start Review Session
              </Button>
            )}
          </div>

          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-2xl font-semibold text-white">{stats.total_active}</div>
                <div className="text-sm text-gray-500">Active Flags</div>
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-2xl font-semibold text-red-400">{stats.high_priority}</div>
                <div className="text-sm text-gray-500">High Priority</div>
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-2xl font-semibold text-amber-400">{stats.never_reviewed}</div>
                <div className="text-sm text-gray-500">Never Reviewed</div>
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-2xl font-semibold text-emerald-400">{stats.total_mastered}</div>
                <div className="text-sm text-gray-500">Mastered</div>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 mb-6">
            <span className="text-sm text-gray-500">Filter:</span>

            {/* Priority Filter */}
            <select
              value={filterPriority || ''}
              onChange={(e) => setFilterPriority(e.target.value ? Number(e.target.value) : null)}
              className="px-3 py-1.5 text-sm bg-gray-900 border border-gray-800 rounded-lg text-gray-300 focus:outline-none focus:border-gray-700"
            >
              <option value="">All Priorities</option>
              <option value="3">High Priority</option>
              <option value="2">Medium Priority</option>
              <option value="1">Low Priority</option>
            </select>

            {/* Reason Filter */}
            <select
              value={filterReason || ''}
              onChange={(e) => setFilterReason(e.target.value || null)}
              className="px-3 py-1.5 text-sm bg-gray-900 border border-gray-800 rounded-lg text-gray-300 focus:outline-none focus:border-gray-700"
            >
              <option value="">All Reasons</option>
              {Object.entries(FLAG_REASON_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-1.5 text-sm bg-gray-900 border border-gray-800 rounded-lg text-gray-300 focus:outline-none focus:border-gray-700"
            >
              <option value="flagged_at">Date Flagged</option>
              <option value="priority">Priority</option>
              <option value="times_reviewed">Times Reviewed</option>
            </select>
          </div>

          {/* Flagged List */}
          {flagged.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">🚩</div>
              <h2 className="text-xl font-medium text-gray-300 mb-2">No Flagged Questions</h2>
              <p className="text-gray-500 mb-6">
                Flag questions during your study sessions to review them later
              </p>
              <Button variant="primary" onClick={() => router.push('/study')}>
                Start Studying
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {flagged.map((flag) => (
                <div
                  key={flag.id}
                  className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      {/* Question Preview */}
                      <p className="text-gray-300 text-sm mb-3 line-clamp-2">
                        {flag.question?.vignette || 'Question content not available'}
                      </p>

                      {/* Meta Info */}
                      <div className="flex flex-wrap items-center gap-2">
                        {/* Priority Badge */}
                        <Badge variant={flag.priority === 3 ? 'danger' : flag.priority === 2 ? 'warning' : 'info'}>
                          {PRIORITY_LABELS[flag.priority]?.label || 'Normal'}
                        </Badge>

                        {/* Reason Badge */}
                        {flag.flag_reason && (
                          <Badge variant="default">
                            {FLAG_REASON_LABELS[flag.flag_reason] || flag.flag_reason}
                          </Badge>
                        )}

                        {/* Specialty */}
                        {flag.question?.specialty && (
                          <Badge variant="default">
                            {flag.question.specialty}
                          </Badge>
                        )}

                        {/* Correct/Incorrect when flagged */}
                        {flag.flagged_after_correct !== null && (
                          <Badge variant={flag.flagged_after_correct ? 'success' : 'danger'}>
                            {flag.flagged_after_correct ? 'Got it right' : 'Got it wrong'}
                          </Badge>
                        )}

                        {/* Review count */}
                        {flag.times_reviewed > 0 && (
                          <span className="text-xs text-gray-600">
                            Reviewed {flag.times_reviewed}x
                          </span>
                        )}
                      </div>

                      {/* Custom Note */}
                      {flag.custom_note && (
                        <p className="mt-2 text-xs text-gray-500 italic">
                          "{flag.custom_note}"
                        </p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => handleMarkMastered(flag.id)}
                        className="p-2 text-gray-500 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
                        title="Mark as mastered"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleUnflag(flag.question_id)}
                        className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                        title="Remove flag"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  );
}

export default function FlaggedPage() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </main>
    }>
      <FlaggedContent />
    </Suspense>
  );
}
