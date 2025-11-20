'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ProgressBar from '@/components/ProgressBar';
import Sidebar from '@/components/Sidebar';

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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [question, setQuestion] = useState<Question | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [loading, setLoading] = useState(true);
  const [questionCount, setQuestionCount] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [startTime, setStartTime] = useState<number>(0);

  // Temporary user ID (in production, this would come from auth)
  const userId = 'demo-user-1';

  const loadNextQuestion = async () => {
    setLoading(true);
    setSelectedAnswer(null);
    setFeedback(null);
    setStartTime(Date.now());

    try {
      const response = await fetch(`http://localhost:8000/api/questions/random`);
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
    loadNextQuestion();
  }, []);

  const handleSubmit = async () => {
    if (!selectedAnswer || !question) return;

    const timeSpent = Math.floor((Date.now() - startTime) / 1000);

    try {
      const response = await fetch('http://localhost:8000/api/questions/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question_id: question.id,
          user_id: userId,
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
        <div className="h-full flex flex-col max-w-5xl mx-auto px-4 py-3">
          {/* Stats bar */}
          <div className="flex justify-between items-center text-xs text-gray-500 mb-2 flex-shrink-0">
            <div>
              Question {questionCount + 1}
            </div>
            <div>
              {correctCount} / {questionCount} correct
              {questionCount > 0 && ` (${Math.round((correctCount / questionCount) * 100)}%)`}
            </div>
          </div>

          {/* Question Vignette - scrollable but compact */}
          <div className="mb-3 overflow-y-auto flex-shrink min-h-0 border-b border-gray-800 pb-2" style={{ maxHeight: '35vh' }}>
            <p className="text-xs leading-normal whitespace-pre-wrap pr-2">
              {question.vignette}
            </p>
          </div>

          {/* Answer Choices - fixed, no scroll */}
          <div className="space-y-1.5 mb-3 flex-shrink-0">
            {question.choices.map((choice, index) => {
              const isSelected = selectedAnswer === choice;
              const isCorrectAnswer = feedback && choice === feedback.correct_answer;

              let borderColor = 'border-gray-700';
              let bgColor = 'bg-transparent';

              if (feedback) {
                if (isCorrectAnswer) {
                  borderColor = 'border-emerald-500';
                  bgColor = 'bg-emerald-500/10';
                } else if (isSelected && !feedback.is_correct) {
                  borderColor = 'border-red-500';
                  bgColor = 'bg-red-500/10';
                }
              } else if (isSelected) {
                borderColor = 'border-[#1E3A5F]';
                bgColor = 'bg-[#1E3A5F]/10';
              }

              return (
                <button
                  key={index}
                  onClick={() => !feedback && setSelectedAnswer(choice)}
                  disabled={!!feedback}
                  className={`w-full p-2 border ${borderColor} ${bgColor} rounded text-left transition-all duration-200 hover:border-[#2C5282] disabled:cursor-not-allowed text-xs`}
                >
                  <span className="text-gray-400 mr-2 text-xs">{String.fromCharCode(65 + index)}.</span>
                  {choice}
                </button>
              );
            })}
          </div>

          {/* Feedback Section */}
          {feedback && (
            <div className={`p-3 border-l-4 mb-2 overflow-y-auto flex-shrink min-h-0 ${
              feedback.is_correct ? 'border-emerald-500 bg-emerald-500/5' : 'border-red-500 bg-red-500/5'
            }`} style={{ maxHeight: '20vh' }}>
              <h3 className={`text-sm font-semibold mb-1 ${
                feedback.is_correct ? 'text-emerald-500' : 'text-red-500'
              }`}>
                {feedback.is_correct ? 'Correct' : 'Incorrect'}
              </h3>
              {!feedback.is_correct && (
                <p className="text-gray-300 mb-1 text-xs">
                  Correct: <strong>{feedback.correct_answer}</strong>
                </p>
              )}
              {feedback.explanation && (
                <p className="text-gray-300 leading-normal text-xs">
                  {feedback.explanation}
                </p>
              )}
              <div className="mt-2 text-xs text-gray-500">
                {feedback.source}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-4 flex-shrink-0">
            {!feedback ? (
              <button
                onClick={handleSubmit}
                disabled={!selectedAnswer}
                className="px-8 py-3 bg-[#1E3A5F] hover:bg-[#2C5282] disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors duration-200"
              >
                Submit Answer
              </button>
            ) : (
              <button
                onClick={handleNext}
                className="px-8 py-3 bg-[#1E3A5F] hover:bg-[#2C5282] text-white rounded-lg transition-colors duration-200"
              >
                Next Question
              </button>
            )}

            <button
              onClick={() => router.push('/')}
              className="px-8 py-3 border border-gray-700 hover:border-[#1E3A5F] text-white rounded-lg transition-colors duration-200"
            >
              End Session
            </button>
          </div>
        </div>
      </main>
    </>
  );
}
