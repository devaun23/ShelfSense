'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui';

interface StudyMode {
  id: string;
  name: string;
  description: string;
  detailedDescription: string;
  bestFor: string[];
  features: string[];
  icon: string;
  color: string;
  bgColor: string;
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
    description: 'Free-form study with immediate feedback',
    detailedDescription: 'Study at your own pace with no pressure. Get instant feedback after each question to reinforce learning.',
    bestFor: ['Daily practice', 'Learning new material', 'Building confidence'],
    features: ['Immediate feedback', 'No time limit', 'Adaptive difficulty', 'Full explanations'],
    icon: '📚',
    color: 'text-blue-400',
    bgColor: 'from-blue-500/20 to-blue-600/10',
    defaults: { difficulty: 'adaptive' }
  },
  {
    id: 'timed',
    name: 'Timed Test',
    description: 'Simulate real exam conditions',
    detailedDescription: 'Practice under realistic exam pressure with a countdown timer. Perfect for building test-taking stamina.',
    bestFor: ['Exam preparation', 'Time management practice', 'Self-assessment'],
    features: ['Countdown timer', 'No feedback until end', 'Score at completion', 'Exam-like experience'],
    icon: '⏱️',
    color: 'text-red-400',
    bgColor: 'from-red-500/20 to-red-600/10',
    defaults: { target_count: 40, time_limit_seconds: 3600, difficulty: 'adaptive' }
  },
  {
    id: 'tutor',
    name: 'Tutor Mode',
    description: 'Deep learning with detailed guidance',
    detailedDescription: 'Get comprehensive explanations, clinical pearls, and memory hooks after each question. Ideal for thorough understanding.',
    bestFor: ['Weak topic review', 'Deep understanding', 'First-time learners'],
    features: ['Detailed explanations', 'Clinical pearls', 'Memory hooks', 'Step-by-step reasoning'],
    icon: '🎓',
    color: 'text-green-400',
    bgColor: 'from-green-500/20 to-green-600/10',
    defaults: { target_count: 20, difficulty: 'adaptive' }
  },
  {
    id: 'challenge',
    name: 'Challenge Mode',
    description: 'Hard questions only - test your limits',
    detailedDescription: 'Push yourself with only difficult questions. No hints or aids - just you and the question.',
    bestFor: ['Advanced review', 'Identifying gaps', 'High-yield practice'],
    features: ['Hard questions only', 'No hints', 'Minimal aids', 'Rigorous testing'],
    icon: '🔥',
    color: 'text-orange-400',
    bgColor: 'from-orange-500/20 to-orange-600/10',
    defaults: { target_count: 20, difficulty: 'hard' }
  },
  {
    id: 'review',
    name: 'Review Mode',
    description: 'Spaced repetition for long-term retention',
    detailedDescription: 'Review questions you\'ve previously answered using scientifically-proven spaced repetition algorithms.',
    bestFor: ['Long-term retention', 'Reinforcing weak areas', 'Efficient review'],
    features: ['Spaced repetition', 'Prioritizes mistakes', 'Optimized intervals', 'Memory strengthening'],
    icon: '🔄',
    color: 'text-purple-400',
    bgColor: 'from-purple-500/20 to-purple-600/10',
    defaults: {}
  },
  {
    id: 'weak_focus',
    name: 'Weak Areas',
    description: 'Target your weakest specialties',
    detailedDescription: 'Focus on topics where your performance is lowest. Efficiently improve where you need it most.',
    bestFor: ['Targeted improvement', 'Efficient studying', 'Pre-exam cramming'],
    features: ['Analyzes your stats', 'Targets weak topics', 'Adaptive difficulty', 'Focused practice'],
    icon: '🎯',
    color: 'text-yellow-400',
    bgColor: 'from-yellow-500/20 to-yellow-600/10',
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
  const [hoveredMode, setHoveredMode] = useState<string | null>(null);
  const [specialty, setSpecialty] = useState('All Specialties');
  const [questionCount, setQuestionCount] = useState<number>(20);
  const [timeLimit, setTimeLimit] = useState<number>(60);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  const selectedModeData = STUDY_MODES.find(m => m.id === selectedMode);
  const displayedModeData = selectedModeData || (hoveredMode ? STUDY_MODES.find(m => m.id === hoveredMode) : null);

  // Store previously focused element and focus close button on mount
  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement;
    closeButtonRef.current?.focus();

    return () => {
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
        className="bg-zinc-900 rounded-xl max-w-5xl w-full max-h-[90vh] overflow-y-auto border border-zinc-800"
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

        <div className="flex flex-col lg:flex-row">
          {/* Mode Selection Grid */}
          <div className="p-6 lg:w-1/2">
            <fieldset>
              <legend className="sr-only">Select a study mode</legend>
              <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label="Study modes">
                {STUDY_MODES.map((mode) => (
                  <button
                    key={mode.id}
                    onClick={() => setSelectedMode(mode.id)}
                    onMouseEnter={() => setHoveredMode(mode.id)}
                    onMouseLeave={() => setHoveredMode(null)}
                    onFocus={() => setHoveredMode(mode.id)}
                    onBlur={() => setHoveredMode(null)}
                    className={`p-4 rounded-xl border-2 transition-all text-left focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-zinc-900 ${
                      selectedMode === mode.id
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-zinc-700 hover:border-zinc-500 bg-zinc-800/50'
                    }`}
                    role="radio"
                    aria-checked={selectedMode === mode.id}
                    aria-describedby={`mode-desc-${mode.id}`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl" aria-hidden="true">{mode.icon}</span>
                      <h3 className="text-white font-semibold text-sm">{mode.name}</h3>
                    </div>
                    <p id={`mode-desc-${mode.id}`} className="text-zinc-500 text-xs leading-relaxed">{mode.description}</p>
                  </button>
                ))}
              </div>
            </fieldset>
          </div>

          {/* Mode Details Panel */}
          <div className="p-6 lg:w-1/2 border-t lg:border-t-0 lg:border-l border-zinc-800 bg-zinc-950/50">
            {displayedModeData ? (
              <div className="space-y-5">
                {/* Mode Header */}
                <div className={`p-4 rounded-lg bg-gradient-to-r ${displayedModeData.bgColor}`}>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-3xl">{displayedModeData.icon}</span>
                    <div>
                      <h3 className={`text-lg font-bold ${displayedModeData.color}`}>{displayedModeData.name}</h3>
                      <p className="text-zinc-300 text-sm">{displayedModeData.detailedDescription}</p>
                    </div>
                  </div>
                </div>

                {/* Best For */}
                <div>
                  <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Best For</h4>
                  <div className="flex flex-wrap gap-2">
                    {displayedModeData.bestFor.map((item, i) => (
                      <span key={i} className="px-2.5 py-1 bg-zinc-800 rounded-full text-xs text-zinc-300">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Features */}
                <div>
                  <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Features</h4>
                  <ul className="space-y-1.5">
                    {displayedModeData.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-zinc-400">
                        <svg className={`w-4 h-4 ${displayedModeData.color}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Quick Start Tip */}
                <div className="p-3 bg-zinc-800/50 rounded-lg border border-zinc-700/50">
                  <div className="flex items-start gap-2">
                    <svg className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-xs text-zinc-400">
                      {displayedModeData.id === 'practice' && 'Start with Practice Mode to build a foundation before testing yourself.'}
                      {displayedModeData.id === 'timed' && 'Use 1.5 minutes per question as a benchmark (40 questions = 60 minutes).'}
                      {displayedModeData.id === 'tutor' && 'Take notes on explanations you find particularly helpful.'}
                      {displayedModeData.id === 'challenge' && 'Challenge Mode is best after you\'ve reviewed the basics.'}
                      {displayedModeData.id === 'review' && 'Review Mode uses your answer history to optimize question selection.'}
                      {displayedModeData.id === 'weak_focus' && 'Complete at least 50 questions before Weak Areas can identify patterns.'}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-center py-12">
                <div className="text-zinc-600">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                  </svg>
                  <p className="text-sm">Select or hover over a mode to see details</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Configuration Panel */}
        {selectedMode && (
          <div className="p-6 border-t border-zinc-800">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">Configure Session</h3>

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

            {/* Error Message */}
            {error && (
              <div className="mt-4 p-3 bg-red-500/20 border border-red-500 rounded-lg text-red-400" role="alert">
                {error}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="p-6 border-t border-zinc-800 flex justify-between items-center">
          <p className="text-xs text-zinc-600">
            Press <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-400">ESC</kbd> to close
          </p>
          <div className="flex gap-4">
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
    </div>
  );
}
