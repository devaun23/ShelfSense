'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@/contexts/UserContext';

interface QuestionItem {
  id: string;
  vignette_preview: string;
  specialty: string | null;
  content_status: string;
  quality_score: number | null;
  created_at: string;
}

interface QuestionsResponse {
  questions: QuestionItem[];
  total: number;
  page: number;
  per_page: number;
}

interface QuestionDetail {
  id: string;
  vignette: string;
  answer_key: string;
  choices: Record<string, string>;
  explanation: any;
  specialty: string | null;
  source: string | null;
  content_status: string;
  difficulty_level: string | null;
  quality_score: number | null;
  expert_reviewed: boolean;
  created_at: string;
  total_attempts: number;
  correct_attempts: number;
  accuracy: number | null;
}

export default function AdminContentPage() {
  const { getAccessToken } = useUser();
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const perPage = 20;

  useEffect(() => {
    fetchQuestions();
  }, [page, search, statusFilter]);

  const fetchQuestions = async () => {
    try {
      setLoading(true);
      const token = await getAccessToken();
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
      });
      if (search) params.append('search', search);
      if (statusFilter) params.append('content_status', statusFilter);

      const response = await fetch(`${apiUrl}/api/admin/questions?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to fetch questions');

      const data: QuestionsResponse = await response.json();
      setQuestions(data.questions);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const viewQuestion = async (id: string) => {
    try {
      setDetailLoading(true);
      const token = await getAccessToken();
      const response = await fetch(`${apiUrl}/api/admin/questions/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to fetch question');

      const data = await response.json();
      setSelectedQuestion(data);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setDetailLoading(false);
    }
  };

  const updateQuestionStatus = async (id: string, newStatus: string) => {
    try {
      setActionLoading(true);
      const token = await getAccessToken();
      const response = await fetch(`${apiUrl}/api/admin/questions/${id}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content_status: newStatus }),
      });

      if (!response.ok) throw new Error('Failed to update question');

      await fetchQuestions();
      if (selectedQuestion?.id === id) {
        setSelectedQuestion({ ...selectedQuestion, content_status: newStatus });
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setActionLoading(false);
    }
  };

  const deleteQuestion = async (id: string) => {
    if (!confirm('Are you sure you want to delete this question? This will archive it.')) {
      return;
    }

    try {
      setActionLoading(true);
      const token = await getAccessToken();
      const response = await fetch(`${apiUrl}/api/admin/questions/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to delete question');

      await fetchQuestions();
      if (selectedQuestion?.id === id) {
        setSelectedQuestion(null);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setActionLoading(false);
    }
  };

  const totalPages = Math.ceil(total / perPage);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-900/30 text-green-400';
      case 'draft':
        return 'bg-yellow-900/30 text-yellow-400';
      case 'archived':
        return 'bg-gray-800 text-gray-400';
      case 'deleted':
        return 'bg-red-900/30 text-red-400';
      default:
        return 'bg-gray-800 text-gray-400';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Content Management</h1>
        <p className="text-sm text-gray-400">{total} questions</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <input
          type="text"
          placeholder="Search questions..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="flex-1 min-w-[200px] px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#4169E1]"
        />
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-white focus:outline-none focus:border-[#4169E1]"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="draft">Draft</option>
          <option value="archived">Archived</option>
          <option value="deleted">Deleted</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Questions List */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <div className="p-4 border-b border-gray-800">
            <h2 className="font-medium text-white">Questions</h2>
          </div>
          <div className="divide-y divide-gray-800 max-h-[600px] overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#4169E1] mx-auto" />
              </div>
            ) : questions.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No questions found</div>
            ) : (
              questions.map((q) => (
                <button
                  key={q.id}
                  onClick={() => viewQuestion(q.id)}
                  className={`w-full p-4 text-left hover:bg-gray-800/50 transition-colors ${
                    selectedQuestion?.id === q.id ? 'bg-gray-800/50' : ''
                  }`}
                >
                  <p className="text-sm text-white line-clamp-2 mb-2">
                    {q.vignette_preview}
                  </p>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(q.content_status)}`}>
                      {q.content_status}
                    </span>
                    {q.specialty && (
                      <span className="text-xs text-gray-500">{q.specialty}</span>
                    )}
                    {q.quality_score !== null && (
                      <span className="text-xs text-gray-500">
                        Quality: {q.quality_score.toFixed(0)}%
                      </span>
                    )}
                  </div>
                </button>
              ))
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

        {/* Question Detail */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <div className="p-4 border-b border-gray-800">
            <h2 className="font-medium text-white">Question Detail</h2>
          </div>
          <div className="p-4 max-h-[600px] overflow-y-auto">
            {detailLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#4169E1]" />
              </div>
            ) : selectedQuestion ? (
              <div className="space-y-4">
                {/* Status & Actions */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(selectedQuestion.content_status)}`}>
                    {selectedQuestion.content_status}
                  </span>
                  <div className="flex-1" />
                  <select
                    value={selectedQuestion.content_status}
                    onChange={(e) => updateQuestionStatus(selectedQuestion.id, e.target.value)}
                    disabled={actionLoading}
                    className="text-xs px-2 py-1 bg-gray-800 border border-gray-700 rounded text-white"
                  >
                    <option value="active">Active</option>
                    <option value="draft">Draft</option>
                    <option value="archived">Archived</option>
                  </select>
                  <button
                    onClick={() => deleteQuestion(selectedQuestion.id)}
                    disabled={actionLoading}
                    className="text-xs px-2 py-1 bg-red-900/30 text-red-400 rounded hover:bg-red-900/50"
                  >
                    Delete
                  </button>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="bg-gray-800 rounded p-2">
                    <p className="text-lg font-semibold text-white">{selectedQuestion.total_attempts}</p>
                    <p className="text-xs text-gray-500">Attempts</p>
                  </div>
                  <div className="bg-gray-800 rounded p-2">
                    <p className="text-lg font-semibold text-white">{selectedQuestion.correct_attempts}</p>
                    <p className="text-xs text-gray-500">Correct</p>
                  </div>
                  <div className="bg-gray-800 rounded p-2">
                    <p className="text-lg font-semibold text-white">
                      {selectedQuestion.accuracy !== null
                        ? `${selectedQuestion.accuracy.toFixed(0)}%`
                        : 'N/A'}
                    </p>
                    <p className="text-xs text-gray-500">Accuracy</p>
                  </div>
                </div>

                {/* Vignette */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Vignette</p>
                  <p className="text-sm text-white whitespace-pre-wrap">{selectedQuestion.vignette}</p>
                </div>

                {/* Choices */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Choices</p>
                  <div className="space-y-1">
                    {selectedQuestion.choices &&
                      Object.entries(selectedQuestion.choices).map(([key, value]) => (
                        <div
                          key={key}
                          className={`p-2 rounded text-sm ${
                            key === selectedQuestion.answer_key
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
                    <p className="text-white">{selectedQuestion.specialty || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Difficulty</p>
                    <p className="text-white">{selectedQuestion.difficulty_level || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Source</p>
                    <p className="text-white">{selectedQuestion.source || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Expert Reviewed</p>
                    <p className="text-white">{selectedQuestion.expert_reviewed ? 'Yes' : 'No'}</p>
                  </div>
                </div>

                {/* ID */}
                <div>
                  <p className="text-xs text-gray-500">Question ID</p>
                  <p className="text-xs text-gray-400 font-mono">{selectedQuestion.id}</p>
                </div>
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                Select a question to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
