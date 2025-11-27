'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface PeerComparisonData {
  user_stats: {
    total_questions: number;
    accuracy: number;
    predicted_score: number | null;
    streak: number;
  };
  comparison: {
    total_peers?: number;
    message?: string;
    percentiles?: {
      accuracy: number;
      questions_answered: number;
      accuracy_label: string;
      questions_label: string;
    };
    platform_averages?: {
      accuracy: number;
      median_accuracy: number;
      questions_per_user: number;
    };
    accuracy_vs_average?: number;
    questions_vs_average?: number;
  };
  distribution?: {
    accuracy_buckets: Record<string, number>;
    user_bucket: string;
  };
  specialty_comparison?: Record<string, {
    user_accuracy: number | null;
    user_questions: number;
    platform_accuracy: number | null;
    platform_questions: number;
    difference: number | null;
  }>;
}

interface PeerComparisonProps {
  userId: string;
}

export default function PeerComparison({ userId }: PeerComparisonProps) {
  const [data, setData] = useState<PeerComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPeerData();
  }, [userId]);

  const fetchPeerData = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/analytics/peer-comparison?user_id=${userId}`);

      if (response.ok) {
        const result = await response.json();
        setData(result);
        setError(null);
      } else {
        setError('Failed to load peer comparison data');
      }
    } catch (err) {
      console.error('Error fetching peer data:', err);
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse text-gray-500 text-center py-8">
        Loading peer comparison...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-8 text-gray-500">
        {error || 'No peer data available'}
      </div>
    );
  }

  // Check if we have enough peer data
  if (data.comparison.message) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-400 mb-2">{data.comparison.message}</p>
        <p className="text-sm text-gray-600">Keep studying! More data will be available soon.</p>
      </div>
    );
  }

  // Prepare distribution chart data (memoized to prevent recomputation)
  const distributionData = useMemo(() =>
    data.distribution ? Object.entries(data.distribution.accuracy_buckets).map(([bucket, count]) => ({
      bucket,
      count,
      isUser: bucket === data.distribution?.user_bucket
    })) : [],
    [data.distribution]
  );

  // Prepare specialty comparison data (memoized)
  const specialtyData = useMemo(() =>
    data.specialty_comparison ? Object.entries(data.specialty_comparison)
      .filter(([_, stats]) => stats.user_accuracy !== null && stats.platform_accuracy !== null)
      .map(([specialty, stats]) => ({
        name: specialty.replace(' and ', ' & ').split(' ').slice(0, 2).join(' '),
        user: stats.user_accuracy,
        platform: stats.platform_accuracy,
        difference: stats.difference
      })) : [],
    [data.specialty_comparison]
  );

  const getPercentileColor = (percentile: number) => {
    if (percentile >= 75) return 'text-emerald-400';
    if (percentile >= 50) return 'text-blue-400';
    if (percentile >= 25) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getDifferenceColor = (diff: number | null) => {
    if (diff === null) return 'text-gray-500';
    if (diff > 5) return 'text-emerald-400';
    if (diff > 0) return 'text-emerald-400/70';
    if (diff > -5) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="space-y-6">
      {/* Percentile Rankings */}
      {data.comparison.percentiles && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5 text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Accuracy Percentile</p>
            <p className={`text-3xl font-bold ${getPercentileColor(data.comparison.percentiles.accuracy)}`}>
              {data.comparison.percentiles.accuracy}%
            </p>
            <p className="text-sm text-gray-400 mt-1">
              {data.comparison.percentiles.accuracy_label}
            </p>
          </div>
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5 text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Activity Percentile</p>
            <p className={`text-3xl font-bold ${getPercentileColor(data.comparison.percentiles.questions_answered)}`}>
              {data.comparison.percentiles.questions_answered}%
            </p>
            <p className="text-sm text-gray-400 mt-1">
              {data.comparison.percentiles.questions_label}
            </p>
          </div>
        </div>
      )}

      {/* Vs Platform Average */}
      {data.comparison.platform_averages && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
          <h4 className="text-sm font-medium text-gray-400 mb-4">Compared to Platform Average</h4>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-2xl font-bold text-white">{data.user_stats.accuracy}%</span>
                <span className={`text-sm ${getDifferenceColor(data.comparison.accuracy_vs_average || 0)}`}>
                  {(data.comparison.accuracy_vs_average || 0) >= 0 ? '+' : ''}{data.comparison.accuracy_vs_average}%
                </span>
              </div>
              <p className="text-xs text-gray-500">Your Accuracy (avg: {data.comparison.platform_averages.accuracy}%)</p>
            </div>
            <div>
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-2xl font-bold text-white">{data.user_stats.total_questions}</span>
                <span className={`text-sm ${getDifferenceColor(data.comparison.questions_vs_average || 0)}`}>
                  {(data.comparison.questions_vs_average || 0) >= 0 ? '+' : ''}{Math.round(data.comparison.questions_vs_average || 0)}
                </span>
              </div>
              <p className="text-xs text-gray-500">Questions (avg: {Math.round(data.comparison.platform_averages.questions_per_user)})</p>
            </div>
          </div>
        </div>
      )}

      {/* Accuracy Distribution Chart */}
      {distributionData.length > 0 && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
          <h4 className="text-sm font-medium text-gray-400 mb-4">Accuracy Distribution</h4>
          <p className="text-xs text-gray-600 mb-3">Where you stand among {data.comparison.total_peers} users</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={distributionData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
              <XAxis type="number" stroke="#6B7280" fontSize={11} />
              <YAxis dataKey="bucket" type="category" stroke="#6B7280" fontSize={11} width={50} />
              <Tooltip
                contentStyle={{ backgroundColor: '#111', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#9CA3AF' }}
                formatter={(value: number) => [`${value} users`, 'Count']}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {distributionData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.isUser ? '#4169E1' : '#374151'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-center text-gray-500 mt-2">
            <span className="inline-block w-3 h-3 bg-[#4169E1] rounded mr-1"></span>
            Your accuracy range
          </p>
        </div>
      )}

      {/* Specialty Comparison */}
      {specialtyData.length > 0 && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
          <h4 className="text-sm font-medium text-gray-400 mb-4">Specialty Performance vs Platform</h4>
          <div className="space-y-3">
            {specialtyData.map((spec) => (
              <div key={spec.name} className="flex items-center justify-between">
                <span className="text-sm text-gray-400 w-28 truncate">{spec.name}</span>
                <div className="flex-1 mx-4">
                  <div className="flex h-2 gap-1">
                    <div
                      className="bg-[#4169E1] rounded-l"
                      style={{ width: `${spec.user}%` }}
                      title={`You: ${spec.user}%`}
                    />
                    <div
                      className="bg-gray-600 rounded-r"
                      style={{ width: `${100 - (spec.user || 0)}%` }}
                    />
                  </div>
                  <div className="flex h-2 gap-1 mt-1">
                    <div
                      className="bg-gray-500 rounded-l"
                      style={{ width: `${spec.platform}%` }}
                      title={`Platform: ${spec.platform}%`}
                    />
                    <div
                      className="bg-gray-700 rounded-r"
                      style={{ width: `${100 - (spec.platform || 0)}%` }}
                    />
                  </div>
                </div>
                <span className={`text-sm font-medium w-16 text-right ${getDifferenceColor(spec.difference)}`}>
                  {spec.difference !== null ? (spec.difference >= 0 ? '+' : '') + spec.difference + '%' : '—'}
                </span>
              </div>
            ))}
          </div>
          <div className="flex justify-center gap-6 mt-4 text-xs text-gray-500">
            <span><span className="inline-block w-3 h-3 bg-[#4169E1] rounded mr-1"></span>You</span>
            <span><span className="inline-block w-3 h-3 bg-gray-500 rounded mr-1"></span>Platform Avg</span>
          </div>
        </div>
      )}

      {/* Total Peers */}
      <p className="text-xs text-center text-gray-600">
        Based on {data.comparison.total_peers} anonymous users with 10+ questions answered
      </p>
    </div>
  );
}
