'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { useExam } from '@/contexts/ExamContext';
import WelcomeModal from '@/components/WelcomeModal';
import { SPECIALTIES, FULL_PREP_MODE, Specialty } from '@/lib/specialties';
import ShelfSenseLogo from '@/components/icons/ShelfSenseLogo';

export default function Home() {
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
          <ShelfSenseLogo size={48} animate={true} />
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

      <main className="min-h-screen bg-black text-white flex flex-col items-center justify-center px-4">
        {/* Logo */}
        <div className="mb-6">
          <ShelfSenseLogo size={40} animate={true} />
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
          Select a shelf exam to begin
        </p>

        {/* Exam Pills - Wrapped row */}
        <div className="flex flex-wrap justify-center gap-2 max-w-2xl mb-8">
          {SPECIALTIES.map((exam) => (
            <button
              key={exam.id}
              onClick={() => handleExamSelect(exam)}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-gray-900/50 hover:bg-gray-800 border border-gray-800 hover:border-gray-600 rounded-full text-sm text-gray-300 hover:text-white transition-all duration-200"
            >
              <span className="text-base">{exam.icon}</span>
              <span>{exam.name}</span>
            </button>
          ))}
        </div>

        {/* Step 2 CK Full Prep - Slightly larger, featured */}
        <button
          onClick={() => handleExamSelect(FULL_PREP_MODE)}
          className="inline-flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-blue-600/20 to-indigo-600/20 hover:from-blue-600/30 hover:to-indigo-600/30 border border-blue-500/30 hover:border-blue-400/50 rounded-full text-white transition-all duration-200 group"
        >
          <span className="text-xl">{FULL_PREP_MODE.icon}</span>
          <span className="font-medium">{FULL_PREP_MODE.name}</span>
          <svg
            className="w-4 h-4 text-blue-400 group-hover:translate-x-0.5 transition-transform"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>

        {/* Bottom quick links */}
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4 text-sm text-gray-600">
          <button
            onClick={() => router.push('/analytics')}
            className="hover:text-gray-400 transition-colors"
          >
            Analytics
          </button>
          <span className="text-gray-800">|</span>
          <button
            onClick={() => router.push('/reviews')}
            className="hover:text-gray-400 transition-colors"
          >
            Reviews
          </button>
          <span className="text-gray-800">|</span>
          <button
            onClick={() => router.push('/help')}
            className="hover:text-gray-400 transition-colors"
          >
            Help
          </button>
        </div>
      </main>
    </>
  );
}
