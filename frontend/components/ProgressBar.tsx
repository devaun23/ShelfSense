'use client';

interface ProgressBarProps {
  progress: number; // 0-100
  questionCount?: number;
  totalQuestions?: number;
}

export default function ProgressBar({ progress, questionCount, totalQuestions }: ProgressBarProps) {
  const clampedProgress = Math.min(100, Math.max(0, progress));

  return (
    <div className="fixed top-0 left-0 right-0 bg-black z-[9999]">
      {/* Minimal progress bar - 2px height, no glow */}
      <div
        role="progressbar"
        aria-valuenow={clampedProgress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={
          questionCount !== undefined && totalQuestions !== undefined
            ? `Question ${questionCount} of ${totalQuestions}, ${Math.round(clampedProgress)}% complete`
            : `${Math.round(clampedProgress)}% complete`
        }
        className="h-[2px] bg-[#4169E1] transition-all duration-300 ease-out"
        style={{
          width: `${clampedProgress}%`
        }}
      />
      {/* Text stats - subtle gray */}
      {questionCount !== undefined && totalQuestions !== undefined && (
        <div className="flex justify-center items-center py-2 text-sm text-gray-500">
          <span aria-hidden="true">{questionCount}/{totalQuestions}</span>
          <span className="sr-only">Question {questionCount} of {totalQuestions}</span>
        </div>
      )}
    </div>
  );
}
