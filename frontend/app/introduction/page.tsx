'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import EyeLogo from '@/components/icons/EyeLogo';

export default function IntroductionPage() {
  const router = useRouter();
  const { user, isLoading } = useUser();
  const [showContent, setShowContent] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);

  useEffect(() => {
    // Trigger staggered animations after mount
    const timer = setTimeout(() => setShowContent(true), 100);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    // If user has already seen intro, redirect to home
    if (user) {
      const introKey = `shelfpass_intro_seen_${user.userId}`;
      const hasSeenIntro = localStorage.getItem(introKey) === 'true';
      if (hasSeenIntro) {
        router.replace('/');
      }
    }
  }, [user, router]);

  const handleBegin = () => {
    setIsTransitioning(true);
    if (user) {
      const introKey = `shelfpass_intro_seen_${user.userId}`;
      localStorage.setItem(introKey, 'true');
    }
    // Smooth fade out then navigate
    setTimeout(() => {
      router.push('/');
    }, 500);
  };

  // Loading state with spinning circles
  if (isLoading) {
    return (
      <main className="h-screen bg-black flex items-center justify-center overflow-hidden">
        <div className="relative w-12 h-12">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="absolute w-2 h-2 bg-white rounded-full"
              style={{
                top: '50%',
                left: '50%',
                transform: `rotate(${i * 45}deg) translateY(-16px)`,
                opacity: 1 - i * 0.1,
                animation: 'spinFade 1s linear infinite',
                animationDelay: `${i * 0.125}s`,
              }}
            />
          ))}
        </div>
        <style jsx>{`
          @keyframes spinFade {
            0%, 100% { opacity: 0.2; }
            50% { opacity: 1; }
          }
        `}</style>
      </main>
    );
  }

  // If no user, redirect to sign-in
  if (!user) {
    router.replace('/sign-in');
    return null;
  }

  return (
    <main className={`h-screen bg-black text-white flex flex-col items-center justify-center px-8 overflow-hidden transition-opacity duration-500 ${isTransitioning ? 'opacity-0' : 'opacity-100'}`}>
      <div className="max-w-2xl w-full text-center">
        {/* Eye Logo */}
        <div
          className={`mb-4 transition-all duration-700 ease-out ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <EyeLogo size={64} className="mx-auto" />
        </div>

        {/* Welcome Heading */}
        <h1
          className={`text-2xl md:text-3xl text-white mb-3 transition-all duration-700 ease-out delay-150 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          Welcome to ShelfPass
        </h1>

        {/* Empathetic Opening - NO HYPHENS */}
        <p
          className={`text-gray-400 text-base mb-4 leading-relaxed transition-all duration-700 ease-out delay-300 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          We know medical school is demanding.<br />
          ShelfSense is here to support you,<br />
          one question at a time.
        </p>

        {/* Divider */}
        <div
          className={`w-12 h-px bg-gray-700 mx-auto mb-4 transition-all duration-700 ease-out delay-450 ${
            showContent ? 'opacity-100 scale-x-100' : 'opacity-0 scale-x-0'
          }`}
        />

        {/* Features - Centered */}
        <div
          className={`space-y-2 mb-4 transition-all duration-700 ease-out delay-500 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <div className="flex items-center justify-center gap-2">
            <svg className="w-4 h-4 text-[#4169E1] flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="text-gray-300 text-sm">
              <strong className="text-white">Adaptive questions</strong> that target your weak areas
            </span>
          </div>
          <div className="flex items-center justify-center gap-2">
            <svg className="w-4 h-4 text-[#4169E1] flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="text-gray-300 text-sm">
              <strong className="text-white">Personalized support</strong> that explains what you need
            </span>
          </div>
          <div className="flex items-center justify-center gap-2">
            <svg className="w-4 h-4 text-[#4169E1] flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="text-gray-300 text-sm">
              <strong className="text-white">Spaced repetition</strong> so you remember what matters
            </span>
          </div>
        </div>

        {/* Divider */}
        <div
          className={`w-12 h-px bg-gray-700 mx-auto mb-4 transition-all duration-700 ease-out delay-600 ${
            showContent ? 'opacity-100 scale-x-100' : 'opacity-0 scale-x-0'
          }`}
        />

        {/* Personal Message & Attribution */}
        <div
          className={`mb-4 transition-all duration-700 ease-out delay-650 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <p
            className="text-gray-300 text-sm leading-relaxed mb-2"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Made with care, for students like you.
          </p>
          <p
            className="text-white text-lg font-extralight tracking-wide"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            By Devaun Reid & friends
          </p>
        </div>

        {/* CTA Button */}
        <button
          onClick={handleBegin}
          disabled={isTransitioning}
          className={`px-8 py-3 bg-[#4169E1] hover:bg-[#3558c0] text-white text-sm font-medium rounded-full transition-all duration-300 ease-out hover:shadow-lg hover:shadow-[#4169E1]/20 active:scale-[0.98] disabled:opacity-50 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
          style={{ fontFamily: 'var(--font-serif)', transitionDelay: showContent ? '800ms' : '0ms' }}
        >
          {isTransitioning ? (
            <span className="flex items-center gap-2">
              <span className="relative w-5 h-5">
                {[...Array(8)].map((_, i) => (
                  <span
                    key={i}
                    className="absolute w-1.5 h-1.5 bg-white rounded-full"
                    style={{
                      top: '50%',
                      left: '50%',
                      transform: `rotate(${i * 45}deg) translateY(-8px)`,
                      opacity: 1 - i * 0.1,
                      animation: 'spinFade 1s linear infinite',
                      animationDelay: `${i * 0.125}s`,
                    }}
                  />
                ))}
              </span>
              Loading
            </span>
          ) : (
            'Get Started'
          )}
        </button>

        {/* Feedback Note */}
        <div
          className={`mt-6 transition-all duration-700 ease-out delay-900 ${
            showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <p
            className="text-white text-xs leading-relaxed"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Questions or ideas? We'd love to hear from you.
          </p>
          <p
            className="text-white/70 text-xs mt-1"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Look for the feedback button at the bottom of the sidebar.
          </p>
        </div>
      </div>

      <style jsx>{`
        @keyframes spinFade {
          0%, 100% { opacity: 0.2; }
          50% { opacity: 1; }
        }
      `}</style>
    </main>
  );
}
