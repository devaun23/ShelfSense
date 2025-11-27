'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui';

interface StudyMode {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  defaults: {
    target_count?: number;
    time_limit_seconds?: number;
    difficulty?: string;
  };
}

const STUDY_MODES: StudyMode[] = [
  {
    id: 'practice',
    name: 'Practice Mode',
    description: 'Free-form study with immediate feedback. No time limit.',
    icon: '📚',
    color: 'from-blue-500 to-blue-600',
    defaults: { difficulty: 'adaptive' }
  },
  {
    id: 'timed',
    name: 'Timed Test',
    description: 'Simulate real exam conditions. 40 questions in 60 minutes.',
    icon: '⏱️',
    color: 'from-red-500 to-red-600',
    defaults: { target_count: 40, time_limit_seconds: 3600, difficulty: 'adaptive' }
  },
  {
    id: 'tutor',
    name: 'Tutor Mode',
    description: 'Detailed explanations and hints after each question.',
    icon: '🎓',
    color: 'from-green-500 to-green-600',
    defaults: { target_count: 20, difficulty: 'adaptive' }
  },
  {
    id: 'challenge',
    name: 'Challenge Mode',
    description: 'Hard questions only. No hints. Test your limits.',
    icon: '🔥',
    color: 'from-orange-500 to-orange-600',
    defaults: { target_count: 20, difficulty: 'hard' }
  },
  {
    id: 'review',
    name: 'Review Mode',
    description: 'Spaced repetition review of questions you\'ve seen.',
    icon: '🔄',
    color: 'from-purple-500 to-purple-600',
    defaults: {}
  },
  {
    id: 'weak_focus',
    name: 'Weak Areas',
    description: 'Focus on specialties where you need improvement.',
    icon: '🎯',
    color: 'from-yellow-500 to-yellow-600',
    defaults: { target_count: 30, difficulty: 'adaptive' }
  }
];

const SPECIALTIES = [
  'All Specialties',
  'Internal Medicine',
  'Surgery',
  'Pediatrics',
  'Psychiatry',
  'OB/GYN',
  'Family Medicine',
  'Emergency Medicine',
  'Preventive Medicine'
];

interface StudyModeSelectorProps {
  userId: string;
  onSessionStart?: (sessionId: string) => void;
  onClose?: () => void;
}

