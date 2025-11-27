'use client';

import { useState, useEffect } from 'react';
import { Award, X } from 'lucide-react';

interface BadgeAward {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
}

interface BadgeCelebrationProps {
  badges: BadgeAward[];
  onDismiss: () => void;
}

export default function BadgeCelebration({ badges, onDismiss }: BadgeCelebrationProps) {
  const [visible, setVisible] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (badges.length === 0) {
      setVisible(false);
      return;
    }

    // Auto-advance through badges
    if (badges.length > 1) {
      const timer = setInterval(() => {
        setCurrentIndex(prev => {
          if (prev >= badges.length - 1) {
            clearInterval(timer);
            setTimeout(() => {
              setVisible(false);
              onDismiss();
            }, 3000);
            return prev;
          }
          return prev + 1;
        });
      }, 3000);

      return () => clearInterval(timer);
    } else {
      // Single badge - dismiss after 4 seconds
      const timer = setTimeout(() => {
        setVisible(false);
        onDismiss();
      }, 4000);

      return () => clearTimeout(timer);
    }
  }, [badges, onDismiss]);

  if (!visible || badges.length === 0) {
    return null;
  }

  const currentBadge = badges[currentIndex];

  // Category-specific colors
  const categoryColors: Record<string, string> = {
    streak: 'from-orange-500 to-amber-500',
    volume: 'from-blue-500 to-cyan-500',
    accuracy: 'from-emerald-500 to-green-500',
    milestone: 'from-violet-500 to-purple-500',
    special: 'from-amber-500 to-yellow-500'
  };

  const gradientClass = categoryColors[currentBadge.category] || categoryColors.special;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fadeIn pointer-events-auto" />

      {/* Celebration Card */}
      <div className="relative z-10 animate-scaleIn pointer-events-auto">
        <div className={`bg-gradient-to-br ${gradientClass} p-1 rounded-2xl shadow-2xl`}>
          <div className="bg-zinc-900 rounded-xl p-8 text-center min-w-[320px]">
            {/* Close button */}
            <button
              onClick={() => {
                setVisible(false);
                onDismiss();
              }}
              className="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Badge Icon with animation */}
            <div className="relative inline-block mb-4">
              <div className={`w-20 h-20 rounded-full bg-gradient-to-br ${gradientClass} flex items-center justify-center animate-pulse`}>
                <Award className="w-10 h-10 text-white" />
              </div>
              {/* Sparkle effects */}
              <div className="absolute -top-2 -right-2 w-4 h-4 bg-yellow-400 rounded-full animate-ping" />
              <div className="absolute -bottom-1 -left-1 w-3 h-3 bg-amber-400 rounded-full animate-ping delay-100" />
            </div>

            {/* Text */}
            <p className="text-sm text-zinc-400 mb-1">Badge Unlocked!</p>
            <h2 className="text-2xl font-bold text-white mb-2">{currentBadge.name}</h2>
            <p className="text-zinc-400 max-w-xs mx-auto">{currentBadge.description}</p>

            {/* Progress indicator for multiple badges */}
            {badges.length > 1 && (
              <div className="flex justify-center gap-1.5 mt-6">
                {badges.map((_, i) => (
                  <div
                    key={i}
                    className={`w-2 h-2 rounded-full transition-colors ${
                      i === currentIndex ? 'bg-white' : 'bg-zinc-600'
                    }`}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes scaleIn {
          from {
            opacity: 0;
            transform: scale(0.8) translateY(20px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }

        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }

        .animate-scaleIn {
          animation: scaleIn 0.4s ease-out;
        }

        .delay-100 {
          animation-delay: 100ms;
        }
      `}</style>
    </div>
  );
}
