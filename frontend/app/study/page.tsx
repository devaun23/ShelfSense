'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ProgressBar from '@/components/ProgressBar';
import Sidebar from '@/components/Sidebar';
import AIChat from '@/components/AIChat';
import QuestionRating from '@/components/QuestionRating';
import { useUser } from '@/contexts/UserContext';

interface Question {
  id: string;
  vignette: string;
  choices: string[];
  source: string;
  recency_weight: number;
}

interface Explanation {
  type?: string;
  principle?: string;
  clinical_reasoning?: string;
  correct_answer_explanation?: string;
  distractor_explanations?: Record<string, string>;
  educational_objective?: string;
  concept?: string;
}

interface Feedback {
  is_correct: boolean;
  correct_answer: string;
  explanation: Explanation | null;
  source: string;
}

export default function StudyPage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [question, setQuestion] = useState<Question | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [loading, setLoading] = useState(true);
  const [questionCount, setQuestionCount] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [queueStats, setQueueStats] = useState({ completed: 0, queueSize: 10 });
  const [expandedChoices, setExpandedChoices] = useState<Set<string>>(new Set());
  const [startTime, setStartTime] = useState<number>(0);
  const [nextQuestion, setNextQuestion] = useState<Question | null>(null);

  const preloadNextQuestion = async () => {
    // Silently pre-load the next question in the background
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/questions/random`);
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

    // If we have a pre-loaded question, use it instantly
    if (nextQuestion) {
      setQuestion(nextQuestion);
      setNextQuestion(null);
      setLoading(false);
      // Start pre-loading the NEXT question
      preloadNextQuestion();
    } else {
      // Fallback: load synchronously
      setLoading(true);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/questions/random`);
        if (response.ok) {
          const data = await response.json();
          setQuestion(data);
          // Start pre-loading for next time
          preloadNextQuestion();
        }
      } catch (error) {
        console.error('Error loading question:', error);
      } finally {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    // Load first question and queue stats only if user is authenticated
    if (user && !question) {
      loadNextQuestion();
      loadQueueStats();
    }
  }, [user, userLoading, router]);

  const loadQueueStats = async () => {
    if (!user) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/analytics/stats?user_id=${user.userId}`);
      if (response.ok) {
        const data = await response.json();

        // Adaptive queue logic
        const completed = data.total_attempts || 0;
        const incorrectCount = data.incorrect_count || 0;

        let queueSize = 10;
        if (incorrectCount > 0) {
          queueSize = Math.min(10 + (incorrectCount * 2), 50);
        }

        setQueueStats({
          completed: completed,
          queueSize: queueSize
        });
      }
    } catch (error) {
      console.error('Error loading queue stats:', error);
    }
  };

  const handleSubmit = async () => {
    if (!selectedAnswer || !question || !user) return;

    const timeSpent = Math.floor((Date.now() - startTime) / 1000);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/questions/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question_id: question.id,
          user_id: user.userId,
          user_answer: selectedAnswer,
          time_spent_seconds: timeSpent,
        }),
      });

      if (response.ok) {
        const data: Feedback = await response.json();
        setFeedback(data);
        setQuestionCount(prev => prev + 1);
        if (data.is_correct) {
          setCorrectCount(prev => prev + 1);
        }
        // Update queue stats after answering
        loadQueueStats();
      }
    } catch (error) {
      console.error('Error submitting answer:', error);
    }
  };

  const handleNext = () => {
    loadNextQuestion();
  };

  const progress = questionCount > 0 ? (questionCount / 1994) * 100 : 0;

  if (loading) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="flex items-center justify-center min-h-screen">
            {/* Solid white gear icon */}
            <svg
              className="animate-spin h-16 w-16 text-white"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M12 2C11.172 2 10.5 2.672 10.5 3.5V5.145C9.419 5.408 8.414 5.877 7.536 6.514L6.379 5.357C5.793 4.771 4.843 4.771 4.257 5.357C3.671 5.943 3.671 6.893 4.257 7.479L5.414 8.636C4.777 9.514 4.308 10.519 4.045 11.6H2.5C1.672 11.6 1 12.272 1 13.1C1 13.928 1.672 14.6 2.5 14.6H4.145C4.408 15.681 4.877 16.686 5.514 17.564L4.357 18.721C3.771 19.307 3.771 20.257 4.357 20.843C4.943 21.429 5.893 21.429 6.479 20.843L7.636 19.686C8.514 20.323 9.519 20.792 10.6 21.055V22.5C10.6 23.328 11.272 24 12.1 24C12.928 24 13.6 23.328 13.6 22.5V20.855C14.681 20.592 15.686 20.123 16.564 19.486L17.721 20.643C18.307 21.229 19.257 21.229 19.843 20.643C20.429 20.057 20.429 19.107 19.843 18.521L18.686 17.364C19.323 16.486 19.792 15.481 20.055 14.4H21.5C22.328 14.4 23 13.728 23 12.9C23 12.072 22.328 11.4 21.5 11.4H19.855C19.592 10.319 19.123 9.314 18.486 8.436L19.643 7.279C20.229 6.693 20.229 5.743 19.643 5.157C19.057 4.571 18.107 4.571 17.521 5.157L16.364 6.314C15.486 5.677 14.481 5.208 13.4 4.945V3.5C13.4 2.672 12.728 2 11.9 2H12ZM12 8C14.209 8 16 9.791 16 12C16 14.209 14.209 16 12 16C9.791 16 8 14.209 8 12C8 9.791 9.791 8 12 8Z" />
            </svg>
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
          <div className="flex items-center justify-center min-h-screen">
            <p className="text-gray-400">No questions available</p>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      {/* Progress bar only appears during questions */}
      <ProgressBar progress={progress} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        <div className="flex flex-col mx-auto px-8 py-6 pt-16 pb-32" style={{ maxWidth: sidebarOpen ? '1200px' : '1400px' }}>
          {/* Stats bar */}
          <div className="flex justify-end items-center gap-6 text-base mb-4 flex-shrink-0">
            <div>
              <span className="text-gray-500 font-semibold">Queue: </span>
              <span className="text-white font-bold">{queueStats.queueSize}</span>
            </div>
            <div>
              <span className="text-gray-500 font-semibold">Completed: </span>
              <span className="text-white font-bold">{queueStats.completed}</span>
            </div>
          </div>

          {/* Question Vignette - Slightly smaller for balance */}
          <div className="mb-6 flex-shrink border-b border-gray-800 pb-6">
            <p className="text-xl leading-relaxed whitespace-pre-wrap font-semibold">
              {question.vignette}
            </p>
          </div>

          {/* Answer Choices - dropdown style with separators */}
          <div className="mb-6 flex-shrink-0 border border-gray-700 rounded-lg divide-y divide-gray-700">
            {question.choices.map((choice, index) => {
              const letter = String.fromCharCode(65 + index);
              const isSelected = selectedAnswer === choice;
              const isExpanded = expandedChoices.has(choice);
              const isCorrectAnswer = feedback && choice === feedback.correct_answer;
              const isUserWrongChoice = feedback && isSelected && !feedback.is_correct;
              const isWrongChoice = feedback && !isCorrectAnswer;

              let bgColor = 'bg-transparent';
              let borderColor = '';

              if (feedback) {
                // After feedback - show results
                if (isCorrectAnswer) {
                  bgColor = 'bg-emerald-500/20';
                  borderColor = 'border-l-4 border-l-emerald-500';
                } else if (isUserWrongChoice) {
                  bgColor = 'bg-red-500/20';
                  borderColor = 'border-l-4 border-l-red-500';
                } else if (isWrongChoice) {
                  bgColor = 'bg-gray-800/10';
                }
              } else if (isSelected) {
                // Before feedback - highlight selected answer
                bgColor = 'bg-blue-500/30';
                borderColor = 'border-l-4 border-l-blue-500';
              }

              const toggleExpand = () => {
                const newExpanded = new Set(expandedChoices);
                if (isExpanded) {
                  newExpanded.delete(choice);
                } else {
                  newExpanded.add(choice);
                }
                setExpandedChoices(newExpanded);
              };

              return (
                <div key={index} className={`transition-all duration-200 ${bgColor} ${borderColor}`}>
                  {/* Choice Row */}
                  <div className="w-full p-3 flex items-center justify-between">
                    <button
                      onClick={async () => {
                        if (!feedback && question && user) {
                          setSelectedAnswer(choice);

                          // Auto-submit immediately
                          const timeSpent = Math.floor((Date.now() - startTime) / 1000);

                          try {
                            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                            const response = await fetch(`${apiUrl}/api/questions/submit`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                question_id: question.id,
                                user_id: user.userId,
                                user_answer: choice,
                                time_spent_seconds: timeSpent,
                              }),
                            });

                            if (response.ok) {
                              const data: Feedback = await response.json();
                              setFeedback(data);
                              setQuestionCount(prev => prev + 1);
                              if (data.is_correct) {
                                setCorrectCount(prev => prev + 1);
                              }
                              loadQueueStats();

                              // Auto-expand correct answer and user's wrong answer (Amboss-style)
                              const newExpanded = new Set<string>();
                              if (data.correct_answer) {
                                newExpanded.add(data.correct_answer);
                              }
                              if (!data.is_correct && choice) {
                                newExpanded.add(choice);
                              }
                              setExpandedChoices(newExpanded);

                              // Pre-load next question in background for instant loading
                              preloadNextQuestion();
                            }
                          } catch (error) {
                            console.error('Error submitting answer:', error);
                          }
                        }
                      }}
                      disabled={!!feedback}
                      className="flex items-center gap-2 flex-1 text-left hover:bg-gray-700/60 rounded-lg p-2 -m-2 transition-all duration-100 ease-out"
                    >
                      <span className="text-gray-400 text-sm font-semibold min-w-[1.5rem]">{letter}.</span>
                      <span className="text-base font-normal text-white leading-snug">{choice}</span>
                    </button>

                    {/* Status indicators */}
                    <div className="flex items-center gap-2">
                      {isSelected && !feedback && (
                        <div className="w-2 h-2 rounded-full bg-blue-500" />
                      )}
                      {feedback && (
                        <button
                          onClick={toggleExpand}
                          className="p-1 hover:bg-gray-800 rounded transition-colors duration-100"
                        >
                          <svg
                            className={`w-5 h-5 transition-transform duration-150 ${
                              isExpanded ? 'rotate-180' : ''
                            } ${isCorrectAnswer ? 'text-emerald-500' : isUserWrongChoice ? 'text-red-500' : 'text-gray-400'}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Explanation Dropdown */}
                  {feedback && isExpanded && (
                    <div className="px-5 pb-5 pt-3 border-t border-gray-700/50">
                      <div className={`text-base ${isCorrectAnswer ? 'text-emerald-400' : isUserWrongChoice ? 'text-red-400' : 'text-gray-400'} font-semibold mb-3`}>
                        {isCorrectAnswer ? '✓ Correct Answer' : isUserWrongChoice ? '✗ Your Answer (Incorrect)' : 'Why this is wrong'}
                      </div>
                      <div className="text-base text-gray-300 leading-relaxed space-y-3">
                        {(() => {
                          if (!feedback.explanation) {
                            return isCorrectAnswer
                              ? 'This is the correct answer for this patient.'
                              : 'Explanation for why this choice is incorrect will appear here.';
                          }

                          if (isCorrectAnswer) {
                            // Show principle + clinical reasoning + correct answer explanation with structure
                            return (
                              <>
                                {feedback.explanation.principle && (
                                  <div className="text-white font-medium">
                                    {feedback.explanation.principle}
                                  </div>
                                )}
                                {feedback.explanation.clinical_reasoning && (
                                  <div className="text-gray-300">
                                    {feedback.explanation.clinical_reasoning}
                                  </div>
                                )}
                                {feedback.explanation.correct_answer_explanation && (
                                  <div className="text-gray-300">
                                    {feedback.explanation.correct_answer_explanation}
                                  </div>
                                )}
                                {!feedback.explanation.principle && !feedback.explanation.clinical_reasoning && !feedback.explanation.correct_answer_explanation && (
                                  <div>This is the correct answer for this patient.</div>
                                )}
                              </>
                            );
                          } else {
                            // Show distractor explanation for this specific choice
                            const distractorExplanations = feedback.explanation.distractor_explanations;
                            if (distractorExplanations && distractorExplanations[letter]) {
                              return <div>{distractorExplanations[letter]}</div>;
                            }
                            return 'Explanation for why this choice is incorrect will appear here.';
                          }
                        })()}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* AI Chat below answer choices - compact version */}
          {feedback && question && user && (
            <div className="mb-4 flex-shrink-0">
              <AIChat
                questionId={question.id}
                userId={user.userId}
                isCorrect={feedback.is_correct}
                userAnswer={selectedAnswer || ''}
              />
            </div>
          )}

          {/* Action Buttons - Only show Next Question after feedback */}
          {feedback && (
            <div className="flex gap-4 flex-shrink-0">
              <button
                onClick={handleNext}
                className="px-10 py-4 bg-[#1E3A5F] hover:bg-[#2C5282] text-white rounded-lg transition-colors duration-200 text-lg font-semibold"
              >
                Next Question
              </button>
            </div>
          )}
        </div>

        {/* Question Rating - Bottom Right Corner (only after feedback) */}
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
