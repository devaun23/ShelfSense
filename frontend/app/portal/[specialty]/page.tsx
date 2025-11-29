'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { getSpecialtyBySlug } from '@/lib/specialties';
import EyeLogo from '@/components/icons/EyeLogo';
import SpecialtyIcon from '@/components/icons/SpecialtyIcon';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import WelcomeModal from '@/components/WelcomeModal';

interface PortalDashboardProps {
  params: Promise<{ specialty: string }>;
}

// Warm, empathetic messages that rotate
const ENCOURAGEMENT_MESSAGES = [
  "You've got this.",
  "One step at a time.",
  "Trust your preparation.",
  "Show up. That's what matters.",
  "Every question is a teacher.",
  "You're exactly where you need to be.",
  "Breathe. Focus. Begin.",
  "Your hard work will pay off.",
];

// Feature card definitions with icons
const FEATURE_CARDS = [
  {
    id: 'analytics',
    label: 'Analytics',
    description: 'Track your progress',
    href: '/analytics',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 3v18h18" />
        <path d="M18 9l-5 5-4-4-3 3" />
      </svg>
    ),
  },
  {
    id: 'weak-areas',
    label: 'Weak Areas',
    description: 'Focus on gaps',
    href: '/weak-areas',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 6v6l4 2" />
      </svg>
    ),
  },
  {
    id: 'reviews',
    label: 'Reviews',
    description: 'Spaced repetition',
    href: '/reviews',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2v4" />
        <path d="M12 18v4" />
        <path d="M4.93 4.93l2.83 2.83" />
        <path d="M16.24 16.24l2.83 2.83" />
        <path d="M2 12h4" />
        <path d="M18 12h4" />
        <path d="M4.93 19.07l2.83-2.83" />
        <path d="M16.24 7.76l2.83-2.83" />
      </svg>
    ),
  },
];

