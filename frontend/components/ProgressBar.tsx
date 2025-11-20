'use client';

interface ProgressBarProps {
  progress: number; // 0-100
}

export default function ProgressBar({ progress }: ProgressBarProps) {
  return (
    <div className="fixed top-0 left-0 right-0 h-[3px] bg-gray-900 z-[9999]">
      <div
        className="h-full bg-[#1E3A5F] transition-all duration-500 ease-out shadow-lg"
        style={{
          width: `${Math.min(100, Math.max(0, progress))}%`,
          boxShadow: '0 0 10px rgba(30, 58, 95, 0.8)'
        }}
      />
    </div>
  );
}
