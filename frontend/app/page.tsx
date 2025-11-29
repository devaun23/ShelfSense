'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useUser } from '@/contexts/UserContext';
import { useExam } from '@/contexts/ExamContext';
import WelcomeModal from '@/components/WelcomeModal';
import { SPECIALTIES, FULL_PREP_MODE, Specialty } from '@/lib/specialties';
import EyeLogo from '@/components/icons/EyeLogo';
import SpecialtyIcon from '@/components/icons/SpecialtyIcon';

// Dynamically import Sidebar to avoid useSearchParams SSR issues
const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });

export default function Home() {
  // Start with sidebar closed to avoid hydration mismatch
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Set initial sidebar state after mount
  useEffect(() => {
    setSidebarOpen(window.innerWidth >= 900);
  }, []);

  const router = useRouter();
  const { user, isLoading, updateTargetScore, updateExamDate } = useUser();
  const { enterPortal } = useExam();
  const [showWelcome, setShowWelcome] = useState(false);

  useEffect(() => {
    if (user) {
      // Check if onboarding is needed
      const onboardingKey = `shelfsense_onboarding_complete_${user.userId}`;
      const hasCompletedOnboarding = localStorage.getItem(onboardingKey) === 'true';

      if (!hasCompletedOnboarding && user.targetScore === null && user.examDate === null) {
        setShowWelcome(true);
      }
    }
  }, [user]);

  const handleExamSelect = (exam: Specialty) => {
    enterPortal(exam.slug);
    router.push(`/portal/${exam.slug}`);
  };

  const handleWelcomeComplete = async (targetScore: number, examDate: string) => {
    if (user) {
      await updateTargetScore(targetScore);
      await updateExamDate(examDate);
      localStorage.setItem(`shelfsense_onboarding_complete_${user.userId}`, 'true');
    }
    setShowWelcome(false);
  };

  const handleWelcomeSkip = () => {
    if (user) {
      localStorage.setItem(`shelfsense_onboarding_complete_${user.userId}`, 'true');
    }
    setShowWelcome(false);
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  if (isLoading) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="animate-pulse">
          <EyeLogo size={48} />
        </div>
      </main>
    );
  }

  return (
    <>
      {showWelcome && user && (
        <WelcomeModal
          firstName={user.firstName}
          onComplete={handleWelcomeComplete}
          onSkip={handleWelcomeSkip}
        />
      )}

      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white flex flex-col items-center justify-center px-4 transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        {/* Logo */}
        <div className="mb-6">
          <EyeLogo size={64} />
        </div>

        {/* Greeting */}
        {user && (
          <h1
            className="text-3xl md:text-4xl text-white mb-8 text-center"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            {getGreeting()}, {user.firstName}
          </h1>
        )}

        {/* Prompt */}
        <p className="text-gray-500 mb-8 text-center">
          Select an exam to begin
        </p>

        {/* Exam Pills - Wrapped row with icons and staggered bounce animation */}
        <div className="flex flex-wrap justify-center gap-2 max-w-2xl mb-8">
          {SPECIALTIES.map((exam, index) => (
            <button
              key={exam.id}
              onClick={() => handleExamSelect(exam)}
              className="flex items-center gap-2 px-4 py-2.5 bg-gray-900/50 hover:bg-gray-800 border border-gray-800 hover:border-gray-600 rounded-full text-sm text-gray-300 hover:text-white transition-all duration-200 ease-out animate-bounce-in active:scale-95 hover:shadow-lg hover:shadow-black/20"
              style={{ animationDelay: `${index * 80}ms` }}
            >
              <SpecialtyIcon specialty={exam.id} size={14} />
              {exam.name}
            </button>
          ))}
        </div>

        {/* Step 2 CK - Slightly larger with delayed animation */}
        <button
          onClick={() => handleExamSelect(FULL_PREP_MODE)}
          className="flex items-center gap-2 px-6 py-3 bg-gray-900/50 hover:bg-gray-800 border border-gray-800 hover:border-gray-600 rounded-full text-gray-300 hover:text-white transition-all duration-200 ease-out animate-bounce-in active:scale-95 hover:shadow-lg hover:shadow-black/20"
          style={{ animationDelay: `${SPECIALTIES.length * 80 + 100}ms` }}
        >
          <SpecialtyIcon specialty="step2-ck" size={16} />
          <span className="font-medium">{FULL_PREP_MODE.name}</span>
        </button>

        {/* Custom animation styles */}
        <style jsx>{`
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
          .animate-bounce-in {
            opacity: 0;
            animation: bounceIn 0.5s ease-out forwards;
          }
        `}</style>
      </main>
    </>
  );
}
