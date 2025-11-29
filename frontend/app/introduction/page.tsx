'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import EyeLogo from '@/components/icons/EyeLogo';

export default function IntroductionPage() {
  const router = useRouter();
  const { user, isLoading } = useUser();
  const [showContent, setShowContent] = useState(false);

  useEffect(() => {
    // Trigger staggered animations after mount
    const timer = setTimeout(() => setShowContent(true), 100);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    // If user has already seen intro, redirect to home
    if (user) {
      const introKey = `shelfsense_intro_seen_${user.userId}`;
      const hasSeenIntro = localStorage.getItem(introKey) === 'true';
      if (hasSeenIntro) {
        router.replace('/');
      }
    }
  }, [user, router]);

  const handleBegin = () => {
    if (user) {
      const introKey = `shelfsense_intro_seen_${user.userId}`;
      localStorage.setItem(introKey, 'true');
    }
    router.push('/');
  };

  if (isLoading) {
    return (
      <main className="min-h-screen bg-black flex items-center justify-center">
        <div className="animate-pulse">
          <EyeLogo size={64} />
        </div>
      </main>
    );
  }

  // If no user, redirect to sign-in
  if (!user) {
    router.replace('/sign-in');
    return null;
  }

  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center justify-center px-6 py-12">
      <div className="max-w-lg w-full text-center">
        {/* Eye Logo */}
        <div
          className={`mb-8 transition-all duration-700 ease-out ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <EyeLogo size={80} className="mx-auto" />
        </div>

        {/* Welcome Heading */}
        <h1
          className={`text-4xl md:text-5xl text-white mb-6 transition-all duration-700 ease-out delay-150 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          Welcome to ShelfSense
        </h1>

        {/* Empathetic Opening */}
        <p
          className={`text-gray-400 text-lg mb-10 leading-relaxed transition-all duration-700 ease-out delay-300 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          We know medical school is demanding.<br />
          ShelfSense is here to support you—<br />
          one question at a time.
        </p>

        {/* Divider */}
        <div
          className={`w-16 h-px bg-gray-800 mx-auto mb-10 transition-all duration-700 ease-out delay-450 ${
            showContent ? 'opacity-100 scale-x-100' : 'opacity-0 scale-x-0'
          }`}
        />

        {/* Features */}
        <div
          className={`space-y-4 mb-10 text-left transition-all duration-700 ease-out delay-500 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-[#4169E1] mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="text-gray-300">
              <strong className="text-white">Adaptive questions</strong> that target your weak areas
            </span>
          </div>
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-[#4169E1] mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="text-gray-300">
              <strong className="text-white">Personalized support</strong> that explains what you need
            </span>
          </div>
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-[#4169E1] mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="text-gray-300">
              <strong className="text-white">Spaced repetition</strong> so you remember what matters
            </span>
          </div>
        </div>

        {/* Divider */}
        <div
          className={`w-16 h-px bg-gray-800 mx-auto mb-10 transition-all duration-700 ease-out delay-600 ${
            showContent ? 'opacity-100 scale-x-100' : 'opacity-0 scale-x-0'
          }`}
        />

        {/* Personal Message & Attribution */}
        <div
          className={`mb-8 transition-all duration-700 ease-out delay-650 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <p
            className="text-gray-300 text-base leading-relaxed mb-3"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Made with care, for students like you.
          </p>
          <p
            className="text-gray-500 text-sm"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            By Devaun Reid & friends
          </p>
        </div>

        {/* CTA Button */}
        <button
          onClick={handleBegin}
          className={`px-8 py-3 bg-[#4169E1] hover:bg-[#3558c0] text-white font-medium rounded-full transition-all duration-300 ease-out hover:shadow-lg hover:shadow-[#4169E1]/20 active:scale-[0.98] delay-800 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          Get Started
        </button>

        {/* Feedback Note */}
        <p
          className={`text-gray-600 text-xs mt-8 transition-all duration-700 ease-out delay-900 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          Questions or ideas? We'd love to hear from you.<br />
          Look for the feedback button at the bottom of the sidebar.
        </p>
      </div>
    </main>
  );
}
