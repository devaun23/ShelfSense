'use client';

import { useEffect, useState } from 'react';

interface EncouragementToastProps {
  message: string;
  duration?: number;
  onDismiss?: () => void;
}

export default function EncouragementToast({
  message,
  duration = 4000,
  onDismiss,
}: EncouragementToastProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    // Fade in
    const showTimer = setTimeout(() => setIsVisible(true), 50);

    // Start fade out before duration ends
    const hideTimer = setTimeout(() => {
      setIsLeaving(true);
    }, duration - 300);

    // Actually remove
    const removeTimer = setTimeout(() => {
      onDismiss?.();
    }, duration);

    return () => {
      clearTimeout(showTimer);
      clearTimeout(hideTimer);
      clearTimeout(removeTimer);
    };
  }, [duration, onDismiss]);

  return (
    <div
      className={`fixed bottom-8 left-1/2 -translate-x-1/2 z-50 px-6 py-3 bg-gray-900/95 border border-gray-800 rounded-full shadow-lg backdrop-blur-sm transition-all duration-300 ease-out ${
        isVisible && !isLeaving
          ? 'opacity-100 translate-y-0'
          : 'opacity-0 translate-y-4'
      }`}
      role="status"
      aria-live="polite"
    >
      <p
        className="text-gray-300 text-sm text-center"
        style={{ fontFamily: 'var(--font-serif)' }}
      >
        {message}
      </p>
    </div>
  );
}

// Hook for managing toast state
export function useEncouragementToast() {
  const [toast, setToast] = useState<{ message: string; key: number } | null>(null);

  const showToast = (message: string) => {
    setToast({ message, key: Date.now() });
  };

  const hideToast = () => {
    setToast(null);
  };

  return { toast, showToast, hideToast };
}
