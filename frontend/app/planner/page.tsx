'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useUser } from '@/contexts/UserContext';
import LoadingSpinner, { FullPageLoader } from '@/components/ui/LoadingSpinner';

const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });

interface Task {
  id: string;
  task_type: string;
  specialty: string | null;
  description: string;
  target_questions: number;
  target_time_minutes: number;
  status: string;
  questions_completed: number;
  time_spent_minutes: number;
  accuracy: number | null;
  priority: number;
}

interface DaySchedule {
  date: string;
  day_name: string;
  tasks: Array<{
    id: string;
    type: string;
    description: string;
    target_questions: number;
    status: string;
  }>;
  total_questions: number;
  total_time: number;
  completed: number;
}

interface FocusArea {
  specialty: string;
  accuracy: number;
  total: number;
}

interface Dashboard {
  status: string;
  exam_date?: string;
  days_remaining?: number;
  weeks_remaining?: number;
  current_phase?: string;
  target_score?: number;
  predicted_score?: number | null;
  score_gap?: number | null;
  on_track?: boolean;
  stats?: {
    total_questions: number;
    accuracy: number;
    weekly_questions: number;
  };
  today?: {
    tasks: Task[];
    total_questions: number;
    completed_questions: number;
    tasks_completed: number;
    tasks_total: number;
  };
  weekly?: {
    week_start: string;
    week_end: string;
    total_questions: number;
    total_time_minutes: number;
    tasks_completed: number;
    tasks_total: number;
    completion_rate: number;
    days: DaySchedule[];
  };
  focus_areas?: FocusArea[];
  message?: string;
}

