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
        <div className="h-full flex flex-col mx-auto px-8 py-6 pt-16" style={{ maxWidth: sidebarOpen ? '1200px' : '1400px' }}>
          {/* Stats bar */}
          <div className="flex justify-end items-center text-base mb-4 flex-shrink-0">
            <div>
              <span className="text-gray-500 font-semibold">Question </span>
              <span className="text-white font-bold">{questionCount + 1}</span>
            </div>
          </div>

          {/* Question Vignette - scrollable but compact */}
          <div className="mb-6 overflow-y-auto flex-shrink min-h-0 border-b border-gray-800 pb-4" style={{ maxHeight: '40vh' }}>
            <p className="text-base leading-loose whitespace-pre-wrap pr-2 font-bold">
              {question.vignette}
            </p>
          </div>

          {/* Answer Choices - fixed, no scroll */}
          <div className="space-y-3 mb-6 flex-shrink-0">
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
                  className={`w-full p-3 border-2 ${borderColor} ${bgColor} rounded-lg text-left transition-all duration-200 hover:border-[#2C5282] disabled:cursor-not-allowed text-base font-medium`}
                >
                  <span className="text-gray-400 mr-3 text-base font-semibold">{String.fromCharCode(65 + index)}.</span>
                  {choice}
                </button>
              );
            })}
          </div>

          {/* Feedback Section */}
          {feedback && (
            <div className={`p-4 border-l-4 mb-4 ${
              feedback.is_correct ? 'border-emerald-500 bg-emerald-500/5' : 'border-red-500 bg-red-500/5'
            }`}>
              <h3 className={`text-lg font-bold ${
                feedback.is_correct ? 'text-emerald-500' : 'text-red-500'
              }`}>
                {feedback.is_correct ? 'Correct' : `Incorrect - Correct: ${feedback.correct_answer}`}
              </h3>
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
