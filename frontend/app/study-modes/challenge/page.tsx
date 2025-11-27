'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import AIChat from '@/components/AIChat';
import QuestionRating from '@/components/QuestionRating';
import { useUser } from '@/contexts/UserContext';

interface Question {
  id: string;
  vignette: string;
  choices: string[];
  source: string;
  global_accuracy?: number;
  attempt_count?: number;
}

interface Feedback {
  is_correct: boolean;
  correct_answer: string;
  explanation: any;
  source: string;
}

export default function ChallengeModePage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [question, setQuestion] = useState<Question | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [challengeStats, setChallengeStats] = useState<any>(null);
  const [questionCount, setQuestionCount] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user && !question) {
      loadChallengeQuestion();
      loadChallengeStats();
    }
  }, [user, userLoading, router]);

  const loadChallengeStats = async () => {
    if (!user) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${apiUrl}/api/study-modes/challenge-questions?user_id=${user.userId}`
      );
      if (response.ok) {
        const data = await response.json();
        setChallengeStats({
          total_hard_questions: data.length,
          avg_accuracy: data.length > 0
            ? Math.round(data.reduce((sum: number, q: any) => sum + q.global_accuracy, 0) / data.length)
            : 0
        });
      }
    } catch (error) {
      console.error('Error loading challenge stats:', error);
    }
  };

  const loadChallengeQuestion = async () => {
    if (!user) return;

    setLoading(true);
    setError(null);
    setSelectedAnswer(null);
    setFeedback(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/questions/random`);

      if (response.ok) {
        const data = await response.json();
        setQuestion(data);
      } else if (response.status === 404) {
        setError('No challenge questions available. Try answering more questions first.');
      } else {
        setError('Failed to load question. Please try again.');
      }
    } catch (error) {
      console.error('Error loading question:', error);
      setError('Network error. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedAnswer || !question || !user) return;

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
          time_spent_seconds: 0,
        }),
      });

      if (response.ok) {
        const data: Feedback = await response.json();
        setFeedback(data);
        setQuestionCount(prev => prev + 1);
        if (data.is_correct) {
          setCorrectCount(prev => prev + 1);
        }
      } else {
        setError('Failed to submit answer. Please try again.');
      }
    } catch (error) {
      console.error('Error submitting answer:', error);
      setError('Network error while submitting. Please try again.');
    }
  };

  const handleNext = () => {
    loadChallengeQuestion();
  };

  if (loading && !question) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="flex items-center justify-center min-h-screen">
            <svg className="animate-spin h-16 w-16 text-white" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C11.172 2 10.5 2.672 10.5 3.5V5.145C9.419 5.408 8.414 5.877 7.536 6.514L6.379 5.357C5.793 4.771 4.843 4.771 4.257 5.357C3.671 5.943 3.671 6.893 4.257 7.479L5.414 8.636C4.777 9.514 4.308 10.519 4.045 11.6H2.5C1.672 11.6 1 12.272 1 13.1C1 13.928 1.672 14.6 2.5 14.6H4.145C4.408 15.681 4.877 16.686 5.514 17.564L4.357 18.721C3.771 19.307 3.771 20.257 4.357 20.843C4.943 21.429 5.893 21.429 6.479 20.843L7.636 19.686C8.514 20.323 9.519 20.792 10.6 21.055V22.5C10.6 23.328 11.272 24 12.1 24C12.928 24 13.6 23.328 13.6 22.5V20.855C14.681 20.592 15.686 20.123 16.564 19.486L17.721 20.643C18.307 21.229 19.257 21.229 19.843 20.643C20.429 20.057 20.429 19.107 19.843 18.521L18.686 17.364C19.323 16.486 19.792 15.481 20.055 14.4H21.5C22.328 14.4 23 13.728 23 12.9C23 12.072 22.328 11.4 21.5 11.4H19.855C19.592 10.319 19.123 9.314 18.486 8.436L19.643 7.279C20.229 6.693 20.229 5.743 19.643 5.157C19.057 4.571 18.107 4.571 17.521 5.157L16.364 6.314C15.486 5.677 14.481 5.208 13.4 4.945V3.5C13.4 2.672 12.728 2 11.9 2H12ZM12 8C14.209 8 16 9.791 16 12C16 14.209 14.209 16 12 16C9.791 16 8 14.209 8 12C8 9.791 9.791 8 12 8Z" />
            </svg>
          </div>
        </main>
      </>
    );
  }

  if (!question && !loading) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="max-w-2xl mx-auto px-8 py-12">
            <h1 className="text-4xl font-bold mb-4" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              🎯 Challenge Mode
            </h1>

            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-6 mb-6">
              <p className="text-yellow-400">
                {error || 'No challenge questions available right now.'}
              </p>
              <p className="text-gray-400 mt-2">
                Challenge mode shows questions with less than 60% global accuracy.
                Try answering more questions in regular study mode first.
              </p>
            </div>

            <div className="flex gap-4">
              <button
                onClick={() => router.push('/study')}
                className="flex-1 px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200 text-lg font-semibold"
              >
                Go to Regular Study
              </button>
              <button
                onClick={() => router.push('/study-modes')}
                className="flex-1 px-8 py-4 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors duration-200 text-lg"
              >
                Back to Study Modes
              </button>
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
        <div className="flex flex-col mx-auto px-8 py-6 pt-16 pb-32" style={{ maxWidth: sidebarOpen ? '1200px' : '1400px' }}>
          {/* Challenge Mode Header */}
          <div className="mb-6 p-4 bg-gradient-to-r from-orange-500/20 to-red-500/20 border border-orange-500/30 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-orange-400">🎯 Challenge Mode</h2>
                <p className="text-sm text-gray-300">Only hard questions (&lt; 60% global accuracy)</p>
              </div>
              {challengeStats && (
                <div className="text-right">
                  <div className="text-2xl font-bold text-orange-400">
                    {challengeStats.avg_accuracy}%
                  </div>
                  <div className="text-xs text-gray-400">Avg Accuracy</div>
                </div>
              )}
            </div>
          </div>

          {/* Stats */}
          <div className="flex justify-between items-center text-base mb-4">
            <div className="flex gap-6">
              <div>
                <span className="text-gray-400 font-semibold">Session: </span>
                <span className="text-white font-bold">{correctCount} / {questionCount}</span>
                {questionCount > 0 && (
                  <span className="text-gray-500 ml-2">
                    ({Math.round((correctCount / questionCount) * 100)}%)
                  </span>
                )}
              </div>
            </div>
            {question && question.global_accuracy !== undefined && (
              <div className="text-sm">
                <span className="text-gray-500">This question: </span>
                <span className="text-orange-400 font-semibold">
                  {Math.round(question.global_accuracy)}% accuracy
                </span>
                {question.attempt_count && (
                  <span className="text-gray-500 ml-2">
                    ({question.attempt_count} attempts)
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Question Vignette */}
          {question && (
            <>
              <div className="mb-6 border-b border-gray-800 pb-6">
                <p className="text-xl leading-relaxed whitespace-pre-wrap font-semibold">
                  {question.vignette}
                </p>
              </div>

              {/* Answer Choices */}
              <div className="mb-6 border border-gray-700 rounded-lg divide-y divide-gray-700">
                {question.choices.map((choice, index) => {
                  const letter = String.fromCharCode(65 + index);
                  const isSelected = selectedAnswer === choice;
                  const isCorrectAnswer = feedback && choice === feedback.correct_answer;
                  const isUserWrongChoice = feedback && isSelected && !feedback.is_correct;

                  let bgColor = 'bg-transparent';
                  let borderColor = '';

                  if (feedback) {
                    if (isCorrectAnswer) {
                      bgColor = 'bg-emerald-500/20';
                      borderColor = 'border-l-4 border-l-emerald-500';
                    } else if (isUserWrongChoice) {
                      bgColor = 'bg-red-500/20';
                      borderColor = 'border-l-4 border-l-red-500';
                    }
                  } else if (isSelected) {
                    bgColor = 'bg-blue-500/30';
                    borderColor = 'border-l-4 border-l-blue-500';
                  }

                  return (
                    <div key={index} className={`transition-all duration-200 ${bgColor} ${borderColor}`}>
                      <div className="w-full p-3 flex items-center justify-between">
                        <button
                          onClick={() => {
                            if (!feedback) {
                              setSelectedAnswer(choice);
                            }
                          }}
                          disabled={!!feedback}
                          className="flex items-center gap-2 flex-1 text-left hover:bg-gray-700/60 rounded-lg p-2 -m-2 transition-all duration-100"
                        >
                          <span className="text-gray-400 text-sm font-semibold min-w-[1.5rem]">{letter}.</span>
                          <span className="text-base font-normal text-white leading-snug">{choice}</span>
                        </button>
                        {isSelected && !feedback && (
                          <div className="w-2 h-2 rounded-full bg-blue-500" />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* AI Chat */}
              {feedback && user && (
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
              {!feedback && selectedAnswer && (
                <div className="flex gap-4">
                  <button
                    onClick={handleSubmit}
                    className="px-10 py-4 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors duration-200 text-lg font-semibold"
                  >
                    Submit Answer
                  </button>
                </div>
              )}

              {feedback && (
                <div className="flex gap-4">
                  <button
                    onClick={handleNext}
                    className="px-10 py-4 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors duration-200 text-lg font-semibold"
                  >
                    Next Challenge
                  </button>
                  <button
                    onClick={() => router.push('/study-modes')}
                    className="px-10 py-4 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors duration-200 text-lg"
                  >
                    Back to Study Modes
                  </button>
                </div>
              )}

              {/* Question Rating */}
              {feedback && user && (
                <QuestionRating
                  questionId={question.id}
                  userId={user.userId}
                  onRatingComplete={handleNext}
                />
              )}
            </>
          )}
        </div>
      </main>
    </>
  );
}
