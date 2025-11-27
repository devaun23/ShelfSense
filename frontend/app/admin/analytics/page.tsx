'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { Button, Badge, CollapsibleSection } from '@/components/ui';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

// Types
interface ActivityOverview {
  dau: number;
  wau: number;
  mau: number;
  total_users: number;
  stickiness: number;
  sessions: {
    total: number;
    completed: number;
    completion_rate: number;
    avg_duration_minutes: number;
    total_time_hours: number;
  };
  questions_answered: number;
  avg_questions_per_dau: number;
  period_days: number;
}

interface ActivityTrends {
  daily_data: Array<{
    date: string;
    active_users: number;
    questions_answered: number;
  }>;
  period_days: number;
}

interface FeatureUsage {
  study_modes: Record<string, number>;
  ai_chat_messages: number;
  ai_questions_generated: number;
  period_days: number;
}

interface RetentionOverview {
  total_users: number;
  activated_users: number;
  activation_rate: number;
  day1_retention: number;
  day7_retention: number;
  day30_retention: number;
  retained_day1: number;
  retained_day7: number;
  retained_day30: number;
}

interface CohortData {
  cohort_week: string;
  cohort_size: number;
  retention: Array<{
    week: number;
    retained: number;
    rate: number;
  }>;
}

interface UserHealthDistribution {
  distribution: {
    active: number;
    at_risk: number;
    churned: number;
    new: number;
  };
  percentages: {
    active: number;
    at_risk: number;
    churned: number;
    new: number;
  };
  total_users: number;
}

interface AtRiskUser {
  user_id: string;
  email: string;
  full_name: string;
  days_since_activity: number | null;
  questions_last_7_days: number;
  churn_risk_score: number;
  risk_factors: string[];
}

type TabType = 'overview' | 'retention' | 'health' | 'batch';

const HEALTH_COLORS: Record<string, string> = {
  active: '#10b981',
  at_risk: '#f59e0b',
  churned: '#ef4444',
  new: '#6b7280',
};

