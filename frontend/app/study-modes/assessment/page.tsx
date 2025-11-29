'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useUser } from '@/contexts/UserContext';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });

interface Assessment {
  id: string;
  name: string;
  total_blocks: number;
  questions_per_block: number;
  time_per_block_minutes: number;
  status: string;
  current_block: number;
  started_at: string | null;
  completed_at: string | null;
  percentage_score: number | null;
  predicted_step2_score: number | null;
  percentile_rank: number | null;
  created_at: string;
}

interface Stats {
  assessments_completed: number;
  avg_score: number | null;
  best_score: number | null;
  avg_percentile: number | null;
  improvement_trend: string | null;
}

export default function AssessmentPage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [newName, setNewName] = useState('Practice Assessment');
  const [newBlocks, setNewBlocks] = useState(4);
  const [newQuestionsPerBlock, setNewQuestionsPerBlock] = useState(40);
  const [newTimePerBlock, setNewTimePerBlock] = useState(60);

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      loadAssessments();
      loadStats();
    }
  }, [user, userLoading, router]);

  const loadAssessments = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/self-assessment/list?user_id=${user.userId}`);
      if (response.ok) {
        const data = await response.json();
        setAssessments(data);
      }
    } catch (err) {
      console.error('Error loading assessments:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    if (!user) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/self-assessment/stats/comparison?user_id=${user.userId}`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  const createAssessment = async () => {
    if (!user) return;
    setCreating(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/self-assessment/create?user_id=${user.userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newName,
          total_blocks: newBlocks,
          questions_per_block: newQuestionsPerBlock,
          time_per_block_minutes: newTimePerBlock,
        }),
      });

      if (response.ok) {
        const assessment = await response.json();
        setShowCreateModal(false);
        router.push(`/study-modes/assessment/${assessment.id}`);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to create assessment');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-400 bg-green-500/20 border-green-500/30';
      case 'in_progress': return 'text-blue-400 bg-blue-500/20 border-blue-500/30';
      case 'abandoned': return 'text-red-400 bg-red-500/20 border-red-500/30';
      default: return 'text-gray-400 bg-gray-500/20 border-gray-500/30';
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const inProgressAssessment = assessments.find(a => a.status === 'in_progress');

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        <div className="max-w-6xl mx-auto px-8 py-12">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <button
                onClick={() => router.push('/study-modes')}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <h1 className="text-4xl font-bold" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                Self Assessment
              </h1>
            </div>
            <p className="text-xl text-gray-400">
              Full length NBME style practice exams with score predictions
            </p>
          </div>

          {/* Stats Cards */}
          {stats && stats.assessments_completed > 0 && (
            <div className="grid md:grid-cols-4 gap-4 mb-8">
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
                <div className="text-gray-400 text-sm mb-1">Assessments Taken</div>
                <div className="text-3xl font-bold">{stats.assessments_completed}</div>
              </div>
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
                <div className="text-gray-400 text-sm mb-1">Average Score</div>
                <div className="text-3xl font-bold">{stats.avg_score ? `${stats.avg_score}%` : 'N/A'}</div>
              </div>
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
                <div className="text-gray-400 text-sm mb-1">Best Score</div>
                <div className="text-3xl font-bold text-green-400">{stats.best_score ? `${stats.best_score}%` : 'N/A'}</div>
              </div>
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
                <div className="text-gray-400 text-sm mb-1">Avg Percentile</div>
                <div className="text-3xl font-bold">{stats.avg_percentile ? `${stats.avg_percentile}th` : 'N/A'}</div>
              </div>
            </div>
          )}

          {/* In Progress Banner */}
          {inProgressAssessment && (
            <div className="mb-8 bg-blue-500/10 border border-blue-500/30 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-blue-400 mb-1">Assessment In Progress</h3>
                  <p className="text-gray-400">
                    {inProgressAssessment.name} &bull; Block {inProgressAssessment.current_block} of {inProgressAssessment.total_blocks}
                  </p>
                </div>
                <button
                  onClick={() => router.push(`/study-modes/assessment/${inProgressAssessment.id}`)}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Create New Assessment Button */}
          <div className="mb-8">
            <button
              onClick={() => setShowCreateModal(true)}
              disabled={!!inProgressAssessment}
              className={`w-full p-6 rounded-xl border-2 border-dashed transition-all ${
                inProgressAssessment
                  ? 'border-gray-700 text-gray-600 cursor-not-allowed'
                  : 'border-gray-600 hover:border-blue-500/50 text-gray-400 hover:text-white'
              }`}
            >
              <div className="flex items-center justify-center gap-3">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span className="text-lg font-semibold">
                  {inProgressAssessment ? 'Complete current assessment first' : 'Start New Assessment'}
                </span>
              </div>
              {!inProgressAssessment && (
                <p className="text-sm mt-2 text-gray-500">
                  4 blocks × 40 questions × 60 minutes = Full NBME simulation
                </p>
              )}
            </button>
          </div>

          {/* Past Assessments */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Past Assessments</h2>
            {loading ? (
              <div className="flex justify-center py-12">
                <LoadingSpinner size="lg" />
              </div>
            ) : assessments.filter(a => a.status !== 'in_progress').length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-lg">No completed assessments yet</p>
                <p className="text-sm mt-1">Start your first assessment to see your predicted score</p>
              </div>
            ) : (
              <div className="space-y-4">
                {assessments.filter(a => a.status !== 'in_progress').map((assessment) => (
                  <button
                    key={assessment.id}
                    onClick={() => router.push(`/study-modes/assessment/${assessment.id}/results`)}
                    className="w-full bg-gray-900 border border-gray-700 hover:border-gray-600 rounded-xl p-6 text-left transition-all"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold">{assessment.name}</h3>
                          <span className={`text-xs px-2 py-1 rounded-full border ${getStatusColor(assessment.status)}`}>
                            {assessment.status.replace('_', ' ')}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500">
                          {formatDate(assessment.created_at)} &bull; {assessment.total_blocks} blocks × {assessment.questions_per_block} questions
                        </p>
                      </div>
                      {assessment.status === 'completed' && assessment.percentage_score !== null && (
                        <div className="text-right">
                          <div className="text-3xl font-bold text-green-400">{assessment.percentage_score}%</div>
                          <div className="text-sm text-gray-500">
                            Predicted: {assessment.predicted_step2_score}
                          </div>
                          {assessment.percentile_rank && (
                            <div className="text-xs text-gray-500">
                              {assessment.percentile_rank}th percentile
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Create Assessment Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 max-w-lg w-full">
            <h2 className="text-2xl font-bold mb-6">Create New Assessment</h2>

            {error && (
              <div className="mb-4 p-4 bg-red-900/20 border border-red-500/50 rounded-lg text-red-400">
                {error}
              </div>
            )}

            <div className="space-y-5">
              <div>
                <label className="block text-sm font-semibold mb-2">Assessment Name</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3"
                  placeholder="Practice Assessment"
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-semibold mb-2">Blocks</label>
                  <select
                    value={newBlocks}
                    onChange={(e) => setNewBlocks(parseInt(e.target.value))}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3"
                  >
                    <option value={1}>1</option>
                    <option value={2}>2</option>
                    <option value={4}>4 (NBME)</option>
                    <option value={8}>8</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2">Questions/Block</label>
                  <select
                    value={newQuestionsPerBlock}
                    onChange={(e) => setNewQuestionsPerBlock(parseInt(e.target.value))}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3"
                  >
                    <option value={20}>20</option>
                    <option value={40}>40 (NBME)</option>
                    <option value={50}>50</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2">Minutes/Block</label>
                  <select
                    value={newTimePerBlock}
                    onChange={(e) => setNewTimePerBlock(parseInt(e.target.value))}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3"
                  >
                    <option value={30}>30</option>
                    <option value={45}>45</option>
                    <option value={60}>60 (NBME)</option>
                    <option value={90}>90</option>
                  </select>
                </div>
              </div>

              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-sm text-gray-400 mb-2">Assessment Summary</div>
                <div className="text-lg font-semibold">
                  {newBlocks * newQuestionsPerBlock} questions in {newBlocks * newTimePerBlock} minutes
                </div>
                <div className="text-sm text-gray-500 mt-1">
                  ~{Math.round(newTimePerBlock / newQuestionsPerBlock * 60)} seconds per question
                </div>
              </div>
            </div>

            <div className="flex gap-4 mt-8">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={createAssessment}
                disabled={creating}
                className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
              >
                {creating ? (
                  <>
                    <LoadingSpinner size="sm" />
                    Creating...
                  </>
                ) : (
                  'Create Assessment'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
