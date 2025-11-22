'use client';

interface ProgressBarProps {
  progress: number; // 0-100
  questionCount?: number;
  totalQuestions?: number;
}

export default function ProgressBar({ progress, questionCount, totalQuestions }: ProgressBarProps) {
  return (
    <div className="fixed top-0 left-0 right-0 bg-gray-900 z-[9999]">
      <div
        className="h-[10px] bg-[#4169E1] transition-all duration-500 ease-out shadow-lg"
        style={{
          width: `${Math.min(100, Math.max(0, progress))}%`,
          boxShadow: '0 0 12px rgba(65, 105, 225, 0.9)'
        }}
      />
      {questionCount !== undefined && totalQuestions !== undefined && (
        <div className="flex justify-center items-center py-1 text-xs text-gray-400">
          <span>{questionCount}/{totalQuestions} ({Math.round(progress)}%)</span>
        </div>
      )}
    </div>
  );
}
