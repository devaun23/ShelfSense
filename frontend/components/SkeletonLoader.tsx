'use client';

// Skeleton components for loading states
// Uses motion-safe for users who prefer reduced motion

export function SkeletonText({ className = '' }: { className?: string }) {
  return (
    <div
      className={`motion-safe:animate-pulse bg-gray-800 rounded ${className}`}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div
      className={`motion-safe:animate-pulse bg-gray-900 border border-gray-800 rounded-2xl ${className}`}
      aria-hidden="true"
    >
      <div className="p-6">
        <SkeletonText className="h-8 w-12 mb-3" />
        <SkeletonText className="h-5 w-32 mb-1" />
        <SkeletonText className="h-3 w-20" />
      </div>
    </div>
  );
}

export function SkeletonQuestion() {
  return (
    <div
      className="motion-safe:animate-pulse"
      role="status"
      aria-label="Loading question"
      aria-busy="true"
    >
      <span className="sr-only">Loading question content...</span>
      {/* Header skeleton */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <SkeletonText className="h-8 w-8 rounded-lg" />
          <SkeletonText className="h-6 w-24 rounded-full" />
          <SkeletonText className="h-4 w-20" />
        </div>
        <SkeletonText className="h-4 w-32" />
      </div>

      {/* Vignette skeleton */}
      <div className="mb-8 space-y-2">
        <SkeletonText className="h-5 w-full" />
        <SkeletonText className="h-5 w-full" />
        <SkeletonText className="h-5 w-full" />
        <SkeletonText className="h-5 w-3/4" />
      </div>

      {/* Choices skeleton */}
      <div className="space-y-2 mb-8">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="border border-gray-800 rounded-xl p-4 flex items-center gap-4">
            <SkeletonText className="h-7 w-7 rounded-full" />
            <SkeletonText className="h-4 flex-1" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonSpecialtyGrid() {
  return (
    <div
      className="grid grid-cols-2 md:grid-cols-4 gap-4 motion-safe:animate-pulse"
      role="status"
      aria-label="Loading specialties"
      aria-busy="true"
    >
      <span className="sr-only">Loading specialty options...</span>
      {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
        <div key={i} className="p-6 bg-gray-900 border border-gray-800 rounded-2xl" aria-hidden="true">
          <SkeletonText className="h-8 w-8 mb-3 rounded" />
          <SkeletonText className="h-5 w-28 mb-1" />
          <SkeletonText className="h-3 w-16" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonStats() {
  return (
    <div
      className="flex justify-center gap-12 motion-safe:animate-pulse"
      role="status"
      aria-label="Loading statistics"
      aria-busy="true"
    >
      <span className="sr-only">Loading your statistics...</span>
      {[1, 2, 3].map((i) => (
        <div key={i} className="text-center" aria-hidden="true">
          <SkeletonText className="h-9 w-16 mx-auto mb-1" />
          <SkeletonText className="h-3 w-24 mx-auto" />
        </div>
      ))}
    </div>
  );
}

export function LoadingSpinner({ size = 'md', label = 'Loading' }: { size?: 'sm' | 'md' | 'lg'; label?: string }) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
  };

  return (
    <svg
      className={`motion-safe:animate-spin text-[#4169E1] ${sizeClasses[size]}`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      role="status"
      aria-label={label}
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
