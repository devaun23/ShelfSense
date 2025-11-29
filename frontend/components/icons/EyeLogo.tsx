'use client';

import { useState, useEffect, useRef } from 'react';

interface EyeLogoProps {
  size?: number;
  className?: string;
}

export default function EyeLogo({
  size = 48,
  className = '',
}: EyeLogoProps) {
  const [isBlinking, setIsBlinking] = useState(false);
  const blinkTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Calculate dimensions based on size (viewBox is 32x20)
  const width = size;
  const height = size * (20 / 32);

  const handleMouseEnter = () => {
    if (blinkTimeoutRef.current) return; // Don't interrupt if already blinking

    // Single smooth blink
    setIsBlinking(true);

    blinkTimeoutRef.current = setTimeout(() => {
      setIsBlinking(false);
      blinkTimeoutRef.current = null;
    }, 500);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (blinkTimeoutRef.current) {
        clearTimeout(blinkTimeoutRef.current);
      }
    };
  }, []);

  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 32 20"
      fill="none"
      className={`cursor-pointer ${className}`}
      onMouseEnter={handleMouseEnter}
      style={{
        animation: isBlinking ? 'eyeBlink 0.5s ease-in-out' : 'none',
        transformOrigin: 'center center',
      }}
    >
      <style>
        {`
          @keyframes eyeBlink {
            0%, 100% { transform: scaleY(1); }
            50% { transform: scaleY(0.1); }
          }
        `}
      </style>

      {/* Eyebrow - Egyptian style arch */}
      <path
        d="M4 4 Q16 0, 28 4"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        fill="none"
      />

      {/* Eye outline - almond shape */}
      <path
        d="M2 10 Q8 2, 16 2 Q24 2, 30 10 Q24 18, 16 18 Q8 18, 2 10 Z"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />

      {/* Extended corner - Eye of Horus style */}
      <path
        d="M29 10 L32 12"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
      />

      {/* Eye of Horus style pupil - circle with spiral drop */}
      <circle
        cx="16"
        cy="9"
        r="3"
        fill="white"
      />
      {/* Spiral drop below pupil */}
      <path
        d="M16 12 Q14 14, 15 16 Q16 15, 16 14"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
