'use client';

import { useState, useEffect } from 'react';

interface FlagButtonProps {
  questionId: string;
  userId: string;
  isCorrect?: boolean;
  attemptId?: string;
  onFlagChange?: (isFlagged: boolean) => void;
}

interface FlagStatus {
  is_flagged: boolean;
  flag_id?: string;
  flag_reason?: string;
  custom_note?: string;
  folder?: string;
  priority?: number;
}

const FLAG_REASONS = [
  { value: 'review_concept', label: 'Review concept' },
  { value: 'tricky_wording', label: 'Tricky wording' },
  { value: 'high_yield', label: 'High yield' },
  { value: 'uncertain', label: 'Uncertain' },
  { value: 'custom', label: 'Other' },
];

export default function FlagButton({
  questionId,
  userId,
  isCorrect,
  attemptId,
  onFlagChange,
}: FlagButtonProps) {
  const [isFlagged, setIsFlagged] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [selectedReason, setSelectedReason] = useState<string | null>(null);
  const [customNote, setCustomNote] = useState('');
  const [priority, setPriority] = useState(1);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Check if question is already flagged
  useEffect(() => {
    const checkFlagStatus = async () => {
      try {
        const response = await fetch(
          `${apiUrl}/api/flagged/check/${questionId}?user_id=${userId}`
        );
        if (response.ok) {
          const data: FlagStatus = await response.json();
          setIsFlagged(data.is_flagged);
          if (data.is_flagged) {
            setSelectedReason(data.flag_reason || null);
            setCustomNote(data.custom_note || '');
            setPriority(data.priority || 1);
          }
        }
      } catch (error) {
        console.error('Error checking flag status:', error);
      }
    };

    if (questionId && userId) {
      checkFlagStatus();
    }
  }, [questionId, userId, apiUrl]);

  const handleFlag = async () => {
    if (loading) return;
    setLoading(true);

    try {
      const response = await fetch(`${apiUrl}/api/flagged/flag?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: questionId,
          flag_reason: selectedReason,
          custom_note: customNote || null,
          attempt_id: attemptId || null,
          flagged_after_correct: isCorrect,
          priority: priority,
        }),
      });

      if (response.ok) {
        setIsFlagged(true);
        setShowMenu(false);
        onFlagChange?.(true);
      }
    } catch (error) {
      console.error('Error flagging question:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUnflag = async () => {
    if (loading) return;
    setLoading(true);

    try {
      const response = await fetch(
        `${apiUrl}/api/flagged/unflag?user_id=${userId}&question_id=${questionId}`,
        { method: 'DELETE' }
      );

      if (response.ok) {
        setIsFlagged(false);
        setSelectedReason(null);
        setCustomNote('');
        setPriority(1);
        onFlagChange?.(false);
      }
    } catch (error) {
      console.error('Error unflagging question:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleMenu = () => {
    if (isFlagged) {
      handleUnflag();
    } else {
      setShowMenu(!showMenu);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={toggleMenu}
        disabled={loading}
        className={`p-2 rounded-lg transition-all ${
          isFlagged
            ? 'bg-amber-500/10 text-amber-400 hover:bg-amber-500/20'
            : 'hover:bg-gray-800 text-gray-500 hover:text-gray-300'
        }`}
        title={isFlagged ? 'Unflag question' : 'Flag for review'}
      >
        {loading ? (
          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg
            className="w-5 h-5"
            fill={isFlagged ? 'currentColor' : 'none'}
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 3v18M3 3h12l-3 4.5 3 4.5H3"
            />
          </svg>
        )}
      </button>

      {/* Flag Menu Dropdown */}
      {showMenu && !isFlagged && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-gray-900 border border-gray-800 rounded-xl shadow-xl z-50">
          <div className="p-4">
            <h3 className="text-sm font-medium text-white mb-3">Flag for Review</h3>

            {/* Reason Selection */}
            <div className="space-y-2 mb-4">
              <label className="text-xs text-gray-500">Reason (optional)</label>
              <div className="flex flex-wrap gap-2">
                {FLAG_REASONS.map((reason) => (
                  <button
                    key={reason.value}
                    onClick={() => setSelectedReason(
                      selectedReason === reason.value ? null : reason.value
                    )}
                    className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                      selectedReason === reason.value
                        ? 'bg-amber-500/20 border-amber-500/50 text-amber-400'
                        : 'border-gray-700 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    {reason.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Priority Selection */}
            <div className="mb-4">
              <label className="text-xs text-gray-500 block mb-2">Priority</label>
              <div className="flex gap-2">
                {[1, 2, 3].map((p) => (
                  <button
                    key={p}
                    onClick={() => setPriority(p)}
                    className={`flex-1 py-1.5 text-xs rounded-lg border transition-colors ${
                      priority === p
                        ? p === 3
                          ? 'bg-red-500/20 border-red-500/50 text-red-400'
                          : p === 2
                          ? 'bg-amber-500/20 border-amber-500/50 text-amber-400'
                          : 'bg-blue-500/20 border-blue-500/50 text-blue-400'
                        : 'border-gray-700 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    {p === 1 ? 'Low' : p === 2 ? 'Medium' : 'High'}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Note */}
            {selectedReason === 'custom' && (
              <div className="mb-4">
                <label className="text-xs text-gray-500 block mb-2">Note</label>
                <textarea
                  value={customNote}
                  onChange={(e) => setCustomNote(e.target.value)}
                  placeholder="Why are you flagging this?"
                  className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gray-600 resize-none"
                  rows={2}
                />
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={() => setShowMenu(false)}
                className="flex-1 px-3 py-2 text-sm text-gray-400 hover:text-white border border-gray-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleFlag}
                disabled={loading}
                className="flex-1 px-3 py-2 text-sm bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 rounded-lg transition-colors"
              >
                {loading ? 'Saving...' : 'Flag'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {showMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowMenu(false)}
        />
      )}
    </div>
  );
}
