'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui';

interface WelcomeModalProps {
  firstName: string;
  onComplete: (targetScore: number, examDate: string) => void;
  onSkip: () => void;
}

export default function WelcomeModal({ firstName, onComplete, onSkip }: WelcomeModalProps) {
  const [targetScore, setTargetScore] = useState(240);
  const [examDate, setExamDate] = useState('');
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  // Get minimum date (today)
  const minDate = new Date().toISOString().split('T')[0];

  // Store previously focused element and prevent body scroll
  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = '';
      previousActiveElement.current?.focus();
    };
  }, []);

  // Handle ESC key and focus trap
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onSkip();
    }

    // Focus trap
    if (e.key === 'Tab' && modalRef.current) {
      const focusableElements = modalRef.current.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0] as HTMLElement;
      const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    }
  }, [onSkip]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const handleSubmit = () => {
    if (examDate) {
      onComplete(targetScore, examDate);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-title"
    >
      <div
        ref={modalRef}
        className="bg-gray-950 rounded-xl max-w-md w-full border border-gray-800 p-6 md:p-8 animate-slide-up"
      >
        {/* Header */}
        <h2
          id="welcome-title"
          className="text-2xl md:text-3xl text-white mb-2"
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          Welcome, {firstName}
        </h2>
        <p className="text-gray-500 mb-8">
          Let&apos;s set up your study goals to help track your progress.
        </p>

        {/* Target Score */}
        <div className="mb-6">
          <label htmlFor="target-score" className="block text-sm text-gray-400 mb-3">
            Target Score
          </label>
          <div className="flex items-center gap-4">
            <input
              id="target-score"
              type="range"
              min="200"
              max="280"
              step="5"
              value={targetScore}
              onChange={(e) => setTargetScore(Number(e.target.value))}
              className="flex-1 h-2 bg-gray-800 rounded-full appearance-none cursor-pointer accent-[#4169E1]"
            />
            <span className="text-2xl font-semibold text-[#4169E1] w-14 text-right tabular-nums">
              {targetScore}
            </span>
          </div>
          <p className="text-xs text-gray-600 mt-2">
            National average: 240-250
          </p>
        </div>

        {/* Exam Date */}
        <div className="mb-8">
          <label htmlFor="exam-date" className="block text-sm text-gray-400 mb-3">
            Exam Date
          </label>
          <input
            id="exam-date"
            type="date"
            value={examDate}
            onChange={(e) => setExamDate(e.target.value)}
            min={minDate}
            className="w-full bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-[#4169E1] focus:border-transparent"
          />
        </div>

        {/* Quick Tips */}
        <div className="mb-8 p-4 bg-gray-900/50 rounded-lg border border-gray-800">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Quick Start Tips</p>
          <ul className="text-sm text-gray-400 space-y-2">
            <li className="flex items-start gap-2">
              <span className="text-[#4169E1] mt-0.5">•</span>
              <span>Select a shelf exam from the sidebar to begin</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-[#4169E1] mt-0.5">•</span>
              <span>Use Reviews for spaced repetition learning</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-[#4169E1] mt-0.5">•</span>
              <span>Track your progress in Analytics</span>
            </li>
          </ul>
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <Button
            variant="primary"
            size="lg"
            className="w-full"
            onClick={handleSubmit}
            disabled={!examDate}
          >
            Get Started
          </Button>
          <button
            onClick={onSkip}
            className="w-full text-sm text-gray-500 hover:text-gray-400 py-2 transition-colors"
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  );
}
