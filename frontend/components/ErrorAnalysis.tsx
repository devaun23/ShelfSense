'use client';

import { useState, useEffect, useRef, memo } from 'react';

interface ErrorAnalysisData {
  error_type: string;
  error_name: string;
  error_icon: string;
  error_color: string;
  confidence: number;
  explanation: string;
  missed_detail: string;
  correct_reasoning: string;
  coaching_question: string;
  user_acknowledged: boolean;
}

interface ErrorAnalysisProps {
  questionId: string;
  userId: string;
  isCorrect: boolean;
}

// Static color maps extracted to module level (prevents recreation on each render)
const COLOR_MAP = {
  blue: 'border-blue-500/50 bg-blue-900/10',
  yellow: 'border-yellow-500/50 bg-yellow-900/10',
  orange: 'border-orange-500/50 bg-orange-900/10',
  purple: 'border-purple-500/50 bg-purple-900/10',
  red: 'border-red-500/50 bg-red-900/10',
  gray: 'border-gray-500/50 bg-gray-900/10'
} as const;

const TEXT_COLOR_MAP = {
  blue: 'text-blue-400',
  yellow: 'text-yellow-400',
  orange: 'text-orange-400',
  purple: 'text-purple-400',
  red: 'text-red-400',
  gray: 'text-gray-400'
} as const;

// Polling configuration
const INITIAL_POLL_INTERVAL = 500; // Start fast (500ms)
const MAX_POLL_INTERVAL = 3000; // Slow down to 3s max
const MAX_POLL_ATTEMPTS = 20; // Stop after ~30 seconds total

