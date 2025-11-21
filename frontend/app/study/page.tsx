'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ProgressBar from '@/components/ProgressBar';
import Sidebar from '@/components/Sidebar';
import AIChat from '@/components/AIChat';
import { useUser } from '@/contexts/UserContext';

interface Question {
  id: string;
  vignette: string;
  choices: string[];
  source: string;
  recency_weight: number;
}

interface Feedback {
  is_correct: boolean;
  correct_answer: string;
  explanation: string | null;
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

  const loadNextQuestion = async () => {
    setLoading(true);
    setSelectedAnswer(null);
    setFeedback(null);
    setExpandedChoices(new Set());
    setStartTime(Date.now());

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/questions/random`);
      if (response.ok) {
        const data = await response.json();
        setQuestion(data);
      }
    } catch (error) {
      console.error('Error loading question:', error);
    } finally {
      setLoading(false);
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
            <p className="text-gray-400">Loading question...</p>
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

      <main className={`h-screen overflow-hidden bg-black text-white transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        <div className="h-full flex flex-col mx-auto px-8 py-6 pt-16" style={{ maxWidth: sidebarOpen ? '1200px' : '1400px' }}>
          {/* Stats bar */}
          <div className="flex justify-end items-center text-base mb-4 flex-shrink-0">
            <div>
              <span className="text-gray-500 font-semibold">Queue: </span>
              <span className="text-white font-bold">{queueStats.completed}/{queueStats.queueSize} Completed</span>
            </div>
          </div>

          {/* Question Vignette - fits on screen, no scroll */}
          <div className="mb-6 flex-shrink border-b border-gray-800 pb-4">
            <p className="text-sm leading-relaxed whitespace-pre-wrap font-bold">
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
              const isIncorrect = feedback && isSelected && !feedback.is_correct;

              let bgColor = 'bg-transparent';
              if (isCorrectAnswer && isExpanded) {
                bgColor = 'bg-emerald-500/10';
              } else if (isIncorrect && isExpanded) {
                bgColor = 'bg-red-500/10';
              } else if (isSelected) {
                bgColor = 'bg-[#1E3A5F]/10';
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
                <div key={index} className={`transition-colors ${bgColor}`}>
                  {/* Choice Button */}
                  <button
                    onClick={() => !feedback && setSelectedAnswer(choice)}
                    disabled={!!feedback}
                    className="w-full p-4 flex items-center justify-between text-left hover:bg-gray-900/30 transition-colors disabled:cursor-default"
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <span className="text-gray-400 text-base font-semibold">{letter}.</span>
                      <span className="text-base font-medium text-white">{choice}</span>
                    </div>

                    {/* Status indicators */}
                    <div className="flex items-center gap-2">
                      {isSelected && !feedback && (
                        <div className="w-2 h-2 rounded-full bg-blue-500" />
                      )}
                      {feedback && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleExpand();
                          }}
                          className="p-1 hover:bg-gray-800 rounded transition-colors"
                        >
                          <svg
                            className={`w-5 h-5 transition-transform ${
                              isExpanded ? 'rotate-180' : ''
                            } ${isCorrectAnswer ? 'text-emerald-500' : isIncorrect ? 'text-red-500' : 'text-gray-400'}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </button>

                  {/* Explanation Dropdown */}
                  {feedback && isExpanded && (
                    <div className="px-4 pb-4 pt-2 border-t border-gray-700/50">
                      <div className={`text-sm ${isCorrectAnswer ? 'text-emerald-400' : isIncorrect ? 'text-red-400' : 'text-gray-400'} font-semibold mb-2`}>
                        {isCorrectAnswer ? '✓ Correct Answer' : isIncorrect ? '✗ Incorrect' : 'Explanation'}
                      </div>
                      <div className="text-sm text-gray-300 leading-relaxed">
                        {/* Placeholder for individual choice explanation */}
                        {isCorrectAnswer
                          ? feedback.explanation || 'This is the correct answer for this patient.'
                          : 'Explanation for why this choice is incorrect will appear here.'}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* AI Chat below answer choices */}
          {feedback && question && user && (
            <div className="mb-4">
              <AIChat
                questionId={question.id}
                userId={user.userId}
                isCorrect={feedback.is_correct}
                userAnswer={selectedAnswer || ''}
              />
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-4 flex-shrink-0">
            {!feedback ? (
              <button
                onClick={handleSubmit}
                disabled={!selectedAnswer}
                className="px-10 py-4 bg-[#1E3A5F] hover:bg-[#2C5282] disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors duration-200 text-base font-semibold"
              >
                Submit Answer
              </button>
            ) : (
              <button
                onClick={handleNext}
                className="px-10 py-4 bg-[#1E3A5F] hover:bg-[#2C5282] text-white rounded-lg transition-colors duration-200 text-base font-semibold"
              >
                Next Question
              </button>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