export default function StudyPlannerPage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Setup form
  const [examDate, setExamDate] = useState('');
  const [targetScore, setTargetScore] = useState(240);
  const [dailyHours, setDailyHours] = useState(3);
  const [studyDays, setStudyDays] = useState(6);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      loadDashboard();
    }
  }, [user, userLoading, router]);

  const loadDashboard = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const response = await fetch(`${apiUrl}/api/study-plan/dashboard?user_id=${user.userId}`);
      if (response.ok) {
        const data = await response.json();
        setDashboard(data);

        if (data.status === 'no_exam_date') {
          setShowSetupModal(true);
        }
      }
    } catch (err) {
      console.error('Error loading dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const createPlan = async () => {
    if (!user || !examDate) return;
    setCreating(true);

    try {
      const response = await fetch(`${apiUrl}/api/study-plan/create?user_id=${user.userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exam_date: new Date(examDate).toISOString(),
          target_score: targetScore,
          daily_hours: dailyHours,
          study_days_per_week: studyDays,
        }),
      });

      if (response.ok) {
        setShowSetupModal(false);
        await loadDashboard();
      }
    } catch (err) {
      console.error('Error creating plan:', err);
    } finally {
      setCreating(false);
    }
  };

  const completeTask = async (taskId: string) => {
    if (!user) return;
    setActionLoading(taskId);

    try {
      await fetch(`${apiUrl}/api/study-plan/task/${taskId}/complete?user_id=${user.userId}`, {
        method: 'POST',
      });
      await loadDashboard();
    } catch (err) {
      console.error('Error completing task:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const skipTask = async (taskId: string) => {
    if (!user) return;
    setActionLoading(taskId);

    try {
      await fetch(`${apiUrl}/api/study-plan/task/${taskId}/skip?user_id=${user.userId}`, {
        method: 'POST',
      });
      await loadDashboard();
    } catch (err) {
      console.error('Error skipping task:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const startTask = (task: Task) => {
    // Navigate to study mode with task context
    if (task.task_type === 'review') {
      router.push('/study-modes/review');
    } else if (task.specialty) {
      router.push(`/study?specialty=${encodeURIComponent(task.specialty)}`);
    } else {
      router.push('/study');
    }
  };

  const getTaskTypeIcon = (type: string) => {
    switch (type) {
      case 'review':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        );
      case 'weak_area':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        );
    }
  };

  const getTaskTypeColor = (type: string) => {
    switch (type) {
      case 'review': return 'text-purple-400 bg-purple-500/20 border-purple-500/30';
      case 'weak_area': return 'text-orange-400 bg-orange-500/20 border-orange-500/30';
      default: return 'text-blue-400 bg-blue-500/20 border-blue-500/30';
    }
  };

  const getPhaseDescription = (phase: string) => {
    switch (phase) {
      case 'foundation': return 'Building your knowledge base';
      case 'strengthening': return 'Targeting weak areas';
      case 'review': return 'High volume review period';
      case 'final': return 'Final preparation';
      default: return '';
    }
  };

  if (loading) {
    return <FullPageLoader message="Loading your study plan..." />;
  }

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${sidebarOpen ? 'md:ml-64' : 'ml-0'}`}>
        <div className="max-w-6xl mx-auto px-8 py-12">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Study Planner
            </h1>
            <p className="text-xl text-gray-400">
              Your personalized adaptive study schedule
            </p>
          </div>

          {dashboard?.status === 'active' && dashboard.days_remaining !== undefined && (
            <>
              {/* Exam Countdown Header */}
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 mb-8">
                <div className="grid md:grid-cols-5 gap-6">
                  <div className="text-center">
                    <div className="text-gray-400 text-sm mb-1">Days Until Exam</div>
                    <div className={`text-5xl font-bold ${dashboard.days_remaining <= 14 ? 'text-red-400' : dashboard.days_remaining <= 30 ? 'text-yellow-400' : 'text-white'}`}>
                      {dashboard.days_remaining}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-gray-400 text-sm mb-1">Target Score</div>
                    <div className="text-5xl font-bold text-blue-400">{dashboard.target_score}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-gray-400 text-sm mb-1">Predicted Score</div>
                    <div className={`text-5xl font-bold ${dashboard.predicted_score && dashboard.predicted_score >= (dashboard.target_score || 0) - 5 ? 'text-green-400' : 'text-yellow-400'}`}>
                      {dashboard.predicted_score || 'N/A'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-gray-400 text-sm mb-1">Current Phase</div>
                    <div className="text-2xl font-bold capitalize">{dashboard.current_phase}</div>
                    <div className="text-xs text-gray-500 mt-1">{getPhaseDescription(dashboard.current_phase || '')}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-gray-400 text-sm mb-1">Status</div>
                    <div className={`text-2xl font-bold ${dashboard.on_track ? 'text-green-400' : 'text-yellow-400'}`}>
                      {dashboard.on_track ? 'On Track' : 'Catching Up'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Today's Tasks */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-2xl font-bold">Today's Tasks</h2>
                  {dashboard.today && (
                    <div className="text-gray-400">
                      {dashboard.today.tasks_completed} / {dashboard.today.tasks_total} completed
                    </div>
                  )}
                </div>

                {dashboard.today && dashboard.today.tasks.length > 0 ? (
                  <div className="space-y-4">
                    {dashboard.today.tasks.map((task) => (
                      <div
                        key={task.id}
                        className={`bg-gray-900 border rounded-xl p-6 transition-all ${
                          task.status === 'completed'
                            ? 'border-green-500/30 opacity-75'
                            : task.status === 'skipped'
                            ? 'border-gray-600 opacity-50'
                            : 'border-gray-700 hover:border-gray-600'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className={`p-3 rounded-lg border ${getTaskTypeColor(task.task_type)}`}>
                              {getTaskTypeIcon(task.task_type)}
                            </div>
                            <div>
                              <h3 className="text-lg font-semibold">{task.description}</h3>
                              <div className="flex items-center gap-4 text-sm text-gray-400 mt-1">
                                <span>{task.target_questions} questions</span>
                                <span>{task.target_time_minutes} min</span>
                                {task.specialty && <span className="text-blue-400">{task.specialty}</span>}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            {task.status === 'completed' ? (
                              <div className="flex items-center gap-2 text-green-400">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                Completed
                              </div>
                            ) : task.status === 'skipped' ? (
                              <div className="text-gray-500">Skipped</div>
                            ) : (
                              <>
                                <button
                                  onClick={() => skipTask(task.id)}
                                  disabled={actionLoading === task.id}
                                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                                >
                                  Skip
                                </button>
                                <button
                                  onClick={() => startTask(task)}
                                  className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-colors"
                                >
                                  Start
                                </button>
                                <button
                                  onClick={() => completeTask(task.id)}
                                  disabled={actionLoading === task.id}
                                  className="px-4 py-2 text-green-400 hover:text-green-300 transition-colors flex items-center gap-1"
                                >
                                  {actionLoading === task.id ? (
                                    <LoadingSpinner size="sm" />
                                  ) : (
                                    <>
                                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                      </svg>
                                      Done
                                    </>
                                  )}
                                </button>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Progress bar for in-progress tasks */}
                        {task.status === 'in_progress' && task.questions_completed > 0 && (
                          <div className="mt-4">
                            <div className="flex justify-between text-sm text-gray-400 mb-1">
                              <span>Progress</span>
                              <span>{task.questions_completed} / {task.target_questions}</span>
                            </div>
                            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-blue-500 transition-all"
                                style={{ width: `${(task.questions_completed / task.target_questions) * 100}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 text-center">
                    <svg className="w-12 h-12 mx-auto text-green-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-lg">All done for today!</p>
                    <p className="text-gray-400 mt-1">Great work! Come back tomorrow for your next tasks.</p>
                  </div>
                )}
              </div>

              {/* Weekly Overview */}
              {dashboard.weekly && (
                <div className="mb-8">
                  <h2 className="text-2xl font-bold mb-4">This Week</h2>
                  <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
                    <div className="grid grid-cols-7 gap-2 mb-6">
                      {dashboard.weekly.days.map((day) => {
                        const isToday = day.date === new Date().toISOString().split('T')[0];
                        const completionRate = day.tasks.length > 0 ? day.completed / day.tasks.length : 0;

                        return (
                          <div
                            key={day.date}
                            className={`p-4 rounded-lg border text-center ${
                              isToday
                                ? 'border-blue-500 bg-blue-500/10'
                                : completionRate === 1
                                ? 'border-green-500/30 bg-green-500/10'
                                : 'border-gray-700'
                            }`}
                          >
                            <div className="text-xs text-gray-500 mb-1">{day.day_name.slice(0, 3)}</div>
                            <div className="text-lg font-semibold">{day.total_questions}</div>
                            <div className="text-xs text-gray-400">questions</div>
                            {completionRate > 0 && (
                              <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-green-500"
                                  style={{ width: `${completionRate * 100}%` }}
                                />
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    <div className="grid grid-cols-4 gap-4 pt-4 border-t border-gray-700">
                      <div className="text-center">
                        <div className="text-2xl font-bold">{dashboard.weekly.total_questions}</div>
                        <div className="text-sm text-gray-400">Total Questions</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold">{Math.round(dashboard.weekly.total_time_minutes / 60)}h</div>
                        <div className="text-sm text-gray-400">Study Time</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold">{dashboard.weekly.tasks_completed}/{dashboard.weekly.tasks_total}</div>
                        <div className="text-sm text-gray-400">Tasks Done</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-400">{dashboard.weekly.completion_rate}%</div>
                        <div className="text-sm text-gray-400">Completion Rate</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Focus Areas */}
              {dashboard.focus_areas && dashboard.focus_areas.length > 0 && (
                <div>
                  <h2 className="text-2xl font-bold mb-4">Focus Areas</h2>
                  <div className="grid md:grid-cols-3 gap-4">
                    {dashboard.focus_areas.map((area) => (
                      <div key={area.specialty} className="bg-gray-900 border border-gray-700 rounded-xl p-6">
                        <h3 className="font-semibold mb-2">{area.specialty}</h3>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-gray-400">Accuracy</span>
                          <span className={`font-bold ${area.accuracy >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
                            {area.accuracy}%
                          </span>
                        </div>
                        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${area.accuracy >= 60 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${area.accuracy}%` }}
                          />
                        </div>
                        <div className="text-xs text-gray-500 mt-2">{area.total} questions attempted</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Edit Plan Button */}
              <div className="mt-8 text-center">
                <button
                  onClick={() => setShowSetupModal(true)}
                  className="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                >
                  Edit Study Plan
                </button>
              </div>
            </>
          )}

          {/* No plan state */}
          {dashboard?.status === 'no_exam_date' && !showSetupModal && (
            <div className="text-center py-16">
              <svg className="w-20 h-20 mx-auto text-gray-600 mb-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <h2 className="text-2xl font-bold mb-2">Create Your Study Plan</h2>
              <p className="text-gray-400 mb-6">Set your exam date and goals to get a personalized daily study schedule</p>
              <button
                onClick={() => setShowSetupModal(true)}
                className="px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-lg text-lg font-semibold transition-colors"
              >
                Get Started
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Setup Modal */}
      {showSetupModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 max-w-lg w-full">
            <h2 className="text-2xl font-bold mb-6">Set Up Your Study Plan</h2>

            <div className="space-y-5">
              <div>
                <label className="block text-sm font-semibold mb-2">Exam Date</label>
                <input
                  type="date"
                  value={examDate}
                  onChange={(e) => setExamDate(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">Target Score</label>
                <input
                  type="number"
                  value={targetScore}
                  onChange={(e) => setTargetScore(parseInt(e.target.value) || 240)}
                  min={194}
                  max={300}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3"
                />
                <p className="text-xs text-gray-500 mt-1">Average passing: 209. Competitive: 240+</p>
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">Hours Available Per Day</label>
                <select
                  value={dailyHours}
                  onChange={(e) => setDailyHours(parseFloat(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3"
                >
                  <option value={1}>1 hour</option>
                  <option value={2}>2 hours</option>
                  <option value={3}>3 hours</option>
                  <option value={4}>4 hours</option>
                  <option value={5}>5 hours</option>
                  <option value={6}>6+ hours</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">Study Days Per Week</label>
                <select
                  value={studyDays}
                  onChange={(e) => setStudyDays(parseInt(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3"
                >
                  <option value={5}>5 days</option>
                  <option value={6}>6 days</option>
                  <option value={7}>7 days</option>
                </select>
              </div>
            </div>

            <div className="flex gap-4 mt-8">
              <button
                onClick={() => setShowSetupModal(false)}
                className="flex-1 px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={createPlan}
                disabled={creating || !examDate}
                className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
              >
                {creating ? (
                  <>
                    <LoadingSpinner size="sm" />
                    Creating...
                  </>
                ) : (
                  'Create Plan'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
