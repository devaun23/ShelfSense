'use client';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

/**
 * Consistent spinning circles loading animation
 * Use this throughout the app for any loading states
 */
export default function LoadingSpinner({ size = 'md', className = '' }: LoadingSpinnerProps) {
  const sizeConfig = {
    sm: { container: 'w-4 h-4', dot: 'w-1 h-1', translate: '6px' },
    md: { container: 'w-8 h-8', dot: 'w-1.5 h-1.5', translate: '12px' },
    lg: { container: 'w-12 h-12', dot: 'w-2 h-2', translate: '16px' },
  };

  const config = sizeConfig[size];

  return (
    <div className={`relative ${config.container} ${className}`}>
      {[...Array(8)].map((_, i) => (
        <div
          key={i}
          className={`absolute ${config.dot} bg-white rounded-full`}
          style={{
            top: '50%',
            left: '50%',
            transform: `rotate(${i * 45}deg) translateY(-${config.translate})`,
            opacity: 1 - i * 0.1,
            animation: 'spinFade 1s linear infinite',
            animationDelay: `${i * 0.125}s`,
          }}
        />
      ))}
      <style jsx>{`
        @keyframes spinFade {
          0%, 100% { opacity: 0.2; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

/**
 * Full page loading overlay with spinning circles
 */
export function FullPageLoader({ message }: { message?: string }) {
  return (
    <div className="fixed inset-0 bg-black z-50 flex flex-col items-center justify-center">
      <LoadingSpinner size="lg" />
      {message && (
        <p
          className="text-gray-400 text-sm mt-4"
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          {message}
        </p>
      )}
    </div>
  );
}
