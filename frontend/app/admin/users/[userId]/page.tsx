'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useUser } from '@/contexts/UserContext';

interface UserDetail {
  user_id: string;
  full_name: string;
  first_name: string;
  email: string;
  is_admin: boolean;
  email_verified: boolean;
  target_score: number | null;
  exam_date: string | null;
  created_at: string;
  last_login: string | null;
  total_attempts: number;
  correct_attempts: number;
  accuracy: number | null;
  attempts_last_7_days: number;
  attempts_last_30_days: number;
  streak_days: number;
  specialty_breakdown: Record<string, { total: number; correct: number; accuracy: number }> | null;
}

interface AttemptItem {
  id: string;
  question_id: string;
  question_preview: string;
  specialty: string | null;
  selected_answer: string;
  is_correct: boolean;
  time_spent: number | null;
  created_at: string;
}

interface AttemptsResponse {
  attempts: AttemptItem[];
  total: number;
  page: number;
  per_page: number;
}

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.userId as string;
  const { getAccessToken, user: currentUser } = useUser();

  const [userDetail, setUserDetail] = useState<UserDetail | null>(null);
  const [attempts, setAttempts] = useState<AttemptItem[]>([]);
  const [attemptsTotal, setAttemptsTotal] = useState(0);
  const [attemptsPage, setAttemptsPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [attemptsLoading, setAttemptsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'attempts' | 'specialties'>('overview');

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const attemptsPerPage = 15;

  useEffect(() => {
    fetchUserDetail();
  }, [userId]);

  useEffect(() => {
    if (activeTab === 'attempts') {
      fetchAttempts();
    }
  }, [activeTab, attemptsPage]);

  const fetchUserDetail = async () => {
    try {
      setLoading(true);
      const token = await getAccessToken();
      const response = await fetch(`${apiUrl}/api/admin/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('User not found');
        }
        throw new Error('Failed to fetch user details');
      }

      const data = await response.json();
      setUserDetail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchAttempts = async () => {
    try {
      setAttemptsLoading(true);
      const token = await getAccessToken();
      const params = new URLSearchParams({
        page: attemptsPage.toString(),
        per_page: attemptsPerPage.toString(),
      });

      const response = await fetch(`${apiUrl}/api/admin/users/${userId}/attempts?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error('Failed to fetch attempts');

      const data: AttemptsResponse = await response.json();
      setAttempts(data.attempts);
      setAttemptsTotal(data.total);
    } catch (err) {
      console.error('Error fetching attempts:', err);
    } finally {
      setAttemptsLoading(false);
    }
  };

  const toggleAdmin = async () => {
    if (!userDetail) return;
    if (userDetail.user_id === currentUser?.userId) {
      alert("You cannot change your own admin status");
      return;
    }

    const action = userDetail.is_admin ? 'revoke' : 'grant';
    if (!confirm(`Are you sure you want to ${action} admin access for this user?`)) {
      return;
    }

    try {
      setActionLoading(true);
      const token = await getAccessToken();
      const response = await fetch(`${apiUrl}/api/admin/users/${userId}/admin`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_admin: !userDetail.is_admin }),
      });

      if (!response.ok) throw new Error('Failed to update admin status');

      await fetchUserDetail();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setActionLoading(false);
    }
  };

  const totalAttemptsPages = Math.ceil(attemptsTotal / attemptsPerPage);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4169E1]" />
      </div>
    );
  }

  if (error || !userDetail) {
    return (
      <div className="space-y-4">
        <Link href="/admin/users" className="text-[#4169E1] hover:underline text-sm">
          &larr; Back to Users
        </Link>
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
          {error || 'User not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link href="/admin/users" className="text-[#4169E1] hover:underline text-sm mb-2 block">
            &larr; Back to Users
          </Link>
          <h1 className="text-2xl font-semibold text-white">{userDetail.full_name}</h1>
          <p className="text-gray-400">{userDetail.email}</p>
        </div>
        <div className="flex items-center gap-3">
          {userDetail.is_admin && (
            <span className="px-2 py-1 text-xs bg-red-900/30 text-red-400 rounded">Admin</span>
          )}
          {userDetail.email_verified && (
            <span className="px-2 py-1 text-xs bg-green-900/30 text-green-400 rounded">Verified</span>
          )}
          <button
            onClick={toggleAdmin}
            disabled={actionLoading || userDetail.user_id === currentUser?.userId}
            className={`text-sm px-4 py-2 rounded transition-colors ${
              userDetail.user_id === currentUser?.userId
                ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                : userDetail.is_admin
                ? 'bg-red-900/30 text-red-400 hover:bg-red-900/50'
                : 'bg-[#4169E1]/20 text-[#4169E1] hover:bg-[#4169E1]/30'
            }`}
          >
            {actionLoading ? 'Updating...' : userDetail.is_admin ? 'Revoke Admin' : 'Make Admin'}
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <p className="text-2xl font-semibold text-white">{userDetail.total_attempts}</p>
          <p className="text-xs text-gray-500">Total Attempts</p>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <p className="text-2xl font-semibold text-white">
            {userDetail.accuracy !== null ? `${userDetail.accuracy.toFixed(0)}%` : 'N/A'}
          </p>
          <p className="text-xs text-gray-500">Accuracy</p>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <p className="text-2xl font-semibold text-white">{userDetail.streak_days}</p>
          <p className="text-xs text-gray-500">Day Streak</p>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <p className="text-2xl font-semibold text-white">{userDetail.attempts_last_7_days}</p>
          <p className="text-xs text-gray-500">Last 7 Days</p>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <p className="text-2xl font-semibold text-white">{userDetail.attempts_last_30_days}</p>
          <p className="text-xs text-gray-500">Last 30 Days</p>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <p className="text-2xl font-semibold text-white">
            {userDetail.target_score || 'Not set'}
          </p>
          <p className="text-xs text-gray-500">Target Score</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-800">
        <nav className="flex gap-4">
          {(['overview', 'attempts', 'specialties'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'text-[#4169E1] border-[#4169E1]'
                  : 'text-gray-400 border-transparent hover:text-white'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Account Info */}
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <h3 className="text-sm font-medium text-white mb-4">Account Information</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">User ID</span>
                <span className="text-sm text-white font-mono">{userDetail.user_id.slice(0, 8)}...</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">First Name</span>
                <span className="text-sm text-white">{userDetail.first_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Email Verified</span>
                <span className="text-sm text-white">{userDetail.email_verified ? 'Yes' : 'No'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Joined</span>
                <span className="text-sm text-white">
                  {new Date(userDetail.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Last Login</span>
                <span className="text-sm text-white">
                  {userDetail.last_login
                    ? new Date(userDetail.last_login).toLocaleString()
                    : 'Never'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Exam Date</span>
                <span className="text-sm text-white">
                  {userDetail.exam_date
                    ? new Date(userDetail.exam_date).toLocaleDateString()
                    : 'Not set'}
                </span>
              </div>
            </div>
          </div>

          {/* Performance Summary */}
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <h3 className="text-sm font-medium text-white mb-4">Performance Summary</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Questions Attempted</span>
                <span className="text-sm text-white">{userDetail.total_attempts}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Correct Answers</span>
                <span className="text-sm text-white">{userDetail.correct_attempts}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Incorrect Answers</span>
                <span className="text-sm text-white">
                  {userDetail.total_attempts - userDetail.correct_attempts}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Overall Accuracy</span>
                <span className={`text-sm ${
                  userDetail.accuracy !== null
                    ? userDetail.accuracy >= 70
                      ? 'text-green-400'
                      : userDetail.accuracy >= 50
                      ? 'text-yellow-400'
                      : 'text-red-400'
                    : 'text-white'
                }`}>
                  {userDetail.accuracy !== null ? `${userDetail.accuracy.toFixed(1)}%` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Specialties Studied</span>
                <span className="text-sm text-white">
                  {userDetail.specialty_breakdown
                    ? Object.keys(userDetail.specialty_breakdown).length
                    : 0}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'attempts' && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <div className="p-4 border-b border-gray-800">
            <h3 className="text-sm font-medium text-white">Recent Attempts ({attemptsTotal})</h3>
          </div>
          {attemptsLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#4169E1]" />
            </div>
          ) : attempts.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No attempts found</div>
          ) : (
            <>
              <div className="divide-y divide-gray-800">
                {attempts.map((attempt) => (
                  <div key={attempt.id} className="p-4 hover:bg-gray-800/50">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white line-clamp-2">{attempt.question_preview}</p>
                        <div className="flex items-center gap-3 mt-2">
                          {attempt.specialty && (
                            <span className="text-xs text-gray-500">{attempt.specialty}</span>
                          )}
                          <span className="text-xs text-gray-500">
                            {new Date(attempt.created_at).toLocaleString()}
                          </span>
                          {attempt.time_spent && (
                            <span className="text-xs text-gray-500">
                              {Math.floor(attempt.time_spent / 60)}:{(attempt.time_spent % 60).toString().padStart(2, '0')}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-400">Answer: {attempt.selected_answer}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          attempt.is_correct
                            ? 'bg-green-900/30 text-green-400'
                            : 'bg-red-900/30 text-red-400'
                        }`}>
                          {attempt.is_correct ? 'Correct' : 'Incorrect'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {totalAttemptsPages > 1 && (
                <div className="p-4 border-t border-gray-800 flex items-center justify-between">
                  <span className="text-sm text-gray-400">
                    Page {attemptsPage} of {totalAttemptsPages}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setAttemptsPage(Math.max(1, attemptsPage - 1))}
                      disabled={attemptsPage === 1}
                      className="px-2 py-1 text-xs bg-gray-800 text-gray-300 rounded hover:bg-gray-700 disabled:opacity-50"
                    >
                      Prev
                    </button>
                    <button
                      onClick={() => setAttemptsPage(Math.min(totalAttemptsPages, attemptsPage + 1))}
                      disabled={attemptsPage === totalAttemptsPages}
                      className="px-2 py-1 text-xs bg-gray-800 text-gray-300 rounded hover:bg-gray-700 disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === 'specialties' && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <div className="p-4 border-b border-gray-800">
            <h3 className="text-sm font-medium text-white">Performance by Specialty</h3>
          </div>
          {!userDetail.specialty_breakdown || Object.keys(userDetail.specialty_breakdown).length === 0 ? (
            <div className="p-8 text-center text-gray-500">No specialty data available</div>
          ) : (
            <div className="divide-y divide-gray-800">
              {Object.entries(userDetail.specialty_breakdown)
                .sort((a, b) => b[1].total - a[1].total)
                .map(([specialty, stats]) => (
                  <div key={specialty} className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-white">{specialty}</span>
                      <span className={`text-sm ${
                        stats.accuracy >= 70
                          ? 'text-green-400'
                          : stats.accuracy >= 50
                          ? 'text-yellow-400'
                          : 'text-red-400'
                      }`}>
                        {stats.accuracy.toFixed(0)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex-1 bg-gray-800 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            stats.accuracy >= 70
                              ? 'bg-green-500'
                              : stats.accuracy >= 50
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }`}
                          style={{ width: `${stats.accuracy}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 whitespace-nowrap">
                        {stats.correct}/{stats.total} correct
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
