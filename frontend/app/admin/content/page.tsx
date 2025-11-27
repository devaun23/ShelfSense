'use client';

import { useEffect, useState, useCallback } from 'react';
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

interface EditFormData {
  vignette: string;
  answer_key: string;
  choices: Record<string, string>;
  explanation: string;
  specialty: string;
  difficulty_level: string;
  content_status: string;
}

const SPECIALTIES = [
  'Cardiology',
  'Pulmonology',
  'Gastroenterology',
  'Nephrology',
  'Neurology',
  'Hematology/Oncology',
  'Endocrinology',
  'Rheumatology',
  'Infectious Disease',
  'General Internal Medicine',
  'Psychiatry',
  'Dermatology',
  'Emergency Medicine',
  'Pediatrics',
  'OB/GYN',
  'Surgery',
  'Orthopedics',
  'Urology',
  'Ophthalmology',
  'ENT',
  'Preventive Medicine',
  'Biostatistics/Epidemiology',
  'Ethics',
  'Pharmacology',
];

const DIFFICULTY_LEVELS = ['easy', 'medium', 'hard'];

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

  // Edit modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editForm, setEditForm] = useState<EditFormData | null>(null);
  const [editSaving, setEditSaving] = useState(false);

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

  // Open edit modal
  const openEditModal = useCallback(() => {
    if (!selectedQuestion) return;

    // Parse explanation - it might be a string or object
    let explanationText = '';
    if (selectedQuestion.explanation) {
      if (typeof selectedQuestion.explanation === 'string') {
        explanationText = selectedQuestion.explanation;
      } else if (typeof selectedQuestion.explanation === 'object') {
        explanationText = selectedQuestion.explanation.text ||
                         selectedQuestion.explanation.main ||
                         JSON.stringify(selectedQuestion.explanation, null, 2);
      }
    }

    setEditForm({
      vignette: selectedQuestion.vignette || '',
      answer_key: selectedQuestion.answer_key || 'A',
      choices: selectedQuestion.choices || { A: '', B: '', C: '', D: '', E: '' },
      explanation: explanationText,
      specialty: selectedQuestion.specialty || '',
      difficulty_level: selectedQuestion.difficulty_level || 'medium',
      content_status: selectedQuestion.content_status || 'draft',
    });
    setIsEditModalOpen(true);
  }, [selectedQuestion]);

  // Save edited question
  const saveQuestion = async () => {
    if (!selectedQuestion || !editForm) return;

    try {
      setEditSaving(true);
      const token = await getAccessToken();

      // Prepare explanation as object if it was originally an object
      let explanationPayload: any = editForm.explanation;
      if (selectedQuestion.explanation && typeof selectedQuestion.explanation === 'object') {
        explanationPayload = {
          ...selectedQuestion.explanation,
          text: editForm.explanation,
          main: editForm.explanation,
        };
      }

      const response = await fetch(`${apiUrl}/api/admin/questions/${selectedQuestion.id}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          vignette: editForm.vignette,
          answer_key: editForm.answer_key,
          choices: editForm.choices,
          explanation: explanationPayload,
          specialty: editForm.specialty || null,
          difficulty_level: editForm.difficulty_level || null,
          content_status: editForm.content_status,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to save question');
      }

      // Refresh the question detail and list
      await viewQuestion(selectedQuestion.id);
      await fetchQuestions();
      setIsEditModalOpen(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setEditSaving(false);
    }
  };

  // Update choice
  const updateChoice = (key: string, value: string) => {
    if (!editForm) return;
    setEditForm({
      ...editForm,
      choices: { ...editForm.choices, [key]: value },
    });
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
                    onClick={openEditModal}
                    disabled={actionLoading}
                    className="text-xs px-2 py-1 bg-[#4169E1]/30 text-[#4169E1] rounded hover:bg-[#4169E1]/50"
                  >
                    Edit
                  </button>
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

      {/* Edit Modal */}
      {isEditModalOpen && editForm && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-lg border border-gray-800 w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <h2 className="text-lg font-medium text-white">Edit Question</h2>
              <button
                onClick={() => setIsEditModalOpen(false)}
                className="text-gray-400 hover:text-white"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Vignette */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">Vignette / Question Stem</label>
                <textarea
                  value={editForm.vignette}
                  onChange={(e) => setEditForm({ ...editForm, vignette: e.target.value })}
                  rows={6}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-[#4169E1] resize-y"
                  placeholder="Enter the clinical vignette..."
                />
              </div>

              {/* Choices */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Answer Choices</label>
                <div className="space-y-2">
                  {['A', 'B', 'C', 'D', 'E'].map((key) => (
                    <div key={key} className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setEditForm({ ...editForm, answer_key: key })}
                        className={`w-8 h-8 rounded flex items-center justify-center text-sm font-medium transition-colors ${
                          editForm.answer_key === key
                            ? 'bg-green-600 text-white'
                            : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                        }`}
                        title={editForm.answer_key === key ? 'Correct answer' : 'Click to set as correct'}
                      >
                        {key}
                      </button>
                      <input
                        type="text"
                        value={editForm.choices[key] || ''}
                        onChange={(e) => updateChoice(key, e.target.value)}
                        className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-[#4169E1]"
                        placeholder={`Choice ${key}...`}
                      />
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-1">Click a letter to set it as the correct answer (green = correct)</p>
              </div>

              {/* Explanation */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">Explanation</label>
                <textarea
                  value={editForm.explanation}
                  onChange={(e) => setEditForm({ ...editForm, explanation: e.target.value })}
                  rows={4}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-[#4169E1] resize-y"
                  placeholder="Enter the explanation for the correct answer..."
                />
              </div>

              {/* Metadata Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Specialty */}
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Specialty</label>
                  <select
                    value={editForm.specialty}
                    onChange={(e) => setEditForm({ ...editForm, specialty: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-[#4169E1]"
                  >
                    <option value="">Select specialty...</option>
                    {SPECIALTIES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                {/* Difficulty */}
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Difficulty</label>
                  <select
                    value={editForm.difficulty_level}
                    onChange={(e) => setEditForm({ ...editForm, difficulty_level: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-[#4169E1]"
                  >
                    {DIFFICULTY_LEVELS.map((d) => (
                      <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
                    ))}
                  </select>
                </div>

                {/* Status */}
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Status</label>
                  <select
                    value={editForm.content_status}
                    onChange={(e) => setEditForm({ ...editForm, content_status: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-[#4169E1]"
                  >
                    <option value="draft">Draft</option>
                    <option value="active">Active</option>
                    <option value="archived">Archived</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-gray-800 flex items-center justify-end gap-3">
              <button
                onClick={() => setIsEditModalOpen(false)}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveQuestion}
                disabled={editSaving}
                className="px-4 py-2 text-sm bg-[#4169E1] text-white rounded-lg hover:bg-[#4169E1]/80 disabled:opacity-50 flex items-center gap-2"
              >
                {editSaving && (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                )}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