export default function PortalDashboard({ params }: PortalDashboardProps) {
  const { user, isLoading, updateTargetScore, updateExamDate } = useUser();
  const router = useRouter();
  const resolvedParams = use(params);
  const specialty = getSpecialtyBySlug(resolvedParams.specialty);
  const [isStarting, setIsStarting] = useState(false);
  const [encouragement, setEncouragement] = useState('');
  const [showWelcome, setShowWelcome] = useState(false);

  // Pick a random encouragement on client-side mount only (avoids hydration mismatch)
  useEffect(() => {
    setEncouragement(
      ENCOURAGEMENT_MESSAGES[Math.floor(Math.random() * ENCOURAGEMENT_MESSAGES.length)]
    );
  }, []);

  // Check if onboarding is needed when entering portal
  useEffect(() => {
    if (user) {
      const onboardingKey = `shelfpass_onboarding_complete_${user.userId}`;
      const hasCompletedOnboarding = localStorage.getItem(onboardingKey) === 'true';

      if (!hasCompletedOnboarding && user.targetScore === null && user.examDate === null) {
        setShowWelcome(true);
      }
    }
  }, [user]);

  const handleWelcomeComplete = async (targetScore: number, examDate: string) => {
    if (user) {
      await updateTargetScore(targetScore);
      await updateExamDate(examDate);
      localStorage.setItem(`shelfpass_onboarding_complete_${user.userId}`, 'true');
    }
    setShowWelcome(false);
  };

  const handleWelcomeSkip = () => {
    if (user) {
      localStorage.setItem(`shelfpass_onboarding_complete_${user.userId}`, 'true');
    }
    setShowWelcome(false);
  };

  const handleStartStudying = () => {
    if (!specialty) return;
    setIsStarting(true);
    // Navigate after a brief moment to show loading state
    setTimeout(() => {
      const specialtyParam = specialty.apiName
        ? `specialty=${encodeURIComponent(specialty.apiName)}`
        : '';
      router.push(`/study?${specialtyParam}`);
    }, 300);
  };

  if (isLoading || !specialty) {
    return (
      <main
        className="min-h-screen bg-black text-white flex items-center justify-center"
        role="status"
        aria-busy="true"
        aria-label="Loading dashboard"
      >
        <LoadingSpinner size="lg" />
        <span className="sr-only">Loading dashboard...</span>
      </main>
    );
  }

  const basePath = `/portal/${specialty.slug}`;

  return (
    <>
      {/* Welcome Modal for onboarding */}
      {showWelcome && user && (
        <WelcomeModal
          firstName={user.firstName}
          onComplete={handleWelcomeComplete}
          onSkip={handleWelcomeSkip}
        />
      )}

      <main className="min-h-screen bg-black text-white flex flex-col items-center justify-center px-4 animate-fade-in">
        {/* Eye Logo */}
        <div className="mb-6 animate-bounce-in" style={{ animationDelay: '0ms' }}>
          <EyeLogo size={48} />
        </div>

      {/* Empathetic Encouragement */}
      {encouragement && (
        <p
          className="text-gray-500 text-lg mb-8 text-center animate-bounce-in"
          style={{ fontFamily: 'var(--font-serif)', animationDelay: '100ms' }}
        >
          {encouragement}
        </p>
      )}

      {/* Specialty Banner */}
      <div
        className="flex items-center gap-3 px-6 py-4 bg-gray-900/50 border border-gray-800 rounded-2xl mb-8 animate-bounce-in"
        style={{ animationDelay: '200ms' }}
      >
        <SpecialtyIcon specialty={specialty.id} size={24} className="text-gray-400" />
        <div>
          <h1
            className="text-2xl font-semibold text-white"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            {specialty.name}
          </h1>
          {specialty.description && (
            <p className="text-sm text-gray-500">{specialty.description}</p>
          )}
        </div>
      </div>

      {/* Feature Cards - bouncing in with stagger */}
      <div className="flex flex-wrap justify-center gap-2 max-w-md mb-10">
        {FEATURE_CARDS.map((card, index) => (
          <button
            key={card.id}
            onClick={() => router.push(`${basePath}${card.href}`)}
            className="flex items-center gap-2 px-4 py-2.5 bg-gray-900/50 hover:bg-gray-800 border border-gray-800 hover:border-gray-600 rounded-full text-sm text-gray-400 hover:text-white transition-all duration-200 ease-out active:scale-95 animate-bounce-in"
            style={{ animationDelay: `${300 + index * 80}ms` }}
          >
            {card.icon}
            <span>{card.label}</span>
          </button>
        ))}
      </div>

      {/* Start Studying Button */}
      <button
        onClick={handleStartStudying}
        disabled={isStarting}
        className="px-8 py-4 bg-white hover:bg-gray-100 text-black font-medium rounded-full transition-all duration-200 ease-out active:scale-95 hover:shadow-lg hover:shadow-white/10 animate-bounce-in disabled:opacity-70"
        style={{ fontFamily: 'var(--font-serif)', animationDelay: '550ms' }}
      >
        {isStarting ? (
          <div className="flex items-center gap-3">
            <LoadingDots />
            <span>Loading</span>
          </div>
        ) : (
          'Start Studying'
        )}
      </button>

      {/* Back to Home */}
      <button
        onClick={() => router.push('/')}
        className="mt-8 text-gray-600 hover:text-gray-400 text-sm transition-colors animate-bounce-in"
        style={{ animationDelay: '650ms' }}
      >
        Back to all exams
      </button>

      {/* Animation styles */}
      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
        @keyframes bounceIn {
          0% {
            opacity: 0;
            transform: scale(0.3) translateY(20px);
          }
          50% {
            transform: scale(1.05) translateY(-5px);
          }
          70% {
            transform: scale(0.95) translateY(2px);
          }
          100% {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        .animate-fade-in {
          animation: fadeIn 0.3s ease-out forwards;
        }
        .animate-bounce-in {
          opacity: 0;
          animation: bounceIn 0.5s ease-out forwards;
        }
      `}</style>
      </main>
    </>
  );
}

// Loading dots component
function LoadingDots() {
  return (
    <div className="flex gap-1">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="w-2 h-2 bg-black rounded-full animate-pulse"
          style={{
            animationDelay: `${i * 150}ms`,
            animationDuration: '0.8s',
          }}
        />
      ))}
    </div>
  );
}