export default memo(function ErrorAnalysis({ questionId, userId, isCorrect }: ErrorAnalysisProps) {
  const [errorData, setErrorData] = useState<ErrorAnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);
  const [pollAttempts, setPollAttempts] = useState(0);

  // Use ref to track if we've successfully fetched data (avoids infinite polling)
  const hasDataRef = useRef(false);
  const pollIntervalRef = useRef(INITIAL_POLL_INTERVAL);

  useEffect(() => {
    // Only load error analysis if question was answered incorrectly
    if (isCorrect) {
      setLoading(false);
      return;
    }

    // Reset state when question changes
    hasDataRef.current = false;
    pollIntervalRef.current = INITIAL_POLL_INTERVAL;
    setPollAttempts(0);

    const loadErrorAnalysis = async () => {
      // Skip if we already have data for this question
      if (hasDataRef.current) return;

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/questions/error-analysis/${questionId}?user_id=${userId}`);

        if (response.ok) {
          const data = await response.json();
          if (data) {
            hasDataRef.current = true;
            setErrorData(data);
            setIsExpanded(true); // Auto-expand on load
            setLoading(false);
            return true;
          }
        }
      } catch (error) {
        console.error('Error loading error analysis:', error);
      }
      return false;
    };

    let timeoutId: NodeJS.Timeout;

    // Adaptive polling with exponential backoff
    const poll = async () => {
      setPollAttempts(prev => prev + 1);

      const success = await loadErrorAnalysis();

      if (!success && !hasDataRef.current && pollAttempts < MAX_POLL_ATTEMPTS) {
        // Exponential backoff: increase interval by 50% each time, cap at max
        pollIntervalRef.current = Math.min(pollIntervalRef.current * 1.5, MAX_POLL_INTERVAL);
        timeoutId = setTimeout(poll, pollIntervalRef.current);
      } else if (pollAttempts >= MAX_POLL_ATTEMPTS) {
        // Give up after max attempts
        setLoading(false);
      }
    };

    // Initial load
    loadErrorAnalysis().then(success => {
      if (!success) {
        // Start polling if initial load didn't succeed
        timeoutId = setTimeout(poll, pollIntervalRef.current);
      }
    });

    // Cleanup
    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [questionId, userId, isCorrect, pollAttempts]);

  const acknowledgeError = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      await fetch(`${apiUrl}/api/questions/acknowledge-error/${questionId}?user_id=${userId}`, {
        method: 'POST'
      });

      if (errorData) {
        setErrorData({ ...errorData, user_acknowledged: true });
      }
    } catch (error) {
      console.error('Error acknowledging:', error);
    }
  };

  // Don't show anything if correct
  if (isCorrect) {
    return null;
  }

  // Show loading state with skeleton shimmer
  if (loading && !errorData) {
    return (
      <div className="border border-gray-700 rounded-lg bg-black/50 p-4 mb-4 overflow-hidden">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#4169E1]"></div>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-gray-400 text-sm">Analyzing your mistake</span>
              <span className="flex gap-1">
                <span className="w-1 h-1 bg-[#4169E1] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-1 h-1 bg-[#4169E1] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-1 h-1 bg-[#4169E1] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </span>
            </div>
            {/* Skeleton preview */}
            <div className="mt-3 space-y-2">
              <div className="h-3 bg-gray-800 rounded animate-pulse w-3/4"></div>
              <div className="h-3 bg-gray-800 rounded animate-pulse w-1/2"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // No error data available yet
  if (!errorData) {
    return null;
  }

  const colorClass = COLOR_MAP[errorData.error_color as keyof typeof COLOR_MAP] || COLOR_MAP.gray;
  const textClass = TEXT_COLOR_MAP[errorData.error_color as keyof typeof TEXT_COLOR_MAP] || TEXT_COLOR_MAP.gray;

  return (
    <div className={`border rounded-lg overflow-hidden mb-4 ${colorClass}`}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{errorData.error_icon}</span>
          <div className="text-left">
            <h3 className={`font-semibold ${textClass}`}>{errorData.error_name}</h3>
            <p className="text-xs text-gray-500">
              {Math.round(errorData.confidence * 100)}% confidence • Click to {isExpanded ? 'collapse' : 'expand'}
            </p>
          </div>
        </div>
        <svg
          className={`w-5 h-5 text-gray-400 motion-safe:transition-transform motion-safe:duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded Content */}
      <div className={`motion-safe:transition-all motion-safe:duration-200 ease-out overflow-hidden ${isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-4 pb-4 space-y-4 border-t border-gray-700/50">
          {/* Why This Happened */}
          <div>
            <h4 className="text-sm font-semibold text-white mb-2 mt-4">💡 Why this happened:</h4>
            <p className="text-sm text-gray-300 leading-relaxed">{errorData.explanation}</p>
          </div>

          {/* What You Missed */}
          {errorData.missed_detail && (
            <div>
              <h4 className="text-sm font-semibold text-white mb-2">🎯 What you missed:</h4>
              <p className="text-sm text-gray-300 leading-relaxed italic">{errorData.missed_detail}</p>
            </div>
          )}

          {/* Correct Reasoning */}
          {errorData.correct_reasoning && (
            <div>
              <h4 className="text-sm font-semibold text-white mb-2">✅ Correct reasoning:</h4>
              <p className="text-sm text-gray-300 leading-relaxed">{errorData.correct_reasoning}</p>
            </div>
          )}

          {/* Coaching Question */}
          {errorData.coaching_question && (
            <div className="bg-[#1E3A5F]/30 border border-[#4169E1]/30 rounded-lg p-3">
              <h4 className="text-sm font-semibold text-[#4169E1] mb-2">🤔 Think about this:</h4>
              <p className="text-sm text-gray-200 leading-relaxed">{errorData.coaching_question}</p>
            </div>
          )}

          {/* Acknowledge Button */}
          {!errorData.user_acknowledged && (
            <div className="pt-2">
              <button
                onClick={acknowledgeError}
                className="w-full px-4 py-2 bg-gradient-to-r from-[#1E3A5F] to-[#2C5282] hover:from-[#2C5282] hover:to-[#3A4F7A] text-white rounded-lg transition-all text-sm font-semibold"
              >
                Got it! I understand my mistake
              </button>
            </div>
          )}

          {errorData.user_acknowledged && (
            <div className="flex items-center gap-2 text-green-400 text-sm pt-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Acknowledged - Keep practicing!</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});
