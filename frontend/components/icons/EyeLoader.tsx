'use client';

interface EyeLoaderProps {
  size?: number;
  className?: string;
}

export default function EyeLoader({
  size = 48,
  className = '',
}: EyeLoaderProps) {
  const height = size * (20 / 32);

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`}>
      <svg
        width={size}
        height={height}
        viewBox="0 0 32 20"
        fill="none"
        className="animate-pulse"
      >
        {/* Eyebrow - Egyptian style arch */}
        <path
          d="M4 4 Q16 0, 28 4"
          stroke="white"
          strokeWidth="1.5"
          strokeLinecap="round"
          fill="none"
          opacity="0.3"
        />

        {/* Eye outline - almond shape */}
        <path
          d="M2 10 Q8 2, 16 2 Q24 2, 30 10 Q24 18, 16 18 Q8 18, 2 10 Z"
          stroke="white"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          opacity="0.3"
        />

        {/* Extended corner - Eye of Horus style */}
        <path
          d="M29 10 L32 12"
          stroke="white"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.3"
        />
      </svg>

      {/* Spinning dots in center */}
      <div
        className="absolute"
        style={{
          width: size * 0.5,
          height: size * 0.5,
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
        }}
      >
        <div className="relative w-full h-full animate-spin" style={{ animationDuration: '1s' }}>
          {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => {
            const angle = (i * 45) * (Math.PI / 180);
            const radius = 40;
            const x = 50 + radius * Math.cos(angle);
            const y = 50 + radius * Math.sin(angle);
            const opacity = 0.2 + (i / 8) * 0.8;

            return (
              <div
                key={i}
                className="absolute rounded-full bg-white"
                style={{
                  width: '15%',
                  height: '15%',
                  left: `${x}%`,
                  top: `${y}%`,
                  transform: 'translate(-50%, -50%)',
                  opacity,
                }}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
