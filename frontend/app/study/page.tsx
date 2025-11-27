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
import { SkeletonQuestion, LoadingSpinner } from '@/components/SkeletonLoader';
import { Button } from '@/components/ui';
import EnhancedExplanation from '@/components/EnhancedExplanation';

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

function StudyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading: userLoading } = useUser();
  // Start with sidebar closed on mobile
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768;
    }
    return true;
  });
  const [question, setQuestion] = useState<Question | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [loading, setLoading] = useState(true);
  const [questionCount, setQuestionCount] = useState(0);
  const [expandedChoices, setExpandedChoices] = useState<Set<string>>(new Set());
  const [startTime, setStartTime] = useState<number>(0);
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [nextQuestion, setNextQuestion] = useState<Question | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [authTimeout, setAuthTimeout] = useState(false);
  const [confidenceLevel, setConfidenceLevel] = useState<number | null>(null);

  // Refs for keyboard handler (prevents handler recreation on state changes)
  const questionRef = useRef<Question | null>(null);
  const selectedAnswerRef = useRef<string | null>(null);
  const feedbackRef = useRef<Feedback | null>(null);

  // Keep refs in sync with state
  questionRef.current = question;
  selectedAnswerRef.current = selectedAnswer;
  feedbackRef.current = feedback;

  // Get specialty from URL params
  const specialtyParam = searchParams.get('specialty');
  const currentSpecialty: Specialty | null = specialtyParam
    ? getSpecialtyByApiName(specialtyParam)
    : null;

  const getApiUrl = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    let url = `${apiUrl}/api/questions/random`;
    if (specialtyParam) {
      url += `?specialty=${encodeURIComponent(specialtyParam)}`;
    }
    return url;
  };

  const preloadNextQuestion = async () => {
    try {
      const response = await fetch(getApiUrl());
      if (response.ok) {
        const data = await response.json();
        setNextQuestion(data);
      }
    } catch (error) {
      console.error('Error preloading question:', error);
    }
  };

  const loadNextQuestion = async () => {
    setSelectedAnswer(null);
    setFeedback(null);
    setExpandedChoices(new Set());
    setStartTime(Date.now());
    setConfidenceLevel(null);

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

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user && !question && !error) {
      loadNextQuestion();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, userLoading, router]);

  // Timer update
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
        setSelectedAnswer(currentQuestion.choices[keyIndex]);
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

  const handleSubmit = async () => {
    if (!selectedAnswer || !question || !user) return;

    const timeSpent = Math.floor((Date.now() - startTime) / 1000);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/questions/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: question.id,
          user_id: user.userId,
          user_answer: selectedAnswer,
          time_spent_seconds: timeSpent,
          confidence_level: confidenceLevel,
        }),
      });

      if (response.ok) {
        const data: Feedback = await response.json();
        setFeedback(data);
        setQuestionCount(prev => prev + 1);

        const newExpanded = new Set<string>();
        if (data.correct_answer) {
          newExpanded.add(data.correct_answer);
        }
        if (!data.is_correct && selectedAnswer) {
          newExpanded.add(selectedAnswer);
        }
        setExpandedChoices(newExpanded);

        preloadNextQuestion();
      } else {
        setError('Failed to submit answer. Please try again.');
      }
    } catch (error) {
      console.error('Error submitting answer:', error);
      setError('Network error while submitting.');
    }
  };

  const handleNext = () => {
    loadNextQuestion();
  };

  const handleBackToHome = () => {
    router.push('/');
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
            {/* Loading header */}
            <div className="flex flex-wrap items-center gap-3 mb-6 md:mb-8">
              <LoadingSpinner size="sm" />
              <span className="text-gray-500">
                {userLoading ? 'Verifying session...' : 'Loading question...'}
              </span>
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
          {/* Header with specialty badge and timer */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-6 md:mb-8 text-sm text-gray-600">
            <div className="flex items-center gap-3 md:gap-4">
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
              {currentSpecialty ? (
                <div className={`flex items-center gap-2 px-2.5 md:px-3 py-1 rounded-full ${currentSpecialty.bgColor} ${currentSpecialty.borderColor} border`}>
                  <span>{currentSpecialty.icon}</span>
                  <span className={`text-xs font-medium ${currentSpecialty.color}`}>
                    {currentSpecialty.shortName}
                  </span>
                </div>
              ) : (
                <div className={`flex items-center gap-2 px-2.5 md:px-3 py-1 rounded-full ${FULL_PREP_MODE.bgColor} ${FULL_PREP_MODE.borderColor} border`}>
                  <span>{FULL_PREP_MODE.icon}</span>
                  <span className={`text-xs font-medium ${FULL_PREP_MODE.color}`}>
                    Step 2 CK
                  </span>
                </div>
              )}

              <span className="text-gray-600 text-xs md:text-sm">Q{questionCount + 1}</span>
              {!feedback && elapsedTime > 0 && (
                <span className="text-gray-500 text-xs md:text-sm">
                  {Math.floor(elapsedTime / 60)}:{(elapsedTime % 60).toString().padStart(2, '0')}
                </span>
              )}
            </div>
            {/* Flag button and keyboard hints */}
            <div className="flex items-center gap-3">
              {/* Flag Button - visible when question is answered */}
              {feedback && question && user && (
                <FlagButton
                  questionId={question.id}
                  userId={user.userId}
                  isCorrect={feedback.is_correct}
                />
              )}

              {/* Keyboard hints - hidden on mobile */}
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

          {/* Question Vignette - conversational style */}
          <div className="mb-8">
            <div className="text-lg leading-relaxed text-gray-100 whitespace-pre-wrap">
              {question.vignette}
            </div>
          </div>

          {/* Answer Choices - clean, minimal */}
          <div className="mb-8 space-y-2">
            {question.choices.map((choice, index) => {
              const letter = String.fromCharCode(65 + index);
              const isSelected = selectedAnswer === choice;
              const isExpanded = expandedChoices.has(choice);
              const isCorrectAnswer = feedback && choice === feedback.correct_answer;
              const isUserWrongChoice = feedback && isSelected && !feedback.is_correct;

              let containerClass = 'border border-gray-800 rounded-xl transition-all';
              if (feedback) {
                if (isCorrectAnswer) {
                  containerClass = 'border-2 border-emerald-500/50 bg-emerald-500/5 rounded-xl';
                } else if (isUserWrongChoice) {
                  containerClass = 'border-2 border-red-500/50 bg-red-500/5 rounded-xl';
                } else {
                  containerClass = 'border border-gray-800/50 rounded-xl opacity-60';
                }
              } else if (isSelected) {
                containerClass = 'border-2 border-[#4169E1] bg-[#4169E1]/5 rounded-xl';
              }

              return (
                <div key={index} className={containerClass}>
                  <button
                    onClick={() => !feedback && setSelectedAnswer(choice)}
                    disabled={!!feedback}
                    className="w-full p-4 flex items-start gap-4 text-left"
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
                    {feedback && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          const newExpanded = new Set(expandedChoices);
                          if (isExpanded) {
                            newExpanded.delete(choice);
                          } else {
                            newExpanded.add(choice);
                          }
                          setExpandedChoices(newExpanded);
                        }}
                        className="flex-shrink-0 p-1"
                      >
                        <svg
                          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''} ${
                            isCorrectAnswer ? 'text-emerald-400' : isUserWrongChoice ? 'text-red-400' : 'text-gray-600'
                          }`}
                          fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                    )}
                  </button>

                  {/* Inline Choice Explanation - simplified since EnhancedExplanation shows full details */}
                  {feedback && isExpanded && !isCorrectAnswer && (
                    <div className="px-4 pb-4 pt-2 border-t border-gray-800/50 ml-11">
                      <div className={`text-xs font-medium mb-2 ${
                        isUserWrongChoice ? 'text-red-400' : 'text-gray-500'
                      }`}>
                        {isUserWrongChoice ? 'Your answer' : 'Why not this'}
                      </div>
                      <div className="text-sm text-gray-400 leading-relaxed">
                        {feedback.explanation?.distractor_explanations?.[letter] || 'This choice is incorrect for this patient.'}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Enhanced Explanation */}
          {feedback && feedback.explanation && (
            <div className="mb-6">
              <EnhancedExplanation
                explanation={feedback.explanation as Parameters<typeof EnhancedExplanation>[0]['explanation']}
                correctAnswer={feedback.correct_answer}
                userAnswer={selectedAnswer || ''}
                isCorrect={feedback.is_correct}
                mode="full"
              />
            </div>
          )}

          {/* Error Analysis */}
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
              <Button variant="primary" size="lg" rounded="full" onClick={handleSubmit}>
                Submit
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
        <div className="animate-pulse text-gray-500">Loading...</div>
      </main>
    }>
      <StudyContent />
    </Suspense>
  );
}
