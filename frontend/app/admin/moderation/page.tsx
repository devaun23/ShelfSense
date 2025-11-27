'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@/contexts/UserContext';

interface ModerationItem {
  id: string;
  question_id: string;
  question_preview: string;
  specialty: string | null;
  status: string;
  priority: number;
  submission_source: string | null;
  submitted_by_email: string | null;
  assigned_to_email: string | null;
  revision_count: number;
  created_at: string;
}

interface ModerationDetail {
  id: string;
  question_id: string;
  question: {
    id: string;
    vignette: string;
    answer_key: string;
    choices: Record<string, string>;
    explanation: any;
    specialty: string | null;
    difficulty_level: string | null;
    content_status: string;
    quality_score: number | null;
  };
  status: string;
  priority: number;
  submission_source: string | null;
  submitted_by_email: string | null;
  assigned_to_email: string | null;
  decision: string | null;
  decision_notes: string | null;
  clinical_accuracy_score: number | null;
  question_clarity_score: number | null;
  distractor_quality_score: number | null;
  explanation_quality_score: number | null;
  revision_requested: boolean;
  revision_notes: string | null;
  revision_count: number;
  created_at: string;
  reviewed_at: string | null;
}

interface ModerationResponse {
  items: ModerationItem[];
  total: number;
  page: number;
  per_page: number;
}

