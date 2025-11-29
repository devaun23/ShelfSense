'use client';

import { useState, useEffect, Suspense, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import AIChat from '@/components/AIChat';
import ErrorAnalysis from '@/components/ErrorAnalysis';
import QuestionRating from '@/components/QuestionRating';
import FlagButton from '@/components/FlagButton';
import ConfidenceSelector from '@/components/ConfidenceSelector';
import { useUser } from '@/contexts/UserContext';
import { getSpecialtyByApiName, FULL_PREP_MODE, Specialty } from '@/lib/specialties';
import { getRandomEncouragement, getRandomCorrectMessage, getRandomIncorrectMessage } from '@/lib/encouragement';
import { SkeletonQuestion, LoadingSpinner } from '@/components/SkeletonLoader';
import { Button } from '@/components/ui';
import TabbedExplanation from '@/components/TabbedExplanation';

// Dynamically import Sidebar to avoid useSearchParams SSR issues
const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });

interface Question {
  id: string;
  vignette: string;
  choices: string[];
  source: string;
  recency_weight: number;
}

interface StepByStep {
  step: number;
  action: string;
  rationale: string;
}

interface DeepDive {
  pathophysiology: string;
  differential_comparison: string;
  clinical_pearls: string[];
}

interface MemoryHooks {
  analogy: string | null;
  mnemonic: string | null;
  clinical_story: string | null;
}

interface CommonTrap {
  trap: string;
  why_wrong: string;
  correct_thinking: string;
}

interface DifficultyFactors {
  content_difficulty: 'basic' | 'intermediate' | 'advanced';
  reasoning_complexity: 'single_step' | 'multi_step' | 'integration';
  common_error_rate: number;
}

interface Explanation {
  type?: string;
  quick_answer?: string;
  principle?: string;
  clinical_reasoning?: string;
  correct_answer_explanation?: string;
  distractor_explanations?: Record<string, string>;
  educational_objective?: string;
  concept?: string;
  deep_dive?: DeepDive;
  step_by_step?: StepByStep[];
  memory_hooks?: MemoryHooks;
  common_traps?: CommonTrap[];
  related_topics?: string[];
  difficulty_factors?: DifficultyFactors;
}

interface Feedback {
  is_correct: boolean;
  correct_answer: string;
  explanation: Explanation | null;
  source: string;
}

interface StudySession {
  id: string;
  mode: string;
  specialty: string | null;
  target_count: number | null;
  time_limit_seconds: number | null;
  questions_answered: number;
  questions_correct: number;
  status: string;
  started_at: string;
}


function StudyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading: userLoading } = useUser();

  // Start with sidebar closed to avoid hydration mismatch
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Set initial sidebar state after mount
  useEffect(() => {
    setSidebarOpen(window.innerWidth >= 900);
  }, []);

  // Session state (simplified, no mode selection)
  const [session, setSession] = useState<StudySession | null>(null);

  // Question state
  const [question, setQuestion] = useState<Question | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [loading, setLoading] = useState(true);
  const [questionCount, setQuestionCount] = useState(0);
  // Removed expandedChoices - UWorld-style shows explanations always after submit
  const [startTime, setStartTime] = useState<number>(0);
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [nextQuestion, setNextQuestion] = useState<Question | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [authTimeout, setAuthTimeout] = useState(false);
  const [confidenceLevel, setConfidenceLevel] = useState<number | null>(null);

  // Cognitive tracking: capture answer changes and timing
  const [answerHistory, setAnswerHistory] = useState<string[]>([]);
  const [firstClickTime, setFirstClickTime] = useState<number | null>(null);

  // Optimistic UI states for faster perceived performance
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [optimisticFeedback, setOptimisticFeedback] = useState<{ submitted: boolean; answer: string } | null>(null);

  // Warm message state (set once when feedback received)
  const [warmMessage, setWarmMessage] = useState<string>('');

  // Timed mode state
  const [sessionTimeRemaining, setSessionTimeRemaining] = useState<number | null>(null);

  // Refs for keyboard handler (prevents handler recreation on state changes)
  const questionRef = useRef<Question | null>(null);
  const selectedAnswerRef = useRef<string | null>(null);
  const feedbackRef = useRef<Feedback | null>(null);
  const startTimeRef = useRef<number>(0);
  const firstClickTimeRef = useRef<number | null>(null);
  const answerHistoryRef = useRef<string[]>([]);

  // Keep refs in sync with state
  questionRef.current = question;
  selectedAnswerRef.current = selectedAnswer;
  feedbackRef.current = feedback;
  startTimeRef.current = startTime;
  firstClickTimeRef.current = firstClickTime;
  answerHistoryRef.current = answerHistory;

  // Get params from URL
  const specialtyParam = searchParams.get('specialty');
  const sessionParam = searchParams.get('session');

  const currentSpecialty: Specialty | null = specialtyParam
    ? getSpecialtyByApiName(specialtyParam)
    : null;

  // Legacy API URL for backwards compatibility
  const getApiUrl = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    let url = `${apiUrl}/api/questions/random`;
    if (specialtyParam) {
      url += `?specialty=${encodeURIComponent(specialtyParam)}`;
    }
    return url;
  };

  // Session-based question loading
  const loadSessionQuestion = async (sessionId: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${apiUrl}/api/study-modes/sessions/${sessionId}/next`);
      if (response.ok) {
        const data = await response.json();
        if (data.completed) {
          // Session complete - show summary
          router.push(`/study/summary?session=${sessionId}`);
          return null;
        }
        return data.question;
      }
      return null;
    } catch (err) {
      console.error('Error loading session question:', err);
      return null;
    }
  };

  // Load session details
  const loadSession = async (sessionId: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${apiUrl}/api/study-modes/sessions/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        setSession(data);
        setQuestionCount(data.questions_answered || 0);

        // Set up timer for timed mode
        if (data.mode === 'timed' && data.time_limit_seconds && data.started_at) {
          const startedAt = new Date(data.started_at).getTime();
          const elapsed = Math.floor((Date.now() - startedAt) / 1000);
          const remaining = Math.max(0, data.time_limit_seconds - elapsed);
          setSessionTimeRemaining(remaining);
        }

        return data;
      }
      return null;
    } catch (err) {
      console.error('Error loading session:', err);
      return null;
    }
  };

  const preloadNextQuestion = async () => {
    try {
      if (sessionParam) {
        // Session-based preloading - fetch next question in background
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/study-modes/sessions/${sessionParam}/peek`);
        if (response.ok) {
          const data = await response.json();
          if (data && !data.completed) {
            setNextQuestion(data.question);
          }
        }
      } else {
        // Legacy preloading
        const response = await fetch(getApiUrl());
        if (response.ok) {
          const data = await response.json();
          setNextQuestion(data);
        }
      }
    } catch (error) {
      // Silently fail - preloading is an optimization, not critical
      console.debug('Question preload skipped:', error);
    }
  };

  const loadNextQuestion = async () => {
    setSelectedAnswer(null);
    setFeedback(null);
    setOptimisticFeedback(null);
    setStartTime(Date.now());
    setConfidenceLevel(null);
    // Reset cognitive tracking for new question
    setAnswerHistory([]);
    setFirstClickTime(null);

    if (sessionParam) {
      // Session-based loading - use preloaded question if available
      if (nextQuestion) {
        setQuestion(nextQuestion);
        setNextQuestion(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      const q = await loadSessionQuestion(sessionParam);
      if (q) {
        setQuestion(q);
        setError(null);
      }
      setLoading(false);
      return;
    }

    // Legacy loading
    if (nextQuestion) {
      setQuestion(nextQuestion);
      setNextQuestion(null);
      setLoading(false);
      preloadNextQuestion();
    } else {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(getApiUrl());
        if (response.ok) {
          const data = await response.json();
          setQuestion(data);
          setError(null);
          preloadNextQuestion();
        } else if (response.status === 404) {
          setError('No questions available. Please try again later.');
        } else {
          const errorData = await response.json().catch(() => ({}));
          setError(errorData.detail || 'Failed to load question. Please check your connection.');
        }
      } catch (error) {
        console.error('Error loading question:', error);
        setError('Network error. Please check your internet connection.');
      } finally {
        setLoading(false);
      }
    }
  };

  // Auth timeout - if still loading after 10 seconds, show error
  useEffect(() => {
    if (userLoading) {
      const timeout = setTimeout(() => {
        setAuthTimeout(true);
        setLoading(false);
      }, 10000);
      return () => clearTimeout(timeout);
    }
  }, [userLoading]);

  // Initialize study session - go straight to questions, no mode selection
  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      // If we have a session param, load that session
      if (sessionParam) {
        loadSession(sessionParam).then((sess) => {
          if (sess) {
            loadNextQuestion();
          } else {
            setError('Session not found');
            setLoading(false);
          }
        });
      }
      // Otherwise just load questions directly
      else if (!question && !error) {
        loadNextQuestion();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, userLoading, router, sessionParam]);

  // Timer update for current question
  useEffect(() => {
    if (!feedback && startTime > 0) {
      const interval = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setElapsedTime(0);
    }
  }, [startTime, feedback]);

  // Session timer for timed mode
  useEffect(() => {
    if (session?.mode === 'timed' && sessionTimeRemaining !== null && sessionTimeRemaining > 0) {
      const interval = setInterval(() => {
        setSessionTimeRemaining(prev => {
          if (prev === null || prev <= 1) {
            // Time's up - end session
            if (sessionParam) {
              router.push(`/study/summary?session=${sessionParam}`);
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [session?.mode, sessionTimeRemaining, sessionParam, router]);

  // Stable keyboard handler using refs (prevents listener churn)
  const handleKeyPress = useCallback((e: KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
      return;
    }

    const currentQuestion = questionRef.current;
    const currentFeedback = feedbackRef.current;
    const currentSelectedAnswer = selectedAnswerRef.current;

    if (!currentFeedback && currentQuestion) {
      const key = e.key.toUpperCase();
      const validKeys = ['A', 'B', 'C', 'D', 'E'];
      const keyIndex = validKeys.indexOf(key);

      if (keyIndex !== -1 && keyIndex < currentQuestion.choices.length) {
        const choice = currentQuestion.choices[keyIndex];
        // Track first click time using refs
        if (!firstClickTimeRef.current && startTimeRef.current > 0) {
          setFirstClickTime(Date.now() - startTimeRef.current);
        }
        // Track answer history
        setAnswerHistory(prev => [...prev, choice]);
        setSelectedAnswer(choice);
        e.preventDefault();
      }
    }

    if (e.key === 'Enter' && currentSelectedAnswer && !currentFeedback) {
      handleSubmit();
      e.preventDefault();
    }

    if (e.key.toLowerCase() === 'n' && currentFeedback) {
      handleNext();
      e.preventDefault();
    }
  }, []); // Empty deps - uses refs for current values

  // Keyboard navigation
  useEffect(() => {
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [handleKeyPress]);

  // Cognitive tracking: capture answer selection with timing
  const handleAnswerSelect = useCallback((choice: string) => {
    // Track first click time
    if (!firstClickTime && startTime > 0) {
      setFirstClickTime(Date.now() - startTime);
    }
    // Track answer history for detecting vacillation
    setAnswerHistory(prev => [...prev, choice]);
    setSelectedAnswer(choice);
  }, [firstClickTime, startTime]);

  const handleSubmit = async () => {
    if (!selectedAnswer || !question || !user || isSubmitting) return;

    const timeSpent = Math.floor((Date.now() - startTime) / 1000);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    // Build cognitive interaction data
    const interactionData = {
      answer_changes: answerHistory.length > 0 ? answerHistory.length - 1 : 0,
      time_to_first_click_ms: firstClickTime,
      final_answer_time_ms: firstClickTime ? timeSpent * 1000 - firstClickTime : null,
      answer_history: answerHistory,
    };

    // Optimistic UI: immediately show submission state
    setIsSubmitting(true);
    setOptimisticFeedback({ submitted: true, answer: selectedAnswer });

    try {
      // Use session-based submit if we have a session
      if (sessionParam) {
        const response = await fetch(`${apiUrl}/api/study-modes/sessions/${sessionParam}/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question_id: question.id,
            answer: selectedAnswer,
            time_spent_seconds: timeSpent,
            confidence_level: confidenceLevel,
            interaction_data: interactionData,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          setFeedback({
            is_correct: data.is_correct,
            correct_answer: data.correct_answer,
            explanation: data.explanation,
            source: question.source,
          });
          setQuestionCount(prev => prev + 1);
          // Set warm message based on correctness
          setWarmMessage(data.is_correct ? getRandomCorrectMessage() : getRandomIncorrectMessage());

          // Preload next question while user reviews feedback
          preloadNextQuestion();
        } else {
          setOptimisticFeedback(null);
          setError('Failed to submit answer. Please try again.');
        }
      } else {
        // Legacy submit
        const response = await fetch(`${apiUrl}/api/questions/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question_id: question.id,
            user_id: user.userId,
            user_answer: selectedAnswer,
            time_spent_seconds: timeSpent,
            confidence_level: confidenceLevel,
            interaction_data: interactionData,
          }),
        });

        if (response.ok) {
          const data: Feedback = await response.json();
          setFeedback(data);
          setQuestionCount(prev => prev + 1);
          // Set warm message based on correctness
          setWarmMessage(data.is_correct ? getRandomCorrectMessage() : getRandomIncorrectMessage());

          preloadNextQuestion();
        } else {
          setOptimisticFeedback(null);
          setError('Failed to submit answer. Please try again.');
        }
      }
    } catch (error) {
      console.error('Error submitting answer:', error);
      setOptimisticFeedback(null);
      setError('Network error while submitting.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNext = () => {
    setWarmMessage(''); // Reset warm message for next question
    loadNextQuestion();
  };

  const handleBackToHome = () => {
    router.push('/');
  };

  // Format time for display
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Auth timeout - show connection error
  if (authTimeout) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="flex flex-col items-center justify-center min-h-screen gap-4 px-4">
            <p className="text-red-400 text-center">Connection issue - unable to verify your session</p>
            <p className="text-gray-500 text-sm text-center">Please check your internet connection and try again.</p>
            <Button variant="secondary" size="md" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </main>
      </>
    );
  }

  if (loading) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="max-w-3xl mx-auto px-4 md:px-6 py-6 md:py-8 pt-14 md:pt-16 pb-24 md:pb-32">
            {/* Loading header with encouragement */}
            <div className="flex flex-col items-center gap-4 mb-6 md:mb-8">
              <LoadingSpinner size="sm" />
              <p
                className="text-gray-400 text-center text-sm max-w-md"
                style={{ fontFamily: 'var(--font-serif)' }}
              >
                {userLoading ? 'Verifying session...' : getRandomEncouragement()}
              </p>
            </div>
            <SkeletonQuestion />
          </div>
        </main>
      </>
    );
  }

  if (!question) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="flex flex-col items-center justify-center min-h-screen gap-4 px-4">
            <p className="text-gray-400 text-center">{error || 'No questions available'}</p>
            <div className="flex gap-3">
              <Button variant="secondary" size="md" onClick={() => { setError(null); loadNextQuestion(); }}>
                Try Again
              </Button>
              <Button variant="ghost" size="md" onClick={handleBackToHome}>
                ← Back to Home
              </Button>
            </div>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        {/* Centered content container - Claude style */}
        <div className="max-w-3xl mx-auto px-4 md:px-6 py-6 md:py-8 pt-14 md:pt-16 pb-24 md:pb-32">
          {/* Minimal header */}
          <div className="flex items-center justify-between mb-6 md:mb-8 text-sm">
            <div className="flex items-center gap-3">
              {/* Back button */}
              <button
                onClick={handleBackToHome}
                className="p-1.5 hover:bg-gray-900 rounded-lg transition-colors"
                title="Back to Home"
              >
                <svg className="w-4 h-4 text-gray-500 hover:text-gray-300" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </button>

              {/* Specialty Badge */}
              <span className="text-gray-400 text-sm" style={{ fontFamily: 'var(--font-serif)' }}>
                {currentSpecialty ? currentSpecialty.name : 'Step 2 CK'}
              </span>

              {/* Question counter */}
              <span className="text-gray-600 text-sm">
                Q{questionCount + 1}
              </span>
            </div>

            {/* Right side */}
            <div className="flex items-center gap-3">
              {/* Flag Button */}
              {feedback && question && user && (
                <FlagButton
                  questionId={question.id}
                  userId={user.userId}
                  isCorrect={feedback.is_correct}
                />
              )}

              {/* Keyboard hints */}
              <div className="hidden md:flex gap-3 text-xs text-gray-700">
                {!feedback && (
                  <>
                    <span><kbd className="px-1.5 py-0.5 bg-gray-900 rounded text-gray-500">A-E</kbd></span>
                    <span><kbd className="px-1.5 py-0.5 bg-gray-900 rounded text-gray-500">Enter</kbd></span>
                  </>
                )}
                {feedback && (
                  <span><kbd className="px-1.5 py-0.5 bg-gray-900 rounded text-gray-500">N</kbd> next</span>
                )}
              </div>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-6 p-4 bg-red-900/20 border border-red-900/50 rounded-lg text-red-400 text-sm">
              {error}
              <button
                onClick={() => { setError(null); loadNextQuestion(); }}
                className="ml-3 underline hover:no-underline"
              >
                Try again
              </button>
            </div>
          )}

          {/* Question Vignette - UWorld-style serif typography */}
          <div className="mb-8">
            <div className="vignette whitespace-pre-wrap">
              {question.vignette}
            </div>
          </div>

          {/* Answer Choices - UWorld-style with proper spacing */}
          <div className="mb-8 space-y-4">
            {question.choices.map((choice, index) => {
              const letter = String.fromCharCode(65 + index);
              const isSelected = selectedAnswer === choice;
              const isCorrectAnswer = feedback && choice === feedback.correct_answer;
              const isUserWrongChoice = feedback && isSelected && !feedback.is_correct;
              const isOptimisticSelected = optimisticFeedback?.answer === choice;

              let containerClass = 'border border-gray-800 rounded-xl transition-all duration-200';
              if (feedback) {
                if (isCorrectAnswer) {
                  containerClass = 'border-2 border-emerald-500/50 bg-emerald-500/5 rounded-xl animate-in fade-in duration-300';
                } else if (isUserWrongChoice) {
                  containerClass = 'border-2 border-red-500/50 bg-red-500/5 rounded-xl animate-in fade-in duration-300';
                } else {
                  containerClass = 'border border-gray-800/50 rounded-xl opacity-60';
                }
              } else if (isOptimisticSelected && isSubmitting) {
                // Optimistic: show selected answer with pulse while waiting
                containerClass = 'border-2 border-[#4169E1] bg-[#4169E1]/10 rounded-xl animate-pulse';
              } else if (isSelected) {
                containerClass = 'border-2 border-[#4169E1] bg-[#4169E1]/5 rounded-xl';
              }

              return (
                <div key={index} className={containerClass}>
                  <button
                    onClick={() => !feedback && handleAnswerSelect(choice)}
                    disabled={!!feedback}
                    className="w-full px-5 py-4 flex items-start gap-4 text-left hover:bg-gray-900/30 transition-colors"
                  >
                    <span className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-medium ${
                      feedback
                        ? isCorrectAnswer
                          ? 'bg-emerald-500 text-white'
                          : isUserWrongChoice
                            ? 'bg-red-500 text-white'
                            : 'bg-gray-800 text-gray-500'
                        : isSelected
                          ? 'bg-[#4169E1] text-white'
                          : 'bg-gray-900 text-gray-400'
                    }`}>
                      {letter}
                    </span>
                    <span className={`flex-1 ${
                      feedback && !isCorrectAnswer && !isUserWrongChoice ? 'text-gray-500' : 'text-gray-200'
                    }`}>
                      {choice}
                    </span>
                    {/* Status indicator for feedback */}
                    {feedback && (
                      <span className="flex-shrink-0">
                        {isCorrectAnswer ? (
                          <svg className="w-5 h-5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        ) : isUserWrongChoice ? (
                          <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                          </svg>
                        ) : null}
                      </span>
                    )}
                  </button>

                  {/* UWorld-style Inline Explanation - visible immediately after submit */}
                  {feedback && !isCorrectAnswer && feedback.explanation?.distractor_explanations?.[letter] && (
                    <div className="px-4 pb-4 pt-2 border-t border-gray-800/50 ml-11">
                      <div className={`text-xs font-medium mb-1 ${
                        isUserWrongChoice ? 'text-red-400' : 'text-gray-500'
                      }`}>
                        {isUserWrongChoice ? 'Why your answer is incorrect' : 'Why not this option'}
                      </div>
                      <div className="text-sm text-gray-400 leading-relaxed">
                        {feedback.explanation.distractor_explanations[letter]}
                      </div>
                    </div>
                  )}
                  {/* Show correct answer explanation inline */}
                  {feedback && isCorrectAnswer && feedback.explanation?.correct_answer_explanation && (
                    <div className="px-4 pb-4 pt-2 border-t border-emerald-800/30 ml-11">
                      <div className="text-xs font-medium mb-1 text-emerald-400">
                        Why this is correct
                      </div>
                      <div className="text-sm text-gray-300 leading-relaxed">
                        {feedback.explanation.correct_answer_explanation}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Warm message after answer */}
          {feedback && warmMessage && (
            <p
              className={`text-sm mb-4 ${feedback.is_correct ? 'text-emerald-400/80' : 'text-gray-400'}`}
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              {warmMessage}
            </p>
          )}

          {/* Tabbed Explanation */}
          {feedback && feedback.explanation && (
            <div className="mb-6">
              <TabbedExplanation
                explanation={feedback.explanation}
                correctAnswer={feedback.correct_answer}
                userAnswer={selectedAnswer ? String.fromCharCode(65 + question.choices.indexOf(selectedAnswer)) : ''}
                isCorrect={feedback.is_correct}
                choices={question.choices}
              />
            </div>
          )}

          {feedback && question && user && (
            <ErrorAnalysis
              questionId={question.id}
              userId={user.userId}
              isCorrect={feedback.is_correct}
            />
          )}

          {/* AI Chat */}
          {feedback && question && user && (
            <div className="mb-6">
              <AIChat
                questionId={question.id}
                userId={user.userId}
                isCorrect={feedback.is_correct}
                userAnswer={selectedAnswer || ''}
              />
            </div>
          )}

          {/* Confidence Selector & Action Button */}
          <div className="flex flex-col items-center gap-4">
            {/* Confidence selector - appears after selecting an answer */}
            {!feedback && selectedAnswer && (
              <ConfidenceSelector
                value={confidenceLevel}
                onChange={setConfidenceLevel}
                disabled={!!feedback}
              />
            )}

            {!feedback && selectedAnswer && (
              <Button
                variant="primary"
                size="lg"
                rounded="full"
                onClick={handleSubmit}
                disabled={isSubmitting}
                className={isSubmitting ? 'opacity-80' : ''}
              >
                {isSubmitting ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Checking...
                  </span>
                ) : (
                  'Submit'
                )}
              </Button>
            )}

            {feedback && (
              <Button variant="secondary" size="lg" rounded="full" onClick={handleNext}>
                Continue
              </Button>
            )}
          </div>
        </div>

        {/* Question Rating */}
        {feedback && question && user && (
          <QuestionRating
            questionId={question.id}
            userId={user.userId}
            onRatingComplete={handleNext}
          />
        )}
      </main>
    </>
  );
}

// Wrap in Suspense for useSearchParams
export default function StudyPage() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </main>
    }>
      <StudyContent />
    </Suspense>
  );
}
