'use client';

import { useState, useEffect, useCallback } from 'react';

interface SessionTimerProps {
  initialSeconds: number;
  onTimeUp?: () => void;
  onTick?: (remaining: number) => void;
  paused?: boolean;
  showWarning?: boolean;
  warningThreshold?: number;
  className?: string;
}

export default function SessionTimer({
  initialSeconds,
  onTimeUp,
  onTick,
  paused = false,
  showWarning = true,
  warningThreshold = 300, // 5 minutes
  className = ''
}: SessionTimerProps) {
  const [timeRemaining, setTimeRemaining] = useState(initialSeconds);
  const [isWarning, setIsWarning] = useState(false);
  const [isCritical, setIsCritical] = useState(false);

  useEffect(() => {
    if (paused || timeRemaining <= 0) return;

    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        const newTime = prev - 1;

        // Update warning states
        if (showWarning && newTime <= warningThreshold) {
          setIsWarning(true);
        }
        if (showWarning && newTime <= 60) {
          setIsCritical(true);
        }

        // Callback
        if (onTick) {
          onTick(newTime);
        }

        // Time's up
        if (newTime <= 0 && onTimeUp) {
          onTimeUp();
          clearInterval(interval);
        }

        return Math.max(0, newTime);
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [paused, timeRemaining, onTimeUp, onTick, showWarning, warningThreshold]);

  const formatTime = useCallback((seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const getTimerColor = () => {
    if (isCritical) return 'text-red-500 animate-pulse';
    if (isWarning) return 'text-yellow-500';
    return 'text-white';
  };

  const progressPercentage = (timeRemaining / initialSeconds) * 100;

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Timer Icon */}
      <svg
        className={`w-5 h-5 ${getTimerColor()}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>

      {/* Time Display */}
      <span className={`font-mono text-lg font-bold ${getTimerColor()}`}>
        {formatTime(timeRemaining)}
      </span>

      {/* Progress Bar */}
      <div className="w-24 h-2 bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-1000 ease-linear ${
            isCritical ? 'bg-red-500' : isWarning ? 'bg-yellow-500' : 'bg-blue-500'
          }`}
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      {/* Paused Indicator */}
      {paused && (
        <span className="text-yellow-500 text-sm font-medium">PAUSED</span>
      )}
    </div>
  );
}

// Compact version for header display
export function CompactTimer({
  seconds,
  warning = false,
  critical = false
}: {
  seconds: number;
  warning?: boolean;
  critical?: boolean;
}) {
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const getColor = () => {
    if (critical) return 'text-red-500 animate-pulse';
    if (warning) return 'text-yellow-500';
    return 'text-zinc-300';
  };

  return (
    <div className={`flex items-center gap-1 ${getColor()}`}>
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span className="font-mono text-sm font-medium">{formatTime(seconds)}</span>
    </div>
  );
}
