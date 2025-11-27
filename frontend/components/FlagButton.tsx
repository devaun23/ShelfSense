'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui';

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

  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const firstFocusableRef = useRef<HTMLButtonElement>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Handle keyboard navigation for dropdown
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!showMenu) return;

    if (e.key === 'Escape') {
      setShowMenu(false);
      triggerRef.current?.focus();
    }

    // Focus trap within menu
    if (e.key === 'Tab' && menuRef.current) {
      const focusableElements = menuRef.current.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0] as HTMLElement;
      const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    }
  }, [showMenu]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Focus first element when menu opens
  useEffect(() => {
    if (showMenu && firstFocusableRef.current) {
      firstFocusableRef.current.focus();
    }
  }, [showMenu]);

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
        ref={triggerRef}
        onClick={toggleMenu}
        disabled={loading}
        className={`p-2 rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-amber-500 ${
          isFlagged
            ? 'bg-amber-500/10 text-amber-400 hover:bg-amber-500/20'
            : 'hover:bg-gray-800 text-gray-500 hover:text-gray-300'
        }`}
        aria-label={isFlagged ? 'Unflag question' : 'Flag for review'}
        aria-expanded={showMenu}
        aria-haspopup="dialog"
      >
        {loading ? (
          <svg className="w-5 h-5 motion-safe:animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
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
            aria-hidden="true"
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
        <div
          ref={menuRef}
          className="absolute right-0 top-full mt-2 w-72 bg-gray-900 border border-gray-800 rounded-xl shadow-xl z-50"
          role="dialog"
          aria-label="Flag question options"
        >
          <div className="p-4">
            <h3 id="flag-menu-title" className="text-sm font-medium text-white mb-3">Flag for Review</h3>

            {/* Reason Selection */}
            <div className="space-y-2 mb-4">
              <span id="reason-label" className="text-xs text-gray-500 block">Reason (optional)</span>
              <div className="flex flex-wrap gap-2" role="group" aria-labelledby="reason-label">
                {FLAG_REASONS.map((reason, index) => (
                  <button
                    key={reason.value}
                    ref={index === 0 ? firstFocusableRef : undefined}
                    onClick={() => setSelectedReason(
                      selectedReason === reason.value ? null : reason.value
                    )}
                    className={`px-2.5 py-1 text-xs rounded-full border transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500 ${
                      selectedReason === reason.value
                        ? 'bg-amber-500/20 border-amber-500/50 text-amber-400'
                        : 'border-gray-700 text-gray-400 hover:border-gray-600'
                    }`}
                    aria-pressed={selectedReason === reason.value}
                  >
                    {reason.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Priority Selection */}
            <div className="mb-4">
              <span id="priority-label" className="text-xs text-gray-500 block mb-2">Priority</span>
              <div className="flex gap-2" role="group" aria-labelledby="priority-label">
                {[1, 2, 3].map((p) => (
                  <button
                    key={p}
                    onClick={() => setPriority(p)}
                    className={`flex-1 py-1.5 text-xs rounded-lg border transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500 ${
                      priority === p
                        ? p === 3
                          ? 'bg-red-500/20 border-red-500/50 text-red-400'
                          : p === 2
                          ? 'bg-amber-500/20 border-amber-500/50 text-amber-400'
                          : 'bg-blue-500/20 border-blue-500/50 text-blue-400'
                        : 'border-gray-700 text-gray-400 hover:border-gray-600'
                    }`}
                    aria-pressed={priority === p}
                  >
                    {p === 1 ? 'Low' : p === 2 ? 'Medium' : 'High'}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Note */}
            {selectedReason === 'custom' && (
              <div className="mb-4">
                <label htmlFor="flag-note" className="text-xs text-gray-500 block mb-2">Note</label>
                <textarea
                  id="flag-note"
                  value={customNote}
                  onChange={(e) => setCustomNote(e.target.value)}
                  placeholder="Why are you flagging this?"
                  className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-amber-500 resize-none"
                  rows={2}
                />
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="flex-1"
                onClick={() => {
                  setShowMenu(false);
                  triggerRef.current?.focus();
                }}
              >
                Cancel
              </Button>
              <Button
                variant="warning"
                size="sm"
                className="flex-1"
                onClick={handleFlag}
                disabled={loading}
                isLoading={loading}
              >
                {loading ? 'Saving...' : 'Flag'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {showMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => {
            setShowMenu(false);
            triggerRef.current?.focus();
          }}
          aria-hidden="true"
        />
      )}
    </div>
  );
}
