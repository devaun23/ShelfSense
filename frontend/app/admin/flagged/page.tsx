'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@/contexts/UserContext';

interface FlaggedItem {
  id: string;
  question_id: string;
  question_preview: string;
  specialty: string | null;
  user_email: string;
  flag_reason: string | null;
  custom_note: string | null;
  priority: number;
  flagged_after_correct: boolean | null;
  times_reviewed: number;
  flagged_at: string;
}

interface FlaggedStats {
  total_flagged: number;
  by_reason: Record<string, number>;
  by_specialty: Record<string, number>;
  most_flagged_questions: Array<{
    question_id: string;
    preview: string;
    specialty: string | null;
    flag_count: number;
  }>;
}

interface QuestionFlags {
  question: {
    id: string;
    vignette: string;
    answer_key: string;
    choices: Record<string, string>;
    explanation: any;
    specialty: string | null;
    difficulty_level: string | null;
    content_status: string;
  };
  flags: Array<{
    id: string;
    user_email: string;
    flag_reason: string | null;
    custom_note: string | null;
    priority: number;
    flagged_after_correct: boolean | null;
    times_reviewed: number;
    flagged_at: string;
  }>;
  total_flags: number;
}

interface FlaggedResponse {
  items: FlaggedItem[];
  total: number;
  page: number;
  per_page: number;
}

const FLAG_REASONS: Record<string, { label: string; color: string }> = {
  review_concept: { label: 'Review Concept', color: 'bg-blue-900/30 text-blue-400' },
  tricky_wording: { label: 'Tricky Wording', color: 'bg-orange-900/30 text-orange-400' },
  high_yield: { label: 'High Yield', color: 'bg-green-900/30 text-green-400' },
  uncertain: { label: 'Uncertain', color: 'bg-yellow-900/30 text-yellow-400' },
  custom: { label: 'Custom', color: 'bg-purple-900/30 text-purple-400' },
  no_reason: { label: 'No Reason', color: 'bg-gray-800 text-gray-400' },
};

