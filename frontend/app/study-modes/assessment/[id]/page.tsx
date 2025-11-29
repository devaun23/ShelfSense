'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useUser } from '@/contexts/UserContext';
import LoadingSpinner, { FullPageLoader } from '@/components/ui/LoadingSpinner';

const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });

interface Question {
  id: string;
  index: number;
  vignette: string;
  choices: string[];
  source: string | null;
  user_answer: string | null;
  flagged: boolean;
  time_spent: number;
}

interface Assessment {
  id: string;
  name: string;
  total_blocks: number;
  questions_per_block: number;
  time_per_block_minutes: number;
  status: string;
  current_block: number;
}

interface BlockData {
  assessment_id: string;
  block_number: number;
  status: string;
  time_limit_seconds: number;
  time_remaining_seconds: number;
  questions: Question[];
  current_index: number;
}

type PageState = 'loading' | 'overview' | 'active' | 'block_complete' | 'break';

export default function AssessmentTakingPage() {
  const router = useRouter();
  const params = useParams();
  const assessmentId = params.id as string;
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [pageState, setPageState] = useState<PageState>('loading');
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [blockData, setBlockData] = useState<BlockData | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [isFlagged, setIsFlagged] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [questionStartTime, setQuestionStartTime] = useState(Date.now());
  const [blockResults, setBlockResults] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user && assessmentId) {
      loadAssessment();
    }
  }, [user, userLoading, assessmentId, router]);

  // Timer countdown
  useEffect(() => {
    if (pageState !== 'active' || timeRemaining <= 0) return;

    const interval = setInterval(() => {
      setTimeRemaining(prev => {
        const newTime = Math.max(0, prev - 1);
        if (newTime === 0) {
          handleCompleteBlock();
        }
        return newTime;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [pageState, timeRemaining]);

  const loadAssessment = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/self-assessment/${assessmentId}?user_id=${user?.userId}`);
      if (!response.ok) {
        setError('Assessment not found');
        return;
      }

      const data = await response.json();
      setAssessment(data);

      if (data.status === 'completed') {
        router.push(`/study-modes/assessment/${assessmentId}/results`);
        return;
      }

      if (data.status === 'not_started') {
        setPageState('overview');
      } else if (data.status === 'in_progress') {
        await loadBlock(data.current_block);
      } else {
        setPageState('overview');
      }
    } catch (err) {
      setError('Failed to load assessment');
    }
  };

  const loadBlock = async (blockNumber: number) => {
    setPageState('loading');
    try {
      const response = await fetch(
        `${apiUrl}/api/self-assessment/${assessmentId}/block/${blockNumber}/questions?user_id=${user?.userId}`
      );

      if (!response.ok) {
        const errData = await response.json();
        setError(errData.detail || 'Failed to load block');
        return;
      }

      const data: BlockData = await response.json();
      setBlockData(data);
      setTimeRemaining(data.time_remaining_seconds);

      // Restore progress
      const firstUnanswered = data.questions.findIndex(q => !q.user_answer);
      const startIndex = firstUnanswered >= 0 ? firstUnanswered : 0;
      setCurrentQuestionIndex(startIndex);

      const currentQ = data.questions[startIndex];
      setSelectedAnswer(currentQ?.user_answer || null);
      setIsFlagged(currentQ?.flagged || false);
      setQuestionStartTime(Date.now());

      setPageState('active');
    } catch (err) {
      setError('Network error loading block');
    }
  };

  const startAssessment = async () => {
    try {
      const response = await fetch(
        `${apiUrl}/api/self-assessment/${assessmentId}/start?user_id=${user?.userId}`,
        { method: 'POST' }
      );

      if (response.ok) {
        await loadAssessment();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to start assessment');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  const saveAnswer = useCallback(async (answer: string | null, flagged: boolean) => {
    if (!blockData || !user) return;

    const question = blockData.questions[currentQuestionIndex];
    const timeSpent = Math.floor((Date.now() - questionStartTime) / 1000);

    if (!answer) return; // Don't save empty answers

    setSaving(true);
    try {
      await fetch(
        `${apiUrl}/api/self-assessment/${assessmentId}/block/${blockData.block_number}/answer?user_id=${user.userId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question_id: question.id,
            answer: answer,
            time_spent_seconds: timeSpent,
            flagged: flagged,
          }),
        }
      );

      // Update local state
      const updatedQuestions = [...blockData.questions];
      updatedQuestions[currentQuestionIndex] = {
        ...question,
        user_answer: answer,
        flagged: flagged,
        time_spent: question.time_spent + timeSpent,
      };
      setBlockData({ ...blockData, questions: updatedQuestions });
    } catch (err) {
      console.error('Error saving answer:', err);
    } finally {
      setSaving(false);
    }
  }, [blockData, currentQuestionIndex, questionStartTime, assessmentId, user, apiUrl]);

  const handleAnswerSelect = (answer: string) => {
    setSelectedAnswer(answer);
    saveAnswer(answer, isFlagged);
  };

  const handleFlagToggle = () => {
    const newFlagged = !isFlagged;
    setIsFlagged(newFlagged);
    if (selectedAnswer) {
      saveAnswer(selectedAnswer, newFlagged);
    }
  };

  const navigateToQuestion = (index: number) => {
    if (index < 0 || index >= (blockData?.questions.length || 0)) return;

    setCurrentQuestionIndex(index);
    const question = blockData?.questions[index];
    setSelectedAnswer(question?.user_answer || null);
    setIsFlagged(question?.flagged || false);
    setQuestionStartTime(Date.now());
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < (blockData?.questions.length || 0) - 1) {
      navigateToQuestion(currentQuestionIndex + 1);
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      navigateToQuestion(currentQuestionIndex - 1);
    }
  };

  const handleCompleteBlock = async () => {
    if (!blockData || !user) return;

    const totalTimeSpent = (blockData.time_limit_seconds - timeRemaining);

    try {
      const response = await fetch(
        `${apiUrl}/api/self-assessment/${assessmentId}/block/${blockData.block_number}/complete?user_id=${user.userId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ time_spent_seconds: totalTimeSpent }),
        }
      );

      if (response.ok) {
        const results = await response.json();
        setBlockResults(results);

        // Check if this was the last block
        if (assessment && blockData.block_number >= assessment.total_blocks) {
          router.push(`/study-modes/assessment/${assessmentId}/results`);
        } else {
          setPageState('break');
        }
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to complete block');
      }
    } catch (err) {
      setError('Network error completing block');
    }
  };

  const startNextBlock = async () => {
    if (assessment && blockData) {
      await loadBlock(blockData.block_number + 1);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Loading state
  if (pageState === 'loading') {
    return <FullPageLoader message="Loading assessment..." />;
  }

  // Error state
  if (error) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Error</h1>
          <p className="text-gray-400 mb-6">{error}</p>
          <button
            onClick={() => router.push('/study-modes/assessment')}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg"
          >
            Back to Assessments
          </button>
        </div>
      </main>
    );
  }

  // Overview state (before starting)
  if (pageState === 'overview' && assessment) {
    const totalQuestions = assessment.total_blocks * assessment.questions_per_block;
    const totalTime = assessment.total_blocks * assessment.time_per_block_minutes;

    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${sidebarOpen ? 'md:ml-64' : 'ml-0'}`}>
          <div className="max-w-2xl mx-auto px-8 py-12">
            <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              {assessment.name}
            </h1>
            <p className="text-xl text-gray-400 mb-8">NBME Style Self Assessment</p>

            <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 mb-8">
              <h2 className="text-xl font-bold mb-6">Assessment Overview</h2>

              <div className="grid grid-cols-2 gap-6 mb-8">
                <div>
                  <div className="text-gray-400 text-sm">Total Questions</div>
                  <div className="text-3xl font-bold">{totalQuestions}</div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Total Time</div>
                  <div className="text-3xl font-bold">{totalTime} min</div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Blocks</div>
                  <div className="text-3xl font-bold">{assessment.total_blocks}</div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Time per Block</div>
                  <div className="text-3xl font-bold">{assessment.time_per_block_minutes} min</div>
                </div>
              </div>

              <div className="bg-gray-800 rounded-lg p-4 mb-6">
                <h3 className="font-semibold mb-2">Instructions</h3>
                <ul className="text-sm text-gray-400 space-y-2">
                  <li>Each block has {assessment.questions_per_block} questions and {assessment.time_per_block_minutes} minutes</li>
                  <li>You can navigate between questions within a block</li>
                  <li>Use the flag feature to mark questions for review</li>
                  <li>When time expires, the block will auto submit</li>
                  <li>Take breaks between blocks if needed</li>
                  <li>Your predicted score will be calculated at the end</li>
                </ul>
              </div>

              <button
                onClick={startAssessment}
                className="w-full px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-lg text-lg font-semibold transition-colors"
              >
                Begin Assessment
              </button>
            </div>

            <button
              onClick={() => router.push('/study-modes/assessment')}
              className="w-full px-8 py-4 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              Back to Assessments
            </button>
          </div>
        </main>
      </>
    );
  }

  // Break state (between blocks)
  if (pageState === 'break' && blockResults && assessment) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="max-w-xl w-full mx-auto px-8">
          <h1 className="text-3xl font-bold mb-2 text-center">Block {blockResults.block_number} Complete</h1>
          <p className="text-gray-400 text-center mb-8">Take a break before continuing</p>

          <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 mb-8">
            <div className="grid grid-cols-3 gap-6 mb-8 text-center">
              <div>
                <div className="text-gray-400 text-sm">Score</div>
                <div className={`text-3xl font-bold ${blockResults.accuracy >= 70 ? 'text-green-400' : blockResults.accuracy >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                  {blockResults.accuracy}%
                </div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Correct</div>
                <div className="text-3xl font-bold">{blockResults.questions_correct}/{blockResults.questions_total}</div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Time</div>
                <div className="text-3xl font-bold">{Math.floor(blockResults.time_spent_seconds / 60)}m</div>
              </div>
            </div>

            <div className="text-center text-gray-400 mb-6">
              Block {blockResults.block_number} of {assessment.total_blocks} completed
            </div>

            <button
              onClick={startNextBlock}
              className="w-full px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-lg text-lg font-semibold transition-colors"
            >
              Continue to Block {blockResults.block_number + 1}
            </button>
          </div>
        </div>
      </main>
    );
  }

  // Active assessment state
  if (pageState === 'active' && blockData && blockData.questions.length > 0) {
    const currentQuestion = blockData.questions[currentQuestionIndex];
    const answeredCount = blockData.questions.filter(q => q.user_answer).length;
    const progress = ((currentQuestionIndex + 1) / blockData.questions.length) * 100;
    const isLowTime = timeRemaining < 300; // Less than 5 minutes

    return (
      <main className="min-h-screen bg-black text-white">
        {/* Timer Bar */}
        <div className="fixed top-0 left-0 right-0 z-50 bg-gray-900 border-b border-gray-700">
          <div className="flex items-center justify-between px-8 py-4">
            <div className="flex items-center gap-6">
              <div className={`text-2xl font-bold ${isLowTime ? 'text-red-500 animate-pulse' : 'text-white'}`}>
                {formatTime(timeRemaining)}
              </div>
              <div className="text-gray-400">
                Block {blockData.block_number} &bull; Question {currentQuestionIndex + 1} of {blockData.questions.length}
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-gray-400">
                {answeredCount} / {blockData.questions.length} answered
              </div>
              {saving && <LoadingSpinner size="sm" />}
            </div>
          </div>
          <div className="h-1 bg-gray-800">
            <div className="h-full bg-blue-500 transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-8 py-6 pt-28">
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
              const isSelected = selectedAnswer === choice;

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
                  {isSelected && <div className="ml-auto w-2 h-2 rounded-full bg-blue-500" />}
                </button>
              );
            })}
          </div>

          {/* Navigation & Actions */}
          <div className="flex items-center justify-between mb-8">
            <div className="flex gap-4">
              <button
                onClick={handlePreviousQuestion}
                disabled={currentQuestionIndex === 0}
                className="px-6 py-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 rounded-lg transition-colors"
              >
                Previous
              </button>
              <button
                onClick={handleNextQuestion}
                disabled={currentQuestionIndex === blockData.questions.length - 1}
                className="px-6 py-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 rounded-lg transition-colors"
              >
                Next
              </button>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={handleFlagToggle}
                className={`px-4 py-3 rounded-lg transition-colors flex items-center gap-2 ${
                  isFlagged ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                <svg className="w-5 h-5" fill={isFlagged ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
                </svg>
                Flag
              </button>
              <button
                onClick={handleCompleteBlock}
                className="px-6 py-3 bg-green-600 hover:bg-green-700 rounded-lg font-semibold transition-colors"
              >
                End Block
              </button>
            </div>
          </div>

          {/* Question Navigator */}
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Question Navigator</h3>
            <div className="grid grid-cols-10 gap-2">
              {blockData.questions.map((q, index) => (
                <button
                  key={index}
                  onClick={() => navigateToQuestion(index)}
                  className={`aspect-square flex items-center justify-center rounded-lg text-sm font-semibold transition-all duration-200 relative ${
                    index === currentQuestionIndex
                      ? 'bg-blue-600 text-white'
                      : q.user_answer
                      ? 'bg-green-500/30 text-green-400 border border-green-500/50'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {index + 1}
                  {q.flagged && (
                    <div className="absolute -top-1 -right-1 w-2 h-2 bg-yellow-400 rounded-full" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      </main>
    );
  }

  return null;
}
