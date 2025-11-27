'use client';

import React from 'react';

interface ScoreGaugeProps {
  predictedScore: number;
  confidenceInterval: number;
  targetScore?: number | null;
  minScore?: number;
  maxScore?: number;
}

/**
 * Visual gauge showing predicted score with confidence band
 *
 * Score Range: 194 ─────────────────────────────── 300
 *          Pass      Your Range
 *          ↓         ╔════════════╗
 *    ├─────┼─────────║────●───────║────────────────┤
 *    194  214       235   245    255              300
 */
export function ScoreGauge({
  predictedScore,
  confidenceInterval,
  targetScore = null,
  minScore = 194,
  maxScore = 300,
}: ScoreGaugeProps) {
  const range = maxScore - minScore;

  // Calculate positions as percentages
  const scorePosition = ((predictedScore - minScore) / range) * 100;
  const bandStart = ((predictedScore - confidenceInterval - minScore) / range) * 100;
  const bandEnd = ((predictedScore + confidenceInterval - minScore) / range) * 100;
  const bandWidth = bandEnd - bandStart;

  // Pass line position (approximately 214 for Step 2 CK)
  const passLine = 214;
  const passPosition = ((passLine - minScore) / range) * 100;

  // Target score position
  const targetPosition = targetScore
    ? ((targetScore - minScore) / range) * 100
    : null;

  // Score thresholds for labels
  const thresholds = [194, 220, 240, 260, 280, 300];

  return (
    <div className="w-full max-w-2xl mx-auto px-4 py-6">
      {/* Score labels */}
      <div className="flex justify-between text-xs text-gray-500 mb-2 px-1">
        <span>Fail</span>
        <span>Pass</span>
        <span>Average</span>
        <span>Excellent</span>
      </div>

      {/* Main gauge container */}
      <div className="relative h-12">
        {/* Background track */}
        <div className="absolute inset-0 bg-gray-800 rounded-lg overflow-hidden">
          {/* Pass zone (green tint after 214) */}
          <div
            className="absolute top-0 bottom-0 bg-emerald-500/10"
            style={{
              left: `${passPosition}%`,
              right: '0%'
            }}
          />

          {/* Confidence band */}
          <div
            className="absolute top-0 bottom-0 bg-[#4169E1]/20 transition-all duration-500"
            style={{
              left: `${Math.max(0, bandStart)}%`,
              width: `${Math.min(100 - bandStart, bandWidth)}%`
            }}
          />
        </div>

        {/* Pass line marker */}
        <div
          className="absolute top-0 bottom-0 w-px bg-red-500/50"
          style={{ left: `${passPosition}%` }}
        >
          <div className="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] text-red-400">
            Pass
          </div>
        </div>

        {/* Target score marker (if set) */}
        {targetPosition !== null && (
          <div
            className="absolute top-0 bottom-0 w-0.5 border-l-2 border-dashed border-emerald-400/70"
            style={{ left: `${targetPosition}%` }}
          >
            <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[10px] text-emerald-400">
              Goal
            </div>
          </div>
        )}

        {/* Predicted score marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-[#4169E1] rounded-full border-2 border-white shadow-lg transition-all duration-500 z-10"
          style={{ left: `calc(${scorePosition}% - 8px)` }}
        >
          {/* Score tooltip */}
          <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
            {predictedScore}
          </div>
        </div>
      </div>

      {/* Threshold labels */}
      <div className="relative h-6 mt-1">
        {thresholds.map((threshold) => {
          const pos = ((threshold - minScore) / range) * 100;
          return (
            <div
              key={threshold}
              className="absolute text-[10px] text-gray-500 -translate-x-1/2"
              style={{ left: `${pos}%` }}
            >
              {threshold}
            </div>
          );
        })}
      </div>

      {/* Confidence interval label */}
      <div className="text-center mt-2">
        <span className="text-sm text-gray-400">
          Confidence Range: {predictedScore - confidenceInterval} - {predictedScore + confidenceInterval}
        </span>
        <span className="text-xs text-gray-500 ml-2">
          (±{confidenceInterval})
        </span>
      </div>
    </div>
  );
}

export default ScoreGauge;