export default function FlaggedQuestionsPage() {
  const { getAccessToken } = useUser();
  const [items, setItems] = useState<FlaggedItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [reasonFilter, setReasonFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Stats
  const [stats, setStats] = useState<FlaggedStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Detail view
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionFlags | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // View mode
  const [viewMode, setViewMode] = useState<'list' | 'stats'>('list');

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const perPage = 20;

  useEffect(() => {
    fetchItems();
    fetchStats();
  }, []);

  useEffect(() => {
    fetchItems();
  }, [page, reasonFilter]);

  const fetchItems = async () => {
    try {
      setLoading(true);
      const token = await getAccessToken();
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
      });
      if (reasonFilter) params.append('flag_reason', reasonFilter);

      const response = await fetch(`${apiUrl}/api/admin/flagged?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to fetch flagged questions');

      const data: FlaggedResponse = await response.json();
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      setStatsLoading(true);
      const token = await getAccessToken();
      const response = await fetch(`${apiUrl}/api/admin/flagged/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to fetch stats');

      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    } finally {
      setStatsLoading(false);
    }
  };

  const viewQuestionFlags = async (questionId: string) => {
    try {
      setDetailLoading(true);
      const token = await getAccessToken();
      const response = await fetch(`${apiUrl}/api/admin/flagged/question/${questionId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to fetch question flags');

      const data = await response.json();
      setSelectedQuestion(data);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setDetailLoading(false);
    }
  };

  const totalPages = Math.ceil(total / perPage);

  const getReasonInfo = (reason: string | null) => {
    return FLAG_REASONS[reason || 'no_reason'] || FLAG_REASONS.no_reason;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Flagged Questions</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode('list')}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              viewMode === 'list'
                ? 'bg-[#4169E1] text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            List View
          </button>
          <button
            onClick={() => setViewMode('stats')}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              viewMode === 'stats'
                ? 'bg-[#4169E1] text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            Statistics
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      {viewMode === 'stats' ? (
        // Statistics View
        <div className="space-y-6">
          {statsLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4169E1]" />
            </div>
          ) : stats ? (
            <>
              {/* Total */}
              <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 text-center">
                <p className="text-4xl font-semibold text-white">{stats.total_flagged}</p>
                <p className="text-gray-400 mt-1">Total Active Flags</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* By Reason */}
                <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
                  <h3 className="text-sm font-medium text-white mb-4">Flags by Reason</h3>
                  <div className="space-y-2">
                    {Object.entries(stats.by_reason)
                      .sort((a, b) => b[1] - a[1])
                      .map(([reason, count]) => {
                        const info = getReasonInfo(reason);
                        return (
                          <div key={reason} className="flex items-center justify-between">
                            <span className={`text-xs px-2 py-0.5 rounded ${info.color}`}>
                              {info.label}
                            </span>
                            <span className="text-sm text-white">{count}</span>
                          </div>
                        );
                      })}
                  </div>
                </div>

                {/* By Specialty */}
                <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
                  <h3 className="text-sm font-medium text-white mb-4">Flags by Specialty</h3>
                  <div className="space-y-2 max-h-[200px] overflow-y-auto">
                    {Object.entries(stats.by_specialty)
                      .sort((a, b) => b[1] - a[1])
                      .map(([specialty, count]) => (
                        <div key={specialty} className="flex items-center justify-between">
                          <span className="text-sm text-gray-400">{specialty}</span>
                          <span className="text-sm text-white">{count}</span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>

              {/* Most Flagged Questions */}
              <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
                <h3 className="text-sm font-medium text-white mb-4">Most Flagged Questions</h3>
                <div className="divide-y divide-gray-800">
                  {stats.most_flagged_questions.map((q, idx) => (
                    <button
                      key={q.question_id}
                      onClick={() => viewQuestionFlags(q.question_id)}
                      className="w-full p-3 text-left hover:bg-gray-800/50 transition-colors flex items-start gap-3"
                    >
                      <span className="text-lg font-semibold text-[#4169E1] min-w-[24px]">
                        #{idx + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white line-clamp-2">{q.preview}</p>
                        <div className="flex items-center gap-2 mt-1">
                          {q.specialty && (
                            <span className="text-xs text-gray-500">{q.specialty}</span>
                          )}
                          <span className="text-xs text-red-400">{q.flag_count} flags</span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="text-center text-gray-500 py-8">No statistics available</div>
          )}
        </div>
      ) : (
        // List View
        <>
          {/* Filters */}
          <div className="flex flex-wrap gap-4">
            <select
              value={reasonFilter}
              onChange={(e) => {
                setReasonFilter(e.target.value);
                setPage(1);
              }}
              className="px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-white focus:outline-none focus:border-[#4169E1]"
            >
              <option value="">All Reasons</option>
              <option value="review_concept">Review Concept</option>
              <option value="tricky_wording">Tricky Wording</option>
              <option value="high_yield">High Yield</option>
              <option value="uncertain">Uncertain</option>
              <option value="custom">Custom</option>
            </select>
            <p className="text-sm text-gray-400 self-center">{total} flagged questions</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Flags List */}
            <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
              <div className="p-4 border-b border-gray-800">
                <h2 className="font-medium text-white">Flagged Questions</h2>
              </div>
              <div className="divide-y divide-gray-800 max-h-[600px] overflow-y-auto">
                {loading ? (
                  <div className="p-8 text-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#4169E1] mx-auto" />
                  </div>
                ) : items.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">No flagged questions found</div>
                ) : (
                  items.map((item) => {
                    const reasonInfo = getReasonInfo(item.flag_reason);
                    return (
                      <button
                        key={item.id}
                        onClick={() => viewQuestionFlags(item.question_id)}
                        className={`w-full p-4 text-left hover:bg-gray-800/50 transition-colors ${
                          selectedQuestion?.question.id === item.question_id ? 'bg-gray-800/50' : ''
                        }`}
                      >
                        <p className="text-sm text-white line-clamp-2 mb-2">
                          {item.question_preview}
                        </p>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-xs px-2 py-0.5 rounded ${reasonInfo.color}`}>
                            {reasonInfo.label}
                          </span>
                          {item.specialty && (
                            <span className="text-xs text-gray-500">{item.specialty}</span>
                          )}
                          <span className="text-xs text-gray-500">by {item.user_email}</span>
                          {item.priority > 1 && (
                            <span className="text-xs text-yellow-400">P{item.priority}</span>
                          )}
                        </div>
                      </button>
                    );
                  })
                )}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="p-4 border-t border-gray-800 flex items-center justify-between">
                  <span className="text-sm text-gray-400">
                    Page {page} of {totalPages}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                      className="px-2 py-1 text-xs bg-gray-800 text-gray-300 rounded hover:bg-gray-700 disabled:opacity-50"
                    >
                      Prev
                    </button>
                    <button
                      onClick={() => setPage(Math.min(totalPages, page + 1))}
                      disabled={page === totalPages}
                      className="px-2 py-1 text-xs bg-gray-800 text-gray-300 rounded hover:bg-gray-700 disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Detail Panel */}
            <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
              <div className="p-4 border-b border-gray-800">
                <h2 className="font-medium text-white">Question Details</h2>
              </div>
              <div className="p-4 max-h-[600px] overflow-y-auto">
                {detailLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#4169E1]" />
                  </div>
                ) : selectedQuestion ? (
                  <div className="space-y-4">
                    {/* Flag Summary */}
                    <div className="bg-red-900/20 border border-red-800 rounded p-3">
                      <p className="text-sm text-red-400">
                        This question has been flagged by {selectedQuestion.total_flags} user
                        {selectedQuestion.total_flags !== 1 ? 's' : ''}
                      </p>
                    </div>

                    {/* Question Content */}
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Vignette</p>
                      <p className="text-sm text-white whitespace-pre-wrap">
                        {selectedQuestion.question.vignette}
                      </p>
                    </div>

                    {/* Choices */}
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Choices</p>
                      <div className="space-y-1">
                        {selectedQuestion.question.choices &&
                          Object.entries(selectedQuestion.question.choices).map(([key, value]) => (
                            <div
                              key={key}
                              className={`p-2 rounded text-sm ${
                                key === selectedQuestion.question.answer_key
                                  ? 'bg-green-900/30 text-green-400 border border-green-800'
                                  : 'bg-gray-800 text-gray-300'
                              }`}
                            >
                              <span className="font-medium">{key}.</span> {value}
                            </div>
                          ))}
                      </div>
                    </div>

                    {/* Metadata */}
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <p className="text-xs text-gray-500">Specialty</p>
                        <p className="text-white">{selectedQuestion.question.specialty || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Difficulty</p>
                        <p className="text-white">
                          {selectedQuestion.question.difficulty_level || 'N/A'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Status</p>
                        <p className="text-white">{selectedQuestion.question.content_status}</p>
                      </div>
                    </div>

                    {/* Individual Flags */}
                    <div className="border-t border-gray-800 pt-4">
                      <h3 className="text-sm font-medium text-white mb-3">
                        User Flags ({selectedQuestion.flags.length})
                      </h3>
                      <div className="space-y-3">
                        {selectedQuestion.flags.map((flag) => {
                          const reasonInfo = getReasonInfo(flag.flag_reason);
                          return (
                            <div
                              key={flag.id}
                              className="bg-gray-800 rounded p-3 space-y-2"
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-400">{flag.user_email}</span>
                                <span className={`text-xs px-2 py-0.5 rounded ${reasonInfo.color}`}>
                                  {reasonInfo.label}
                                </span>
                              </div>
                              {flag.custom_note && (
                                <p className="text-sm text-white">&ldquo;{flag.custom_note}&rdquo;</p>
                              )}
                              <div className="flex items-center gap-3 text-xs text-gray-500">
                                <span>
                                  {flag.flagged_after_correct
                                    ? 'Flagged after correct'
                                    : flag.flagged_after_correct === false
                                    ? 'Flagged after incorrect'
                                    : 'Context unknown'}
                                </span>
                                <span>Reviewed {flag.times_reviewed}x</span>
                                <span>{new Date(flag.flagged_at).toLocaleDateString()}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    Select a flagged question to view details
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
