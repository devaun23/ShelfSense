'use client';

import React from 'react';

interface ContributionSource {
  name: string;
  weight: number;
  rawScore: number | null;
  dataPoints: number;
}

interface ScoreBreakdownProps {
  shelfsenseWeight: number;
  shelfsenseScore: number | null;
  shelfsenseQuestions: number;
  nbmeWeight: number;
  nbmeAvg: number | null;
  nbmeCount: number;
  uwsaWeight: number;
  uwsaAvg: number | null;
  uwsaCount: number;
  finalScore: number;
  strategy: string;
}

export function ScoreBreakdown({
  shelfsenseWeight,
  shelfsenseScore,
  shelfsenseQuestions,
  nbmeWeight,
  nbmeAvg,
  nbmeCount,
  uwsaWeight,
  uwsaAvg,
  uwsaCount,
  finalScore,
  strategy,
}: ScoreBreakdownProps) {
  const contributions: ContributionSource[] = [
    {
      name: 'ShelfSense Performance',
      weight: shelfsenseWeight,
      rawScore: shelfsenseScore,
      dataPoints: shelfsenseQuestions,
    },
  ];

  if (nbmeWeight > 0) {
    contributions.push({
      name: 'NBME Self-Assessments',
      weight: nbmeWeight,
      rawScore: nbmeAvg,
      dataPoints: nbmeCount,
    });
  }

  if (uwsaWeight > 0) {
    contributions.push({
      name: 'UWSA Self-Assessments',
      weight: uwsaWeight,
      rawScore: uwsaAvg,
      dataPoints: uwsaCount,
    });
  }

  const getStrategyLabel = (s: string) => {
    switch (s) {
      case 'shelfsense_only':
        return 'ShelfSense Only';
      case 'shelfsense_1_nbme':
        return 'ShelfSense + NBME';
      case 'shelfsense_multi_nbme':
        return 'Multi-NBME Calibrated';
      case 'full_calibration':
        return 'Fully Calibrated';
      case 'shelfsense_uwsa':
        return 'ShelfSense + UWSA';
      default:
        return s;
    }
  };

  const getSourceColor = (name: string) => {
    if (name.includes('ShelfSense')) return '#4169E1';
    if (name.includes('NBME')) return '#10B981';
    if (name.includes('UWSA')) return '#F59E0B';
    return '#6B7280';
  };

  return (
    <div className="space-y-4">
      {/* Strategy badge */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 uppercase tracking-wider">Prediction Method:</span>
        <span className="px-2 py-0.5 bg-gray-800 text-gray-300 text-xs rounded-full">
          {getStrategyLabel(strategy)}
        </span>
      </div>

      {/* Stacked weight bar */}
      <div className="space-y-2">
        <div className="flex h-6 rounded-lg overflow-hidden">
          {contributions.map((c, i) => (
            <div
              key={c.name}
              className="flex items-center justify-center text-xs font-medium text-white transition-all"
              style={{
                width: `${c.weight * 100}%`,
                backgroundColor: getSourceColor(c.name),
                opacity: c.rawScore !== null ? 1 : 0.5,
              }}
              title={`${c.name}: ${Math.round(c.weight * 100)}%`}
            >
              {c.weight >= 0.15 && `${Math.round(c.weight * 100)}%`}
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 text-xs">
          {contributions.map((c) => (
            <div key={c.name} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: getSourceColor(c.name) }}
              />
              <span className="text-gray-400">{c.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Detailed breakdown */}
      <div className="space-y-2">
        {contributions.map((c) => (
          <div
            key={c.name}
            className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg"
          >
            <div className="flex items-center gap-3">
              <div
                className="w-2 h-8 rounded-full"
                style={{ backgroundColor: getSourceColor(c.name) }}
              />
              <div>
                <p className="text-white text-sm font-medium">{c.name}</p>
                <p className="text-gray-500 text-xs">
                  {c.name.includes('ShelfSense')
                    ? `${c.dataPoints} questions`
                    : `${c.dataPoints} score${c.dataPoints !== 1 ? 's' : ''}`}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-white font-semibold">
                {c.rawScore !== null ? Math.round(c.rawScore) : '—'}
              </p>
              <p className="text-gray-500 text-xs">
                {Math.round(c.weight * 100)}% weight
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Final calculation */}
      <div className="pt-3 border-t border-gray-800">
        <div className="flex items-center justify-between">
          <span className="text-gray-400">Weighted Average</span>
          <span className="text-2xl font-semibold text-white">{finalScore}</span>
        </div>
        <p className="text-xs text-gray-600 mt-2">
          Score calculated as weighted average of all sources, with more recent data weighted higher.
        </p>
      </div>
    </div>
  );
}

export default ScoreBreakdown;