export default function StudyModeSelector({ userId, onSessionStart, onClose }: StudyModeSelectorProps) {
  const router = useRouter();
  const [selectedMode, setSelectedMode] = useState<string | null>(null);
  const [specialty, setSpecialty] = useState('All Specialties');
  const [questionCount, setQuestionCount] = useState<number>(20);
  const [timeLimit, setTimeLimit] = useState<number>(60);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  const selectedModeData = STUDY_MODES.find(m => m.id === selectedMode);

  // Store previously focused element and focus close button on mount
  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement;
    closeButtonRef.current?.focus();

    return () => {
      // Restore focus when modal closes
      previousActiveElement.current?.focus();
    };
  }, []);

  // Handle ESC key to close modal
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && onClose) {
      onClose();
    }

    // Focus trap
    if (e.key === 'Tab' && modalRef.current) {
      const focusableElements = modalRef.current.querySelectorAll(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
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
  }, [onClose]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [handleKeyDown]);

  const handleStartSession = async () => {
    if (!selectedMode) return;

    setLoading(true);
    setError(null);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const body: Record<string, unknown> = {
        mode: selectedMode,
        specialty: specialty === 'All Specialties' ? null : specialty,
      };

      // Add mode-specific settings
      if (selectedMode === 'timed') {
        body.target_count = questionCount;
        body.time_limit_minutes = timeLimit;
      } else if (selectedMode !== 'review') {
        body.target_count = questionCount;
      }

      const response = await fetch(
        `${API_URL}/api/study-modes/sessions/start?user_id=${userId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to start session');
      }

      const session = await response.json();

      if (onSessionStart) {
        onSessionStart(session.id);
      }

      // Navigate to study page with session
      router.push(`/study?mode=${selectedMode}&session=${session.id}`);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start session');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="study-mode-title"
      aria-describedby="study-mode-description"
      onClick={(e) => e.target === e.currentTarget && onClose?.()}
    >
      <div
        ref={modalRef}
        className="bg-zinc-900 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-zinc-800"
      >
        {/* Header */}
        <div className="p-6 border-b border-zinc-800 flex justify-between items-center">
          <div>
            <h2 id="study-mode-title" className="text-2xl font-bold text-white">Select Study Mode</h2>
            <p id="study-mode-description" className="text-zinc-400 mt-1">Choose how you want to study today</p>
          </div>
          {onClose && (
            <button
              ref={closeButtonRef}
              onClick={onClose}
              className="text-zinc-400 hover:text-white p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close modal"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Mode Selection Grid */}
        <div className="p-6">
          <fieldset>
            <legend className="sr-only">Select a study mode</legend>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4" role="radiogroup" aria-label="Study modes">
              {STUDY_MODES.map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => setSelectedMode(mode.id)}
                  className={`p-4 rounded-xl border-2 transition-all text-left focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-zinc-900 ${
                    selectedMode === mode.id
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-zinc-700 hover:border-zinc-500 bg-zinc-800/50'
                  }`}
                  role="radio"
                  aria-checked={selectedMode === mode.id}
                  aria-describedby={`mode-desc-${mode.id}`}
                >
                  <div className="text-3xl mb-2" aria-hidden="true">{mode.icon}</div>
                  <h3 className="text-white font-semibold">{mode.name}</h3>
                  <p id={`mode-desc-${mode.id}`} className="text-zinc-400 text-sm mt-1">{mode.description}</p>
                </button>
              ))}
            </div>
          </fieldset>
        </div>

        {/* Configuration Panel */}
        {selectedMode && (
          <div className="p-6 border-t border-zinc-800">
            <h3 className="text-lg font-semibold text-white mb-4">Configure Session</h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Specialty Selection */}
              <div>
                <label htmlFor="specialty-select" className="block text-sm text-zinc-400 mb-2">Specialty</label>
                <select
                  id="specialty-select"
                  value={specialty}
                  onChange={(e) => setSpecialty(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {SPECIALTIES.map((spec) => (
                    <option key={spec} value={spec}>{spec}</option>
                  ))}
                </select>
              </div>

              {/* Question Count (not for review mode) */}
              {selectedMode !== 'review' && (
                <div>
                  <label htmlFor="question-count-select" className="block text-sm text-zinc-400 mb-2">Questions</label>
                  <select
                    id="question-count-select"
                    value={questionCount}
                    onChange={(e) => setQuestionCount(Number(e.target.value))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={10}>10 questions</option>
                    <option value={20}>20 questions</option>
                    <option value={30}>30 questions</option>
                    <option value={40}>40 questions</option>
                    <option value={50}>50 questions</option>
                  </select>
                </div>
              )}

              {/* Time Limit (only for timed mode) */}
              {selectedMode === 'timed' && (
                <div>
                  <label htmlFor="time-limit-select" className="block text-sm text-zinc-400 mb-2">Time Limit</label>
                  <select
                    id="time-limit-select"
                    value={timeLimit}
                    onChange={(e) => setTimeLimit(Number(e.target.value))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={30}>30 minutes</option>
                    <option value={45}>45 minutes</option>
                    <option value={60}>60 minutes</option>
                    <option value={90}>90 minutes</option>
                    <option value={120}>120 minutes</option>
                  </select>
                </div>
              )}
            </div>

            {/* Mode-specific info */}
            {selectedModeData && (
              <div className={`mt-4 p-4 rounded-lg bg-gradient-to-r ${selectedModeData.color} bg-opacity-10`}>
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{selectedModeData.icon}</span>
                  <div>
                    <h4 className="text-white font-semibold">{selectedModeData.name}</h4>
                    <p className="text-white/80 text-sm">{selectedModeData.description}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="mt-4 p-3 bg-red-500/20 border border-red-500 rounded-lg text-red-400" role="alert">
                {error}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="p-6 border-t border-zinc-800 flex justify-end gap-4">
          {onClose && (
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
          )}
          <Button
            variant="primary"
            size="lg"
            onClick={handleStartSession}
            disabled={!selectedMode || loading}
            isLoading={loading}
          >
            {loading ? 'Starting...' : 'Start Session'}
          </Button>
        </div>
      </div>
    </div>
  );
}
