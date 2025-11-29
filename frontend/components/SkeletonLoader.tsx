'use client';

// Skeleton components for loading states
// Uses motion-safe for users who prefer reduced motion
// Eye-based loading animation for brand consistency

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
  const sizes = {
    sm: 24,
    md: 40,
    lg: 64,
  };
  const pixelSize = sizes[size];
  const dotSize = pixelSize * 0.15;
  const radius = pixelSize * 0.4;

  return (
    <div
      className="relative inline-flex items-center justify-center"
      role="status"
      aria-label={label}
      style={{ width: pixelSize, height: pixelSize }}
    >
      {/* Spinning dots only */}
      <div
        className="relative animate-spin"
        style={{
          width: radius * 2,
          height: radius * 2,
          animationDuration: '1s',
        }}
      >
        {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => {
          const angle = (i * 45 - 90) * (Math.PI / 180);
          const x = radius + radius * 0.85 * Math.cos(angle);
          const y = radius + radius * 0.85 * Math.sin(angle);
          const opacity = 0.2 + (i / 8) * 0.8;

          return (
            <div
              key={i}
              className="absolute rounded-full bg-white"
              style={{
                width: dotSize,
                height: dotSize,
                left: x - dotSize / 2,
                top: y - dotSize / 2,
                opacity,
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

// Full page loading screen with eye animation
export function PageLoader({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center gap-6">
      <LoadingSpinner size="lg" label={message} />
      <p className="text-gray-400 font-serif text-lg animate-pulse">{message}</p>
    </div>
  );
}
