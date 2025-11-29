'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useUser } from '@/contexts/UserContext';
import { FullPageLoader } from '@/components/ui/LoadingSpinner';

const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });

interface BlockResult {
  block_number: number;
  questions_total: number;
  questions_answered: number;
  questions_correct: number;
  accuracy: number;
  time_spent_seconds: number;
  avg_time_per_question: number;
  questions: Array<{
    question_id: string;
    user_answer: string | null;
    correct_answer: string | null;
    is_correct: boolean;
    source: string | null;
  }>;
}

interface AssessmentResults {
  id: string;
  name: string;
  status: string;
  total_questions: number;
  questions_answered: number;
  questions_correct: number;
  raw_score: number;
  percentage_score: number;
  predicted_step2_score: number;
  confidence_interval_low: number;
  confidence_interval_high: number;
  percentile_rank: number;
  total_time_seconds: number;
  avg_time_per_question: number;
  performance_by_system: Record<string, number>;
  performance_by_difficulty: Record<string, number>;
  blocks: BlockResult[];
  readiness_verdict: string;
  recommendations: string[];
}

export default function AssessmentResultsPage() {
  const router = useRouter();
  const params = useParams();
  const assessmentId = params.id as string;
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [results, setResults] = useState<AssessmentResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedBlock, setExpandedBlock] = useState<number | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user && assessmentId) {
      loadResults();
    }
  }, [user, userLoading, assessmentId, router]);

  const loadResults = async () => {
    try {
      const response = await fetch(
        `${apiUrl}/api/self-assessment/${assessmentId}/results?user_id=${user?.userId}`
      );

      if (!response.ok) {
        const errData = await response.json();
        setError(errData.detail || 'Failed to load results');
        return;
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError('Network error loading results');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getVerdictStyle = (verdict: string) => {
    switch (verdict) {
      case 'Ready to Test':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'Almost Ready':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'Need More Preparation':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      default:
        return 'bg-red-500/20 text-red-400 border-red-500/30';
    }
  };

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  if (loading) {
    return <FullPageLoader message="Loading results..." />;
  }

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

  if (!results) return null;

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${sidebarOpen ? 'md:ml-64' : 'ml-0'}`}>
        <div className="max-w-5xl mx-auto px-8 py-12">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <button
                onClick={() => router.push('/study-modes/assessment')}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <h1 className="text-4xl font-bold" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                Assessment Results
              </h1>
            </div>
            <p className="text-xl text-gray-400">{results.name}</p>
          </div>

          {/* Main Score Card */}
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 mb-8">
            <div className="grid md:grid-cols-4 gap-8">
              {/* Score */}
              <div className="text-center">
                <div className="text-gray-400 text-sm mb-2">Your Score</div>
                <div className={`text-6xl font-bold ${getScoreColor(results.percentage_score)}`}>
                  {results.percentage_score}%
                </div>
                <div className="text-gray-500 mt-2">
                  {results.questions_correct} / {results.total_questions} correct
                </div>
              </div>

              {/* Predicted Score */}
              <div className="text-center">
                <div className="text-gray-400 text-sm mb-2">Predicted Step 2 CK</div>
                <div className="text-6xl font-bold text-blue-400">
                  {results.predicted_step2_score}
                </div>
                <div className="text-gray-500 mt-2">
                  Range: {results.confidence_interval_low} to {results.confidence_interval_high}
                </div>
              </div>

              {/* Percentile */}
              <div className="text-center">
                <div className="text-gray-400 text-sm mb-2">Percentile Rank</div>
                <div className="text-6xl font-bold text-purple-400">
                  {results.percentile_rank}
                </div>
                <div className="text-gray-500 mt-2">
                  out of 100
                </div>
              </div>

              {/* Time */}
              <div className="text-center">
                <div className="text-gray-400 text-sm mb-2">Total Time</div>
                <div className="text-6xl font-bold text-gray-300">
                  {formatTime(results.total_time_seconds)}
                </div>
                <div className="text-gray-500 mt-2">
                  {results.avg_time_per_question}s avg per question
                </div>
              </div>
            </div>

            {/* Readiness Verdict */}
            <div className="mt-8 pt-8 border-t border-gray-700">
              <div className={`inline-block px-6 py-3 rounded-lg border text-lg font-semibold ${getVerdictStyle(results.readiness_verdict)}`}>
                {results.readiness_verdict}
              </div>
            </div>
          </div>

          {/* Performance Breakdown */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            {/* By System */}
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
              <h3 className="text-lg font-bold mb-4">Performance by System</h3>
              <div className="space-y-3">
                {Object.entries(results.performance_by_system)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .map(([system, score]) => (
                    <div key={system}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-400">{system}</span>
                        <span className={getScoreColor(score as number)}>{score}%</span>
                      </div>
                      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            (score as number) >= 70 ? 'bg-green-500' : (score as number) >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${score}%` }}
                        />
                      </div>
                    </div>
                  ))}
              </div>
            </div>

            {/* By Difficulty */}
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
              <h3 className="text-lg font-bold mb-4">Performance by Difficulty</h3>
              <div className="space-y-3">
                {['easy', 'medium', 'hard'].map((diff) => {
                  const score = results.performance_by_difficulty[diff] || 0;
                  return (
                    <div key={diff}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-400 capitalize">{diff}</span>
                        <span className={getScoreColor(score)}>{score}%</span>
                      </div>
                      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            score >= 70 ? 'bg-green-500' : score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${score}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Recommendations */}
          {results.recommendations.length > 0 && (
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-6 mb-8">
              <h3 className="text-lg font-bold mb-4 text-blue-400">Recommendations</h3>
              <ul className="space-y-2">
                {results.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start gap-3 text-gray-300">
                    <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Block Results */}
          <div className="mb-8">
            <h3 className="text-xl font-bold mb-4">Block Results</h3>
            <div className="space-y-4">
              {results.blocks.map((block) => (
                <div key={block.block_number} className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
                  <button
                    onClick={() => setExpandedBlock(expandedBlock === block.block_number ? null : block.block_number)}
                    className="w-full p-6 flex items-center justify-between hover:bg-gray-800 transition-colors"
                  >
                    <div className="flex items-center gap-6">
                      <span className="text-lg font-semibold">Block {block.block_number}</span>
                      <span className={`text-2xl font-bold ${getScoreColor(block.accuracy)}`}>
                        {block.accuracy}%
                      </span>
                      <span className="text-gray-500">
                        {block.questions_correct}/{block.questions_total} correct
                      </span>
                      <span className="text-gray-500">
                        {formatTime(block.time_spent_seconds)}
                      </span>
                    </div>
                    <svg
                      className={`w-5 h-5 text-gray-400 transition-transform ${expandedBlock === block.block_number ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {expandedBlock === block.block_number && (
                    <div className="border-t border-gray-700 p-6">
                      <div className="grid grid-cols-10 gap-2">
                        {block.questions.map((q, index) => (
                          <div
                            key={index}
                            className={`aspect-square flex items-center justify-center rounded-lg text-sm font-semibold ${
                              q.is_correct
                                ? 'bg-green-500/30 text-green-400 border border-green-500/50'
                                : q.user_answer
                                ? 'bg-red-500/30 text-red-400 border border-red-500/50'
                                : 'bg-gray-800 text-gray-500'
                            }`}
                            title={q.source || 'Unknown'}
                          >
                            {index + 1}
                          </div>
                        ))}
                      </div>
                      <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 bg-green-500/30 rounded border border-green-500/50" />
                          <span>Correct</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 bg-red-500/30 rounded border border-red-500/50" />
                          <span>Incorrect</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 bg-gray-800 rounded" />
                          <span>Unanswered</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-4">
            <button
              onClick={() => router.push('/study-modes/assessment')}
              className="flex-1 px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-lg text-lg font-semibold transition-colors"
            >
              Take Another Assessment
            </button>
            <button
              onClick={() => router.push('/analytics')}
              className="flex-1 px-8 py-4 bg-gray-700 hover:bg-gray-600 rounded-lg text-lg transition-colors"
            >
              View Analytics
            </button>
          </div>
        </div>
      </main>
    </>
  );
}
