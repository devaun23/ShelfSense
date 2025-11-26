'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

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

  const selectedModeData = STUDY_MODES.find(m => m.id === selectedMode);

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
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-zinc-800">
        {/* Header */}
        <div className="p-6 border-b border-zinc-800 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-white">Select Study Mode</h2>
            <p className="text-zinc-400 mt-1">Choose how you want to study today</p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="text-zinc-400 hover:text-white p-2"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Mode Selection Grid */}
        <div className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {STUDY_MODES.map((mode) => (
              <button
                key={mode.id}
                onClick={() => setSelectedMode(mode.id)}
                className={`p-4 rounded-xl border-2 transition-all text-left ${
                  selectedMode === mode.id
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-zinc-700 hover:border-zinc-500 bg-zinc-800/50'
                }`}
              >
                <div className="text-3xl mb-2">{mode.icon}</div>
                <h3 className="text-white font-semibold">{mode.name}</h3>
                <p className="text-zinc-400 text-sm mt-1">{mode.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Configuration Panel */}
        {selectedMode && (
          <div className="p-6 border-t border-zinc-800">
            <h3 className="text-lg font-semibold text-white mb-4">Configure Session</h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Specialty Selection */}
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Specialty</label>
                <select
                  value={specialty}
                  onChange={(e) => setSpecialty(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white"
                >
                  {SPECIALTIES.map((spec) => (
                    <option key={spec} value={spec}>{spec}</option>
                  ))}
                </select>
              </div>

              {/* Question Count (not for review mode) */}
              {selectedMode !== 'review' && (
                <div>
                  <label className="block text-sm text-zinc-400 mb-2">Questions</label>
                  <select
                    value={questionCount}
                    onChange={(e) => setQuestionCount(Number(e.target.value))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white"
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
                  <label className="block text-sm text-zinc-400 mb-2">Time Limit</label>
                  <select
                    value={timeLimit}
                    onChange={(e) => setTimeLimit(Number(e.target.value))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white"
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
              <div className="mt-4 p-3 bg-red-500/20 border border-red-500 rounded-lg text-red-400">
                {error}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="p-6 border-t border-zinc-800 flex justify-end gap-4">
          {onClose && (
            <button
              onClick={onClose}
              className="px-6 py-2 text-zinc-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
          )}
          <button
            onClick={handleStartSession}
            disabled={!selectedMode || loading}
            className={`px-8 py-3 rounded-lg font-semibold transition-all ${
              selectedMode && !loading
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
            }`}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Starting...
              </span>
            ) : (
              'Start Session'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
