'use client';

import React, { useState } from 'react';

interface NBMEScore {
  id: string;
  assessment_type: string;
  assessment_name: string;
  score: number;
  percentile?: number;
  date_taken: string;
  notes?: string;
  created_at: string;
}

interface NBMEInputFormProps {
  userId: string;
  existingScores: NBMEScore[];
  onScoreAdded: (score: NBMEScore) => void;
  onScoreDeleted: (scoreId: string) => void;
}

const ASSESSMENT_OPTIONS = [
  { value: 'nbme-9', type: 'nbme', name: 'NBME 9' },
  { value: 'nbme-10', type: 'nbme', name: 'NBME 10' },
  { value: 'nbme-11', type: 'nbme', name: 'NBME 11' },
  { value: 'nbme-12', type: 'nbme', name: 'NBME 12' },
  { value: 'nbme-13', type: 'nbme', name: 'NBME 13' },
  { value: 'uwsa-1', type: 'uwsa', name: 'UWSA 1' },
  { value: 'uwsa-2', type: 'uwsa', name: 'UWSA 2' },
  { value: 'free120', type: 'free120', name: 'Free 120' },
];

export function NBMEInputForm({
  userId,
  existingScores,
  onScoreAdded,
  onScoreDeleted,
}: NBMEInputFormProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedAssessment, setSelectedAssessment] = useState('');
  const [score, setScore] = useState('');
  const [dateTaken, setDateTaken] = useState('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!selectedAssessment || !score || !dateTaken) {
      setError('Please fill in all required fields');
      return;
    }

    const scoreNum = parseInt(score);
    if (scoreNum < 100 || scoreNum > 300) {
      setError('Score must be between 100 and 300');
      return;
    }

    const selectedOption = ASSESSMENT_OPTIONS.find(o => o.value === selectedAssessment);
    if (!selectedOption) {
      setError('Invalid assessment selected');
      return;
    }

    setIsSubmitting(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${apiUrl}/api/score-predictor/assessments?user_id=${userId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            assessment_type: selectedOption.type,
            assessment_name: selectedOption.name,
            score: scoreNum,
            date_taken: new Date(dateTaken).toISOString(),
            notes: notes || null,
          }),
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to add score');
      }

      const newScore = await response.json();
      onScoreAdded(newScore);

      // Reset form
      setSelectedAssessment('');
      setScore('');
      setDateTaken('');
      setNotes('');
      setIsExpanded(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add score');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (scoreId: string) => {
    if (!confirm('Are you sure you want to delete this score?')) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${apiUrl}/api/score-predictor/assessments/${scoreId}?user_id=${userId}`,
        { method: 'DELETE' }
      );

      if (!response.ok) {
        throw new Error('Failed to delete score');
      }

      onScoreDeleted(scoreId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete score');
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="bg-gray-900/50 rounded-xl border border-gray-800 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">📊</span>
          <span className="font-medium text-white">External Test Scores</span>
          {existingScores.length > 0 && (
            <span className="px-2 py-0.5 bg-[#4169E1]/20 text-[#4169E1] text-xs rounded-full">
              {existingScores.length} score{existingScores.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-800">
          {/* Existing scores list */}
          {existingScores.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Your Scores</p>
              {existingScores.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-white">{s.score}</span>
                    <span className="text-gray-400">{s.assessment_name}</span>
                    <span className="text-xs text-gray-500">{formatDate(s.date_taken)}</span>
                  </div>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="text-gray-500 hover:text-red-400 transition-colors"
                    title="Delete score"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add score form */}
          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Add New Score</p>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Assessment type */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Assessment *</label>
                <select
                  value={selectedAssessment}
                  onChange={(e) => setSelectedAssessment(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-[#4169E1]"
                >
                  <option value="">Select...</option>
                  {ASSESSMENT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Score */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Score (100-300) *</label>
                <input
                  type="number"
                  value={score}
                  onChange={(e) => setScore(e.target.value)}
                  min={100}
                  max={300}
                  placeholder="235"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-[#4169E1]"
                />
              </div>

              {/* Date */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Date Taken *</label>
                <input
                  type="date"
                  value={dateTaken}
                  onChange={(e) => setDateTaken(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-[#4169E1]"
                />
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-xs text-gray-400 mb-1">Notes (optional)</label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g., Struggled with psychiatry section"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-[#4169E1]"
              />
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:w-auto px-6 py-2 bg-[#4169E1] hover:bg-[#4169E1]/90 disabled:bg-gray-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {isSubmitting ? 'Adding...' : 'Add Score'}
            </button>
          </form>

          {/* Help text */}
          <p className="mt-4 text-xs text-gray-500">
            Adding NBME and UWSA scores improves your predicted Step 2 CK score accuracy by combining
            your ShelfSense performance with official practice exam results.
          </p>
        </div>
      )}
    </div>
  );
}

export default NBMEInputForm;
