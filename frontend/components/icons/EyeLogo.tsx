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

  // Calculate dimensions based on size (viewBox is 32x18)
  const width = size;
  const height = size * (18 / 32);

  const handleMouseEnter = () => {
    if (blinkTimeoutRef.current) return;

    setIsBlinking(true);

    blinkTimeoutRef.current = setTimeout(() => {
      setIsBlinking(false);
      blinkTimeoutRef.current = null;
    }, 400);
  };

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
      viewBox="0 0 32 18"
      fill="none"
      className={`cursor-pointer ${className}`}
      onMouseEnter={handleMouseEnter}
      style={{
        animation: isBlinking ? 'eyeBlink 0.4s ease-in-out' : 'none',
        transformOrigin: 'center center',
      }}
    >
      <style>
        {`
          @keyframes eyeBlink {
            0%, 100% { transform: scaleY(1); }
            50% { transform: scaleY(0.08); }
          }
        `}
      </style>

      {/* Eye outline - rounded almond shape */}
      <path
        d="M1 9 C5 3, 10 2, 16 2 C22 2, 27 3, 31 9 C27 15, 22 16, 16 16 C10 16, 5 15, 1 9 Z"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />

      {/* Iris - outer ring */}
      <circle
        cx="16"
        cy="9"
        r="5.5"
        stroke="white"
        strokeWidth="1.5"
        fill="none"
      />

      {/* Pupil - solid center */}
      <circle
        cx="16"
        cy="9"
        r="2.5"
        fill="white"
      />
    </svg>
  );
}
