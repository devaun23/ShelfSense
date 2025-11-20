'use client';

interface ProgressBarProps {
  progress: number; // 0-100
}

export default function ProgressBar({ progress }: ProgressBarProps) {
  return (
    <div className="fixed top-0 left-0 right-0 h-[6px] bg-gray-900 z-[9999]">
      <div
        className="h-full bg-[#4169E1] transition-all duration-500 ease-out shadow-lg"
        style={{
          width: `${Math.min(100, Math.max(0, progress))}%`,
          boxShadow: '0 0 12px rgba(65, 105, 225, 0.9)'
        }}
      />
    </div>
  );
}