export default function ModerationPage() {
  const { getAccessToken, user } = useUser();
  const [items, setItems] = useState<ModerationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detail view state
  const [selectedItem, setSelectedItem] = useState<ModerationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Decision form state
  const [showDecisionForm, setShowDecisionForm] = useState(false);
  const [decisionType, setDecisionType] = useState<'approve' | 'reject' | 'revise'>('approve');
  const [decisionNotes, setDecisionNotes] = useState('');
  const [revisionNotes, setRevisionNotes] = useState('');
  const [scores, setScores] = useState({
    clinical_accuracy: 0,
    question_clarity: 0,
    distractor_quality: 0,
    explanation_quality: 0,
  });

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const perPage = 20;

  useEffect(() => {
    fetchItems();
  }, [page, statusFilter]);

  const fetchItems = async () => {
    try {
      setLoading(true);
      const token = await getAccessToken();
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
      });
      if (statusFilter) params.append('status', statusFilter);

      const response = await fetch(`${apiUrl}/api/admin/moderation?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to fetch moderation queue');

      const data: ModerationResponse = await response.json();
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const viewItem = async (id: string) => {
    try {
      setDetailLoading(true);
      const token = await getAccessToken();
      const response = await fetch(`${apiUrl}/api/admin/moderation/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to fetch item details');

      const data = await response.json();
      setSelectedItem(data);
      setShowDecisionForm(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setDetailLoading(false);
    }
  };

  const assignToSelf = async () => {
    if (!selectedItem) return;

    try {
      setActionLoading(true);
      const token = await getAccessToken();
      const response = await fetch(`${apiUrl}/api/admin/moderation/${selectedItem.id}/assign`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to assign item');

      await viewItem(selectedItem.id);
      await fetchItems();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setActionLoading(false);
    }
  };

  const submitDecision = async () => {
    if (!selectedItem) return;

    try {
      setActionLoading(true);
      const token = await getAccessToken();

      const body: any = {
        decision: decisionType,
        decision_notes: decisionNotes || null,
      };

      if (scores.clinical_accuracy > 0) body.clinical_accuracy_score = scores.clinical_accuracy;
      if (scores.question_clarity > 0) body.question_clarity_score = scores.question_clarity;
      if (scores.distractor_quality > 0) body.distractor_quality_score = scores.distractor_quality;
      if (scores.explanation_quality > 0) body.explanation_quality_score = scores.explanation_quality;
      if (decisionType === 'revise' && revisionNotes) body.revision_notes = revisionNotes;

      const response = await fetch(`${apiUrl}/api/admin/moderation/${selectedItem.id}/decision`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) throw new Error('Failed to submit decision');

      // Reset form
      setShowDecisionForm(false);
      setDecisionNotes('');
      setRevisionNotes('');
      setScores({ clinical_accuracy: 0, question_clarity: 0, distractor_quality: 0, explanation_quality: 0 });

      await fetchItems();
      setSelectedItem(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setActionLoading(false);
    }
  };

  const totalPages = Math.ceil(total / perPage);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-900/30 text-yellow-400';
      case 'in_review':
        return 'bg-blue-900/30 text-blue-400';
      case 'approved':
        return 'bg-green-900/30 text-green-400';
      case 'rejected':
        return 'bg-red-900/30 text-red-400';
      case 'needs_revision':
        return 'bg-orange-900/30 text-orange-400';
      default:
        return 'bg-gray-800 text-gray-400';
    }
  };

  const getPriorityLabel = (priority: number) => {
    if (priority <= 3) return { label: 'High', color: 'text-red-400' };
    if (priority <= 6) return { label: 'Medium', color: 'text-yellow-400' };
    return { label: 'Low', color: 'text-gray-400' };
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Content Moderation</h1>
        <p className="text-sm text-gray-400">{total} items in queue</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-white focus:outline-none focus:border-[#4169E1]"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="in_review">In Review</option>
          <option value="needs_revision">Needs Revision</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Queue List */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <div className="p-4 border-b border-gray-800">
            <h2 className="font-medium text-white">Review Queue</h2>
          </div>
          <div className="divide-y divide-gray-800 max-h-[600px] overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#4169E1] mx-auto" />
              </div>
            ) : items.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                {statusFilter ? `No ${statusFilter} items` : 'Queue is empty'}
              </div>
            ) : (
              items.map((item) => {
                const priority = getPriorityLabel(item.priority);
                return (
                  <button
                    key={item.id}
                    onClick={() => viewItem(item.id)}
                    className={`w-full p-4 text-left hover:bg-gray-800/50 transition-colors ${
                      selectedItem?.id === item.id ? 'bg-gray-800/50' : ''
                    }`}
                  >
                    <p className="text-sm text-white line-clamp-2 mb-2">
                      {item.question_preview}
                    </p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(item.status)}`}>
                        {item.status.replace('_', ' ')}
                      </span>
                      <span className={`text-xs ${priority.color}`}>
                        P{item.priority} ({priority.label})
                      </span>
                      {item.specialty && (
                        <span className="text-xs text-gray-500">{item.specialty}</span>
                      )}
                      {item.revision_count > 0 && (
                        <span className="text-xs text-orange-400">Rev. {item.revision_count}</span>
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
            <h2 className="font-medium text-white">Review Details</h2>
          </div>
          <div className="p-4 max-h-[600px] overflow-y-auto">
            {detailLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#4169E1]" />
              </div>
            ) : selectedItem ? (
              <div className="space-y-4">
                {/* Status & Actions */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(selectedItem.status)}`}>
                    {selectedItem.status.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-gray-500">Priority: {selectedItem.priority}</span>
                  <div className="flex-1" />
                  {selectedItem.status === 'pending' && (
                    <button
                      onClick={assignToSelf}
                      disabled={actionLoading}
                      className="text-xs px-3 py-1 bg-[#4169E1]/30 text-[#4169E1] rounded hover:bg-[#4169E1]/50"
                    >
                      Assign to Me
                    </button>
                  )}
                  {selectedItem.status === 'in_review' && selectedItem.assigned_to_email === user?.email && (
                    <button
                      onClick={() => setShowDecisionForm(true)}
                      disabled={actionLoading}
                      className="text-xs px-3 py-1 bg-green-900/30 text-green-400 rounded hover:bg-green-900/50"
                    >
                      Make Decision
                    </button>
                  )}
                </div>

                {/* Assignment Info */}
                {selectedItem.assigned_to_email && (
                  <div className="text-xs text-gray-500">
                    Assigned to: <span className="text-white">{selectedItem.assigned_to_email}</span>
                  </div>
                )}

                {/* Revision Notes */}
                {selectedItem.revision_notes && (
                  <div className="bg-orange-900/20 border border-orange-800 rounded p-3">
                    <p className="text-xs text-orange-400 mb-1">Revision Required:</p>
                    <p className="text-sm text-white">{selectedItem.revision_notes}</p>
                  </div>
                )}

                {/* Question Content */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Vignette</p>
                  <p className="text-sm text-white whitespace-pre-wrap">{selectedItem.question?.vignette}</p>
                </div>

                {/* Choices */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Choices</p>
                  <div className="space-y-1">
                    {selectedItem.question?.choices &&
                      Object.entries(selectedItem.question.choices).map(([key, value]) => (
                        <div
                          key={key}
                          className={`p-2 rounded text-sm ${
                            key === selectedItem.question?.answer_key
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
                    <p className="text-white">{selectedItem.question?.specialty || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Difficulty</p>
                    <p className="text-white">{selectedItem.question?.difficulty_level || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Source</p>
                    <p className="text-white">{selectedItem.submission_source || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Submitted By</p>
                    <p className="text-white">{selectedItem.submitted_by_email || 'N/A'}</p>
                  </div>
                </div>

                {/* Decision Form */}
                {showDecisionForm && (
                  <div className="border-t border-gray-800 pt-4 mt-4 space-y-4">
                    <h3 className="text-sm font-medium text-white">Make Decision</h3>

                    {/* Decision Type */}
                    <div className="flex gap-2">
                      {(['approve', 'reject', 'revise'] as const).map((type) => (
                        <button
                          key={type}
                          onClick={() => setDecisionType(type)}
                          className={`flex-1 py-2 text-sm rounded transition-colors ${
                            decisionType === type
                              ? type === 'approve'
                                ? 'bg-green-600 text-white'
                                : type === 'reject'
                                ? 'bg-red-600 text-white'
                                : 'bg-orange-600 text-white'
                              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                          }`}
                        >
                          {type.charAt(0).toUpperCase() + type.slice(1)}
                        </button>
                      ))}
                    </div>

                    {/* Quality Scores */}
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { key: 'clinical_accuracy', label: 'Clinical Accuracy' },
                        { key: 'question_clarity', label: 'Question Clarity' },
                        { key: 'distractor_quality', label: 'Distractor Quality' },
                        { key: 'explanation_quality', label: 'Explanation Quality' },
                      ].map(({ key, label }) => (
                        <div key={key}>
                          <label className="text-xs text-gray-400">{label}</label>
                          <div className="flex gap-1 mt-1">
                            {[1, 2, 3, 4, 5].map((score) => (
                              <button
                                key={score}
                                onClick={() => setScores({ ...scores, [key]: score })}
                                className={`w-8 h-8 text-xs rounded ${
                                  scores[key as keyof typeof scores] === score
                                    ? 'bg-[#4169E1] text-white'
                                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                                }`}
                              >
                                {score}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Decision Notes */}
                    <div>
                      <label className="text-xs text-gray-400">Decision Notes</label>
                      <textarea
                        value={decisionNotes}
                        onChange={(e) => setDecisionNotes(e.target.value)}
                        rows={2}
                        className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm focus:outline-none focus:border-[#4169E1]"
                        placeholder="Optional notes about your decision..."
                      />
                    </div>

                    {/* Revision Notes */}
                    {decisionType === 'revise' && (
                      <div>
                        <label className="text-xs text-gray-400">Revision Instructions *</label>
                        <textarea
                          value={revisionNotes}
                          onChange={(e) => setRevisionNotes(e.target.value)}
                          rows={3}
                          className="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm focus:outline-none focus:border-[#4169E1]"
                          placeholder="Explain what needs to be revised..."
                        />
                      </div>
                    )}

                    {/* Submit Buttons */}
                    <div className="flex gap-2">
                      <button
                        onClick={() => setShowDecisionForm(false)}
                        className="flex-1 py-2 text-sm bg-gray-800 text-gray-300 rounded hover:bg-gray-700"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={submitDecision}
                        disabled={actionLoading || (decisionType === 'revise' && !revisionNotes)}
                        className={`flex-1 py-2 text-sm rounded disabled:opacity-50 ${
                          decisionType === 'approve'
                            ? 'bg-green-600 text-white hover:bg-green-700'
                            : decisionType === 'reject'
                            ? 'bg-red-600 text-white hover:bg-red-700'
                            : 'bg-orange-600 text-white hover:bg-orange-700'
                        }`}
                      >
                        {actionLoading ? 'Submitting...' : `Confirm ${decisionType.charAt(0).toUpperCase() + decisionType.slice(1)}`}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                Select an item to review
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