export default function AdminAnalyticsPage() {
  const router = useRouter();
  const { user, isLoading: userLoading, getAccessToken } = useUser();

  // Data states
  const [activityOverview, setActivityOverview] = useState<ActivityOverview | null>(null);
  const [activityTrends, setActivityTrends] = useState<ActivityTrends | null>(null);
  const [featureUsage, setFeatureUsage] = useState<FeatureUsage | null>(null);
  const [retentionOverview, setRetentionOverview] = useState<RetentionOverview | null>(null);
  const [cohortData, setCohortData] = useState<CohortData[] | null>(null);
  const [healthDistribution, setHealthDistribution] = useState<UserHealthDistribution | null>(null);
  const [atRiskUsers, setAtRiskUsers] = useState<AtRiskUser[] | null>(null);

  // UI states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchResult, setBatchResult] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Redirect non-admin users
  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (!userLoading && user && !user.isAdmin) {
      router.push('/');
      return;
    }

    if (user && user.isAdmin) {
      fetchAllData();
    }
  }, [user, userLoading, router]);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      setError(null);
      const token = await getAccessToken();

      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      // Fetch all data in parallel
      const [overviewRes, trendsRes, featureRes, retentionRes, cohortRes, healthRes, atRiskRes] = await Promise.all([
        fetch(`${apiUrl}/api/admin/analytics/overview?days=30`, { headers }),
        fetch(`${apiUrl}/api/admin/analytics/trends?days=30`, { headers }),
        fetch(`${apiUrl}/api/admin/analytics/feature-usage?days=30`, { headers }),
        fetch(`${apiUrl}/api/admin/analytics/retention`, { headers }),
        fetch(`${apiUrl}/api/admin/analytics/cohorts?weeks=8`, { headers }),
        fetch(`${apiUrl}/api/admin/analytics/user-health`, { headers }),
        fetch(`${apiUrl}/api/admin/analytics/users-at-risk?limit=20`, { headers }),
      ]);

      if (overviewRes.ok) setActivityOverview(await overviewRes.json());
      if (trendsRes.ok) setActivityTrends(await trendsRes.json());
      if (featureRes.ok) setFeatureUsage(await featureRes.json());
      if (retentionRes.ok) setRetentionOverview(await retentionRes.json());
      if (cohortRes.ok) setCohortData(await cohortRes.json());
      if (healthRes.ok) setHealthDistribution(await healthRes.json());
      if (atRiskRes.ok) setAtRiskUsers(await atRiskRes.json());

      if (!overviewRes.ok) {
        setError('Failed to load analytics. Make sure you have admin access.');
      }
    } catch (err) {
      console.error('Error fetching admin analytics:', err);
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const runBatchJob = async (jobType: string) => {
    try {
      setBatchRunning(true);
      setBatchResult(null);
      const token = await getAccessToken();

      const response = await fetch(`${apiUrl}/api/admin/analytics/batch/${jobType}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const result = await response.json();
        setBatchResult(`Success: ${JSON.stringify(result, null, 2)}`);
        // Refresh data after batch job
        fetchAllData();
      } else {
        setBatchResult('Failed to run batch job');
      }
    } catch (err) {
      setBatchResult('Error running batch job');
    } finally {
      setBatchRunning(false);
    }
  };

  // Format number with commas
  const formatNumber = (num: number) => num.toLocaleString();

  // Loading state
  if (userLoading || loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4169E1]" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
        <div className="mb-4">{error}</div>
        <Button onClick={fetchAllData} size="sm">Retry</Button>
      </div>
    );
  }

  // Prepare chart data
  const healthPieData = healthDistribution ? [
    { name: 'Active', value: healthDistribution.distribution.active, color: HEALTH_COLORS.active },
    { name: 'At Risk', value: healthDistribution.distribution.at_risk, color: HEALTH_COLORS.at_risk },
    { name: 'Churned', value: healthDistribution.distribution.churned, color: HEALTH_COLORS.churned },
    { name: 'New', value: healthDistribution.distribution.new, color: HEALTH_COLORS.new },
  ] : [];

  const featureChartData = featureUsage ? Object.entries(featureUsage.study_modes).map(([mode, count]) => ({
    name: mode.charAt(0).toUpperCase() + mode.slice(1),
    value: count,
  })) : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Usage Analytics</h1>
          <p className="text-gray-400 text-sm mt-1">Platform-wide engagement metrics</p>
        </div>
        <Button onClick={fetchAllData} variant="ghost" size="sm">
          Refresh
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {(['overview', 'retention', 'health', 'batch'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div>
          {/* Overview Tab */}
          {activeTab === 'overview' && activityOverview && (
            <div className="space-y-6">
              {/* Key Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard
                  label="Daily Active Users"
                  value={activityOverview.dau}
                  subtext="Today"
                />
                <MetricCard
                  label="Weekly Active Users"
                  value={activityOverview.wau}
                  subtext="Last 7 days"
                />
                <MetricCard
                  label="Monthly Active Users"
                  value={activityOverview.mau}
                  subtext="Last 30 days"
                />
                <MetricCard
                  label="Stickiness"
                  value={`${activityOverview.stickiness}%`}
                  subtext="DAU/MAU ratio"
                />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard
                  label="Total Users"
                  value={activityOverview.total_users}
                  subtext="All registered"
                />
                <MetricCard
                  label="Questions Answered"
                  value={formatNumber(activityOverview.questions_answered)}
                  subtext="Last 30 days"
                />
                <MetricCard
                  label="Avg Q/DAU"
                  value={activityOverview.avg_questions_per_dau.toFixed(1)}
                  subtext="Questions per active user"
                />
                <MetricCard
                  label="Study Sessions"
                  value={activityOverview.sessions.total}
                  subtext={`${activityOverview.sessions.completion_rate}% completed`}
                />
              </div>

              {/* Activity Trend Chart */}
              {activityTrends && activityTrends.daily_data.length > 0 && (
                <CollapsibleSection title="Activity Trends (30 Days)" defaultOpen={true}>
                  <div className="bg-gray-900/50 rounded-xl p-4">
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={activityTrends.daily_data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis
                          dataKey="date"
                          stroke="#9CA3AF"
                          tick={{ fontSize: 12 }}
                          tickFormatter={(value) => value.slice(5)}
                        />
                        <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1f2937',
                            border: 'none',
                            borderRadius: '8px',
                          }}
                        />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="active_users"
                          name="Active Users"
                          stroke="#3b82f6"
                          strokeWidth={2}
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="questions_answered"
                          name="Questions"
                          stroke="#10b981"
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CollapsibleSection>
              )}

              {/* Feature Usage */}
              {featureUsage && featureChartData.length > 0 && (
                <CollapsibleSection title="Feature Usage" defaultOpen={true}>
                  <div className="bg-gray-900/50 rounded-xl p-4">
                    <div className="grid md:grid-cols-2 gap-6">
                      <div>
                        <h4 className="text-sm text-gray-400 mb-3">Study Modes</h4>
                        <ResponsiveContainer width="100%" height={200}>
                          <BarChart data={featureChartData} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis type="number" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
                            <YAxis dataKey="name" type="category" stroke="#9CA3AF" tick={{ fontSize: 12 }} width={80} />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: '#1f2937',
                                border: 'none',
                                borderRadius: '8px',
                              }}
                            />
                            <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="space-y-4">
                        <div className="bg-gray-800 rounded-lg p-4">
                          <div className="text-2xl font-bold text-blue-400">{formatNumber(featureUsage.ai_chat_messages)}</div>
                          <div className="text-sm text-gray-400">AI Chat Messages</div>
                        </div>
                        <div className="bg-gray-800 rounded-lg p-4">
                          <div className="text-2xl font-bold text-emerald-400">{formatNumber(featureUsage.ai_questions_generated)}</div>
                          <div className="text-sm text-gray-400">AI Questions Generated</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CollapsibleSection>
              )}
            </div>
          )}

          {/* Retention Tab */}
          {activeTab === 'retention' && retentionOverview && (
            <div className="space-y-6">
              {/* Retention Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard
                  label="Activation Rate"
                  value={`${retentionOverview.activation_rate}%`}
                  subtext={`${retentionOverview.activated_users} of ${retentionOverview.total_users} users`}
                />
                <MetricCard
                  label="Day 1 Retention"
                  value={`${retentionOverview.day1_retention}%`}
                  subtext={`${retentionOverview.retained_day1} users`}
                />
                <MetricCard
                  label="Day 7 Retention"
                  value={`${retentionOverview.day7_retention}%`}
                  subtext={`${retentionOverview.retained_day7} users`}
                />
                <MetricCard
                  label="Day 30 Retention"
                  value={`${retentionOverview.day30_retention}%`}
                  subtext={`${retentionOverview.retained_day30} users`}
                />
              </div>

              {/* Cohort Table */}
              {cohortData && cohortData.length > 0 && (
                <CollapsibleSection title="Cohort Retention" defaultOpen={true}>
                  <div className="bg-gray-900/50 rounded-xl p-4 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-gray-400 border-b border-gray-700">
                          <th className="text-left py-2 px-3">Cohort Week</th>
                          <th className="text-center py-2 px-3">Size</th>
                          {[0, 1, 2, 3, 4, 5, 6, 7].map((week) => (
                            <th key={week} className="text-center py-2 px-3">W{week}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {cohortData.slice(0, 8).map((cohort) => (
                          <tr key={cohort.cohort_week} className="border-b border-gray-800">
                            <td className="py-2 px-3 text-gray-300">{cohort.cohort_week}</td>
                            <td className="text-center py-2 px-3">{cohort.cohort_size}</td>
                            {[0, 1, 2, 3, 4, 5, 6, 7].map((week) => {
                              const retention = cohort.retention.find((r) => r.week === week);
                              return (
                                <td
                                  key={week}
                                  className="text-center py-2 px-3"
                                  style={{
                                    backgroundColor: retention
                                      ? `rgba(16, 185, 129, ${retention.rate / 100})`
                                      : 'transparent',
                                  }}
                                >
                                  {retention ? `${retention.rate}%` : '-'}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CollapsibleSection>
              )}
            </div>
          )}

          {/* Health Tab */}
          {activeTab === 'health' && healthDistribution && (
            <div className="space-y-6">
              {/* Health Distribution */}
              <div className="grid md:grid-cols-2 gap-6">
                <div className="bg-gray-900/50 rounded-xl p-6">
                  <h3 className="text-lg font-semibold mb-4">User Health Distribution</h3>
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={healthPieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                      >
                        {healthPieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1f2937',
                          border: 'none',
                          borderRadius: '8px',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="space-y-3">
                  <HealthStatusCard
                    label="Active"
                    count={healthDistribution.distribution.active}
                    percentage={healthDistribution.percentages.active}
                    color="emerald"
                    description="Engaged in last 7 days"
                  />
                  <HealthStatusCard
                    label="At Risk"
                    count={healthDistribution.distribution.at_risk}
                    percentage={healthDistribution.percentages.at_risk}
                    color="yellow"
                    description="Low activity, may churn"
                  />
                  <HealthStatusCard
                    label="Churned"
                    count={healthDistribution.distribution.churned}
                    percentage={healthDistribution.percentages.churned}
                    color="red"
                    description="No activity 14+ days"
                  />
                  <HealthStatusCard
                    label="New"
                    count={healthDistribution.distribution.new}
                    percentage={healthDistribution.percentages.new}
                    color="gray"
                    description="No activity yet"
                  />
                </div>
              </div>

              {/* At Risk Users Table */}
              {atRiskUsers && atRiskUsers.length > 0 && (
                <CollapsibleSection title="At-Risk Users" defaultOpen={true}>
                  <div className="bg-gray-900/50 rounded-xl p-4 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-gray-400 border-b border-gray-700">
                          <th className="text-left py-2 px-3">User</th>
                          <th className="text-center py-2 px-3">Days Inactive</th>
                          <th className="text-center py-2 px-3">Q Last 7d</th>
                          <th className="text-center py-2 px-3">Risk Score</th>
                          <th className="text-left py-2 px-3">Risk Factors</th>
                        </tr>
                      </thead>
                      <tbody>
                        {atRiskUsers.map((user) => (
                          <tr key={user.user_id} className="border-b border-gray-800">
                            <td className="py-2 px-3">
                              <div className="text-gray-200">{user.full_name}</div>
                              <div className="text-xs text-gray-500">{user.email}</div>
                            </td>
                            <td className="text-center py-2 px-3 text-yellow-400">
                              {user.days_since_activity ?? '-'}
                            </td>
                            <td className="text-center py-2 px-3">{user.questions_last_7_days}</td>
                            <td className="text-center py-2 px-3">
                              <span
                                className={`px-2 py-1 rounded text-xs ${
                                  user.churn_risk_score > 0.7
                                    ? 'bg-red-900/50 text-red-400'
                                    : user.churn_risk_score > 0.4
                                    ? 'bg-yellow-900/50 text-yellow-400'
                                    : 'bg-gray-800 text-gray-400'
                                }`}
                              >
                                {(user.churn_risk_score * 100).toFixed(0)}%
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              <div className="flex flex-wrap gap-1">
                                {user.risk_factors.slice(0, 2).map((factor, i) => (
                                  <Badge key={i} variant="danger" size="sm">
                                    {factor.replace(/_/g, ' ')}
                                  </Badge>
                                ))}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CollapsibleSection>
              )}
            </div>
          )}

          {/* Batch Jobs Tab */}
          {activeTab === 'batch' && (
            <div className="space-y-6">
              <div className="bg-gray-900/50 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-4">Batch Processing Jobs</h3>
                <p className="text-gray-400 text-sm mb-6">
                  Run batch jobs to update pre-aggregated analytics data. These jobs compute metrics
                  and store them for faster dashboard loading.
                </p>

                <div className="grid md:grid-cols-2 gap-4">
                  <BatchJobCard
                    title="Daily Metrics"
                    description="Compute DAU/WAU/MAU, session counts, and daily stats"
                    onRun={() => runBatchJob('daily-metrics')}
                    running={batchRunning}
                  />
                  <BatchJobCard
                    title="User Engagement"
                    description="Update engagement scores and health status for all users"
                    onRun={() => runBatchJob('user-engagement')}
                    running={batchRunning}
                  />
                  <BatchJobCard
                    title="Cohort Retention"
                    description="Calculate weekly cohort retention rates"
                    onRun={() => runBatchJob('cohort-retention')}
                    running={batchRunning}
                  />
                  <BatchJobCard
                    title="Run All Jobs"
                    description="Execute all batch jobs in sequence"
                    onRun={() => runBatchJob('all')}
                    running={batchRunning}
                    primary
                  />
                </div>

                {batchResult && (
                  <div className="mt-6 p-4 bg-gray-800 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-300 mb-2">Result:</h4>
                    <pre className="text-xs text-gray-400 whitespace-pre-wrap">{batchResult}</pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
    </div>
  );
}

// Component: Metric Card
function MetricCard({
  label,
  value,
  subtext,
}: {
  label: string;
  value: string | number;
  subtext: string;
}) {
  return (
    <div className="bg-gray-900/50 rounded-xl p-4">
      <div className="text-sm text-gray-400 mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{subtext}</div>
    </div>
  );
}

// Component: Health Status Card
function HealthStatusCard({
  label,
  count,
  percentage,
  color,
  description,
}: {
  label: string;
  count: number;
  percentage: number;
  color: 'emerald' | 'yellow' | 'red' | 'gray';
  description: string;
}) {
  const colorClasses = {
    emerald: 'border-emerald-500/30 bg-emerald-900/20',
    yellow: 'border-yellow-500/30 bg-yellow-900/20',
    red: 'border-red-500/30 bg-red-900/20',
    gray: 'border-gray-500/30 bg-gray-800/50',
  };

  const textClasses = {
    emerald: 'text-emerald-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
    gray: 'text-gray-400',
  };

  return (
    <div className={`rounded-lg border p-4 ${colorClasses[color]}`}>
      <div className="flex justify-between items-center">
        <div>
          <div className={`font-semibold ${textClasses[color]}`}>{label}</div>
          <div className="text-xs text-gray-500">{description}</div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-white">{count}</div>
          <div className="text-sm text-gray-400">{percentage}%</div>
        </div>
      </div>
    </div>
  );
}

// Component: Batch Job Card
function BatchJobCard({
  title,
  description,
  onRun,
  running,
  primary,
}: {
  title: string;
  description: string;
  onRun: () => void;
  running: boolean;
  primary?: boolean;
}) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h4 className="font-medium text-white mb-1">{title}</h4>
      <p className="text-sm text-gray-400 mb-3">{description}</p>
      <Button
        onClick={onRun}
        disabled={running}
        variant={primary ? 'primary' : 'ghost'}
        size="sm"
      >
        {running ? 'Running...' : 'Run Job'}
      </Button>
    </div>
  );
}
