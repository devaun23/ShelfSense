'use client';

import { useState } from 'react';

interface ConfidenceSelectorProps {
  value: number | null;
  onChange: (level: number) => void;
  disabled?: boolean;
}

const CONFIDENCE_LEVELS = [
  { level: 1, label: 'Guessing', description: 'No idea', color: 'text-red-400', bgColor: 'bg-red-500/20', borderColor: 'border-red-500/50' },
  { level: 2, label: 'Unsure', description: 'Probably wrong', color: 'text-orange-400', bgColor: 'bg-orange-500/20', borderColor: 'border-orange-500/50' },
  { level: 3, label: 'Maybe', description: '50/50', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', borderColor: 'border-yellow-500/50' },
  { level: 4, label: 'Likely', description: 'Probably right', color: 'text-blue-400', bgColor: 'bg-blue-500/20', borderColor: 'border-blue-500/50' },
  { level: 5, label: 'Certain', description: 'Definitely right', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20', borderColor: 'border-emerald-500/50' },
];

export default function ConfidenceSelector({ value, onChange, disabled }: ConfidenceSelectorProps) {
  const [hoveredLevel, setHoveredLevel] = useState<number | null>(null);

  const displayLevel = hoveredLevel ?? value;
  const currentLevel = displayLevel ? CONFIDENCE_LEVELS.find(l => l.level === displayLevel) : null;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="flex items-center gap-1 sm:gap-2">
        <span className="text-xs text-gray-500 mr-1 sm:mr-2">Confidence:</span>
        {/* Touch-optimized button container with minimum 44px touch targets */}
        <div className="flex gap-0.5 sm:gap-1" role="radiogroup" aria-label="Select your confidence level">
          {CONFIDENCE_LEVELS.map(({ level, label, color, bgColor, borderColor }) => {
            const isSelected = value === level;
            const isHovered = hoveredLevel === level;
            const isActive = isSelected || isHovered;

            return (
              <button
                key={level}
                onClick={() => !disabled && onChange(level)}
                onMouseEnter={() => !disabled && setHoveredLevel(level)}
                onMouseLeave={() => setHoveredLevel(null)}
                disabled={disabled}
                role="radio"
                aria-checked={isSelected}
                aria-label={`${label} - confidence level ${level} of 5`}
                className={`
                  min-w-[44px] min-h-[44px] w-10 h-10 sm:w-11 sm:h-11
                  rounded-full flex items-center justify-center text-sm font-medium
                  transition-all duration-150 touch-manipulation
                  ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer active:scale-95'}
                  ${isActive
                    ? `${bgColor} ${borderColor} border-2 ${color}`
                    : 'bg-gray-800/50 border border-gray-700 text-gray-500'
                  }
                `}
                style={{ WebkitTapHighlightColor: 'transparent' }}
              >
                {level}
              </button>
            );
          })}
        </div>
      </div>

      {/* Label display */}
      <div className="h-5 text-xs sm:text-sm" aria-live="polite">
        {currentLevel && (
          <span className={currentLevel.color}>
            {currentLevel.label} - {currentLevel.description}
          </span>
        )}
      </div>
    </div>
  );
}
