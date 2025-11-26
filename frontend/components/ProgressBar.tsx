'use client';

interface ProgressBarProps {
  progress: number; // 0-100
  questionCount?: number;
  totalQuestions?: number;
}

export default function ProgressBar({ progress, questionCount, totalQuestions }: ProgressBarProps) {
  return (
    <div className="fixed top-0 left-0 right-0 bg-black z-[9999]">
      {/* Minimal progress bar - 2px height, no glow */}
      <div
        className="h-[2px] bg-[#4169E1] transition-all duration-300 ease-out"
        style={{
          width: `${Math.min(100, Math.max(0, progress))}%`
        }}
      />
      {/* Text stats - subtle gray */}
      {questionCount !== undefined && totalQuestions !== undefined && (
        <div className="flex justify-center items-center py-2 text-sm text-gray-500">
          <span>{questionCount}/{totalQuestions}</span>
        </div>
      )}
    </div>
  );
}
