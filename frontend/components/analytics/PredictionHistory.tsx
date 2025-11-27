'use client';

import React, { useState } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';

interface PredictionPoint {
  date: string;
  predicted_score: number;
  confidence_low: number;
  confidence_high: number;
  external_score_count: number;
}

interface PredictionHistoryProps {
  data: PredictionPoint[];
  trend: string;
  scoreChange30d: number | null;
  scoreChange7d: number | null;
}

type TimeRange = '7d' | '30d' | '90d';

export function PredictionHistory({
  data,
  trend,
  scoreChange30d,
  scoreChange7d,
}: PredictionHistoryProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');

  // Filter data based on time range
  const filteredData = React.useMemo(() => {
    const now = new Date();
    const cutoffDays = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    const cutoff = new Date(now.getTime() - cutoffDays * 24 * 60 * 60 * 1000);

    return data
      .filter((d) => new Date(d.date) >= cutoff)
      .map((d) => ({
        ...d,
        dateLabel: new Date(d.date).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
        }),
        confidenceRange: [d.confidence_low, d.confidence_high],
      }));
  }, [data, timeRange]);

  const getTrendIcon = () => {
    switch (trend) {
      case 'improving':
        return '↑';
      case 'declining':
        return '↓';
      default:
        return '→';
    }
  };

  const getTrendColor = () => {
    switch (trend) {
      case 'improving':
        return 'text-emerald-400';
      case 'declining':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const CustomTooltip = ({ active, payload, label }: {
    active?: boolean;
    payload?: Array<{ value: number; payload: PredictionPoint & { confidenceRange: number[] } }>;
    label?: string;
  }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-lg">
          <p className="text-white font-medium">{label}</p>
          <p className="text-[#4169E1] text-lg font-semibold">{data.predicted_score}</p>
          <p className="text-gray-400 text-xs">
            Range: {data.confidence_low} - {data.confidence_high}
          </p>
          {data.external_score_count > 0 && (
            <p className="text-gray-500 text-xs mt-1">
              {data.external_score_count} NBME/UWSA score{data.external_score_count !== 1 ? 's' : ''} included
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  if (data.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No prediction history yet.</p>
        <p className="text-gray-600 text-sm mt-1">
          Answer questions daily to build your score prediction timeline.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with trend info */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-4">
          <span className={`text-lg ${getTrendColor()}`}>
            {getTrendIcon()} {trend.charAt(0).toUpperCase() + trend.slice(1)}
          </span>
          {scoreChange30d !== null && (
            <span className="text-sm text-gray-400">
              {scoreChange30d >= 0 ? '+' : ''}{scoreChange30d} pts (30d)
            </span>
          )}
          {scoreChange7d !== null && (
            <span className="text-sm text-gray-500">
              {scoreChange7d >= 0 ? '+' : ''}{scoreChange7d} pts (7d)
            </span>
          )}
        </div>

        {/* Time range buttons */}
        <div className="flex gap-1">
          {(['7d', '30d', '90d'] as TimeRange[]).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 text-sm rounded-full transition-colors ${
                timeRange === range
                  ? 'bg-[#4169E1] text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {range === '7d' ? '7 days' : range === '30d' ? '30 days' : '90 days'}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={filteredData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4169E1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#4169E1" stopOpacity={0.05} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />

            <XAxis
              dataKey="dateLabel"
              stroke="#6B7280"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#374151' }}
            />

            <YAxis
              domain={[190, 300]}
              stroke="#6B7280"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#374151' }}
              tickFormatter={(value) => value.toString()}
            />

            <Tooltip content={<CustomTooltip />} />

            {/* Pass line */}
            <ReferenceLine y={214} stroke="#EF4444" strokeDasharray="5 5" opacity={0.5} />

            {/* Confidence band area */}
            <Area
              type="monotone"
              dataKey="confidenceRange"
              stroke="none"
              fill="url(#confidenceGradient)"
            />

            {/* Main prediction line */}
            <Line
              type="monotone"
              dataKey="predicted_score"
              stroke="#4169E1"
              strokeWidth={2}
              dot={{ fill: '#4169E1', strokeWidth: 0, r: 3 }}
              activeDot={{ fill: '#4169E1', strokeWidth: 2, stroke: '#fff', r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 text-xs text-gray-500">
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-[#4169E1]" />
          <span>Predicted Score</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-[#4169E1]/20 rounded" />
          <span>Confidence Range</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-red-500 border-dashed" style={{ borderTop: '1px dashed' }} />
          <span>Pass Line (214)</span>
        </div>
      </div>
    </div>
  );
}

export default PredictionHistory;
