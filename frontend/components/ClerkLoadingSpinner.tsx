'use client';

/**
 * Loading spinner shown while Clerk is initializing
 */
export default function ClerkLoadingSpinner() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="relative w-12 h-12">
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 bg-white rounded-full"
            style={{
              top: '50%',
              left: '50%',
              transform: `rotate(${i * 45}deg) translateY(-16px)`,
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
    </div>
  );
}
