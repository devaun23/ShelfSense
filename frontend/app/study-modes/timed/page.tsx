'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { useUser } from '@/contexts/UserContext';

interface Question {
  id: string;
  vignette: string;
  choices: string[];
  source: string;
}

interface QuestionResult {
  question: Question;
  userAnswer: string | null;
  correct_answer?: string;
  is_correct?: boolean;
  time_spent: number;
}

type SessionState = 'config' | 'active' | 'results';

export default function TimedModePage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Session configuration
  const [sessionState, setSessionState] = useState<SessionState>('config');
  const [numQuestions, setNumQuestions] = useState(10);
  const [timePerQuestion, setTimePerQuestion] = useState(6); // minutes

  // Active session state
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<(string | null)[]>([]);
  const [questionStartTime, setQuestionStartTime] = useState<number>(0);
  const [questionTimeLeft, setQuestionTimeLeft] = useState<number>(0);
  const [results, setResults] = useState<QuestionResult[]>([]);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
    }
  }, [user, userLoading, router]);

  // Timer countdown
  useEffect(() => {
    if (sessionState === 'active' && questionTimeLeft > 0) {
      const interval = setInterval(() => {
        const timeLeft = timePerQuestion * 60 - Math.floor((Date.now() - questionStartTime) / 1000);
        setQuestionTimeLeft(Math.max(0, timeLeft));

        // Auto-advance when time runs out
        if (timeLeft <= 0) {
          handleNextQuestion();
        }
      }, 100);

      return () => clearInterval(interval);
    }
  }, [sessionState, questionStartTime, questionTimeLeft, timePerQuestion]);

  const startSession = async () => {
    if (!user) return;

    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/study-modes/start-session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: 'timed',
          num_questions: numQuestions,
          time_per_question_minutes: timePerQuestion,
          user_id: user.userId
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setQuestions(data.questions);
        setSelectedAnswers(new Array(data.questions.length).fill(null));
        setSessionState('active');
        setCurrentQuestionIndex(0);
        setQuestionStartTime(Date.now());
        setQuestionTimeLeft(timePerQuestion * 60);
      } else {
        setError('Failed to start session. Please try again.');
      }
    } catch (error) {
      console.error('Error starting session:', error);
      setError('Network error. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerSelect = (answer: string) => {
    const newAnswers = [...selectedAnswers];
    newAnswers[currentQuestionIndex] = answer;
    setSelectedAnswers(newAnswers);
  };

  const handleNextQuestion = () => {
    const timeSpent = Math.floor((Date.now() - questionStartTime) / 1000);

    // Save current question result
    const newResults = [...results];
    newResults[currentQuestionIndex] = {
      question: questions[currentQuestionIndex],
      userAnswer: selectedAnswers[currentQuestionIndex],
      time_spent: timeSpent
    };
    setResults(newResults);

    // Move to next question or finish
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setQuestionStartTime(Date.now());
      setQuestionTimeLeft(timePerQuestion * 60);
    } else {
      finishSession(newResults);
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
      setQuestionStartTime(Date.now());
      setQuestionTimeLeft(timePerQuestion * 60);
    }
  };

  const finishSession = async (sessionResults: QuestionResult[]) => {
    if (!user) return;

    setLoading(true);

    try {
      // Submit all answers and get feedback
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const submissionPromises = sessionResults.map(async (result, index) => {
        if (!result.userAnswer) return result;

        const response = await fetch(`${apiUrl}/api/questions/submit`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question_id: result.question.id,
            user_id: user.userId,
            user_answer: result.userAnswer,
            time_spent_seconds: result.time_spent,
          }),
        });

        if (response.ok) {
          const feedback = await response.json();
          return {
            ...result,
            correct_answer: feedback.correct_answer,
            is_correct: feedback.is_correct
          };
        }

        return result;
      });

      const finalResults = await Promise.all(submissionPromises);
      setResults(finalResults);
      setSessionState('results');
    } catch (error) {
      console.error('Error submitting answers:', error);
      setError('Failed to submit answers. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const resetSession = () => {
    setSessionState('config');
    setQuestions([]);
    setSelectedAnswers([]);
    setCurrentQuestionIndex(0);
    setResults([]);
    setError(null);
  };

  // Configuration Screen
  if (sessionState === 'config') {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="max-w-2xl mx-auto px-8 py-12">
            <h1 className="text-4xl font-bold mb-4" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              ⏱️ Timed Mode
            </h1>
            <p className="text-xl text-gray-400 mb-8">
              Simulate real exam conditions with a countdown timer
            </p>

            {error && (
              <div className="mb-6 p-4 bg-red-900/20 border border-red-500/50 rounded-lg">
                <p className="text-red-400">{error}</p>
              </div>
            )}

            <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 space-y-6">
              <div>
                <label className="block text-lg font-semibold mb-3">Number of Questions</label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={numQuestions}
                  onChange={(e) => setNumQuestions(parseInt(e.target.value) || 10)}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white text-lg"
                />
                <p className="mt-2 text-sm text-gray-400">Choose between 1-50 questions</p>
              </div>

              <div>
                <label className="block text-lg font-semibold mb-3">Time per Question (minutes)</label>
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={timePerQuestion}
                  onChange={(e) => setTimePerQuestion(parseInt(e.target.value) || 6)}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white text-lg"
                />
                <p className="mt-2 text-sm text-gray-400">USMLE Step 2 CK averages 90 seconds per question (~1.5 minutes)</p>
              </div>

              <div className="pt-4 border-t border-gray-700">
                <div className="flex items-center gap-3 text-gray-300 mb-2">
                  <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="font-semibold">Total Session Time: {numQuestions * timePerQuestion} minutes</span>
                </div>
                <p className="text-sm text-gray-400 ml-8">
                  All answers will be revealed at the end, just like a real exam
                </p>
              </div>

              <button
                onClick={startSession}
                disabled={loading}
                className="w-full px-8 py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white rounded-lg transition-colors duration-200 text-lg font-semibold"
              >
                {loading ? 'Starting Session...' : 'Start Timed Session'}
              </button>

              <button
                onClick={() => router.push('/study-modes')}
                className="w-full px-8 py-4 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors duration-200 text-lg"
              >
                Back to Study Modes
              </button>
            </div>
          </div>
        </main>
      </>
    );
  }

  // Active Session Screen
  if (sessionState === 'active' && questions.length > 0) {
    const currentQuestion = questions[currentQuestionIndex];
    const progress = ((currentQuestionIndex + 1) / questions.length) * 100;
    const minutes = Math.floor(questionTimeLeft / 60);
    const seconds = questionTimeLeft % 60;

    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          {/* Timer Bar */}
          <div className="fixed top-0 left-0 right-0 z-50 bg-gray-900 border-b border-gray-700">
            <div className="flex items-center justify-between px-8 py-4">
              <div className="flex items-center gap-6">
                <div className={`text-2xl font-bold ${questionTimeLeft < 60 ? 'text-red-500 animate-pulse' : 'text-white'}`}>
                  {minutes}:{seconds.toString().padStart(2, '0')}
                </div>
                <div className="text-gray-400">
                  Question {currentQuestionIndex + 1} of {questions.length}
                </div>
              </div>
              <div className="text-gray-400">
                {selectedAnswers.filter(a => a !== null).length} / {questions.length} answered
              </div>
            </div>
            <div className="h-1 bg-gray-800">
              <div
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className={`max-w-4xl mx-auto px-8 py-6 pt-28 ${sidebarOpen ? 'md:ml-0' : ''}`}>
            {/* Question Vignette */}
            <div className="mb-6 border-b border-gray-800 pb-6">
              <p className="text-xl leading-relaxed whitespace-pre-wrap font-semibold">
                {currentQuestion.vignette}
              </p>
            </div>

            {/* Answer Choices */}
            <div className="mb-8 border border-gray-700 rounded-lg divide-y divide-gray-700">
              {currentQuestion.choices.map((choice, index) => {
                const letter = String.fromCharCode(65 + index);
                const isSelected = selectedAnswers[currentQuestionIndex] === choice;

                return (
                  <button
                    key={index}
                    onClick={() => handleAnswerSelect(choice)}
                    className={`w-full p-4 flex items-center gap-3 text-left transition-all duration-200 ${
                      isSelected
                        ? 'bg-blue-500/30 border-l-4 border-l-blue-500'
                        : 'hover:bg-gray-800'
                    }`}
                  >
                    <span className="text-gray-400 text-sm font-semibold min-w-[1.5rem]">{letter}.</span>
                    <span className="text-base text-white leading-snug">{choice}</span>
                    {isSelected && (
                      <div className="ml-auto w-2 h-2 rounded-full bg-blue-500" />
                    )}
                  </button>
                );
              })}
            </div>

            {/* Navigation Buttons */}
            <div className="flex gap-4 justify-between">
              <button
                onClick={handlePreviousQuestion}
                disabled={currentQuestionIndex === 0}
                className="px-6 py-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded-lg transition-colors duration-200"
              >
                ← Previous
              </button>

              {currentQuestionIndex < questions.length - 1 ? (
                <button
                  onClick={handleNextQuestion}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200"
                >
                  Next →
                </button>
              ) : (
                <button
                  onClick={handleNextQuestion}
                  className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors duration-200 font-semibold"
                >
                  Finish & See Results
                </button>
              )}
            </div>

            {/* Question Navigator */}
            <div className="mt-8 p-6 bg-gray-900 border border-gray-700 rounded-lg">
              <h3 className="text-lg font-semibold mb-4">Question Navigator</h3>
              <div className="grid grid-cols-10 gap-2">
                {questions.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      setCurrentQuestionIndex(index);
                      setQuestionStartTime(Date.now());
                      setQuestionTimeLeft(timePerQuestion * 60);
                    }}
                    className={`aspect-square flex items-center justify-center rounded-lg text-sm font-semibold transition-all duration-200 ${
                      index === currentQuestionIndex
                        ? 'bg-blue-600 text-white'
                        : selectedAnswers[index] !== null
                        ? 'bg-green-500/30 text-green-400 border border-green-500/50'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}
                  >
                    {index + 1}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </main>
      </>
    );
  }

  // Results Screen
  if (sessionState === 'results') {
    const correctCount = results.filter(r => r.is_correct).length;
    const totalQuestions = results.length;
    const percentage = Math.round((correctCount / totalQuestions) * 100);
    const totalTime = results.reduce((sum, r) => sum + r.time_spent, 0);
    const avgTime = Math.round(totalTime / totalQuestions);

    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="max-w-4xl mx-auto px-8 py-12">
            <h1 className="text-4xl font-bold mb-8" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Session Complete!
            </h1>

            {/* Summary Stats */}
            <div className="grid md:grid-cols-3 gap-6 mb-8">
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
                <div className="text-gray-400 text-sm mb-2">Score</div>
                <div className={`text-4xl font-bold ${percentage >= 70 ? 'text-green-500' : percentage >= 50 ? 'text-yellow-500' : 'text-red-500'}`}>
                  {percentage}%
                </div>
                <div className="text-gray-400 text-sm mt-2">{correctCount} / {totalQuestions} correct</div>
              </div>

              <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
                <div className="text-gray-400 text-sm mb-2">Total Time</div>
                <div className="text-4xl font-bold">{Math.floor(totalTime / 60)}m</div>
                <div className="text-gray-400 text-sm mt-2">{totalTime}s total</div>
              </div>

              <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
                <div className="text-gray-400 text-sm mb-2">Avg Time/Question</div>
                <div className="text-4xl font-bold">{avgTime}s</div>
                <div className="text-gray-400 text-sm mt-2">
                  {avgTime < 90 ? 'Great pace!' : avgTime < 120 ? 'Good pace' : 'Consider speeding up'}
                </div>
              </div>
            </div>

            {/* Question Results */}
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 mb-8">
              <h2 className="text-2xl font-bold mb-4">Question Results</h2>
              <div className="space-y-3">
                {results.map((result, index) => (
                  <div
                    key={index}
                    className={`p-4 rounded-lg border ${
                      result.is_correct
                        ? 'bg-green-500/10 border-green-500/30'
                        : 'bg-red-500/10 border-red-500/30'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`text-lg font-semibold ${result.is_correct ? 'text-green-500' : 'text-red-500'}`}>
                          {result.is_correct ? '✓' : '✗'}
                        </div>
                        <div className="text-sm">
                          <span className="text-gray-400">Question {index + 1}</span>
                          {!result.userAnswer && (
                            <span className="ml-2 text-yellow-500">(Unanswered)</span>
                          )}
                        </div>
                      </div>
                      <div className="text-sm text-gray-400">
                        {result.time_spent}s
                      </div>
                    </div>
                    {result.correct_answer && (
                      <div className="mt-2 text-sm text-gray-300">
                        <span className="text-gray-500">Correct answer:</span> {result.correct_answer}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                onClick={resetSession}
                className="flex-1 px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200 text-lg font-semibold"
              >
                Start New Session
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

  return null;
}
