'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useUser } from '@/contexts/UserContext';

// Dynamically import Sidebar to avoid useSearchParams SSR issues
const Sidebar = dynamic(() => import('@/components/Sidebar'), { ssr: false });

interface StudyModeCard {
  id: string;
  name: string;
  description: string;
  icon: string;
  path: string;
  features: string[];
  bestFor: string;
  badge?: string;
}

export default function StudyModesPage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [reviewCount, setReviewCount] = useState<number>(0);
  const [challengeCount, setChallengeCount] = useState<number>(0);

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    // Load stats for review and challenge modes
    if (user) {
      loadReviewCount();
      loadChallengeCount();
    }
  }, [user, userLoading, router]);

  const loadReviewCount = async () => {
    if (!user) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${apiUrl}/api/study-modes/review-schedule?user_id=${user.userId}`
      );
      if (response.ok) {
        const data = await response.json();
        // Count reviews due today
        const today = new Date().toISOString().split('T')[0];
        const dueToday = data.filter((review: any) =>
          review.next_review_date.startsWith(today)
        ).length;
        setReviewCount(dueToday);
      }
    } catch (error) {
      console.error('Error loading review count:', error);
    }
  };

  const loadChallengeCount = async () => {
    if (!user) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${apiUrl}/api/study-modes/challenge-questions?user_id=${user.userId}`
      );
      if (response.ok) {
        const data = await response.json();
        setChallengeCount(data.length);
      }
    } catch (error) {
      console.error('Error loading challenge count:', error);
    }
  };

  const studyModes: StudyModeCard[] = [
    {
      id: 'timed',
      name: 'Timed Mode',
      description: 'Simulate real exam conditions with a countdown timer',
      icon: '⏱️',
      path: '/study-modes/timed',
      features: [
        '6 minutes per question (customizable)',
        'All answers revealed at end',
        'Performance tracking',
        'Exam simulation experience'
      ],
      bestFor: 'Preparing for test day and improving time management'
    },
    {
      id: 'tutor',
      name: 'Tutor Mode',
      description: 'Get immediate feedback after each question',
      icon: '📚',
      path: '/study',
      features: [
        'Instant feedback after each answer',
        'Detailed explanations',
        'AI chat for deeper understanding',
        'No time pressure'
      ],
      bestFor: 'Learning new concepts and understanding weak areas',
      badge: 'Default'
    },
    {
      id: 'challenge',
      name: 'Challenge Mode',
      description: 'Test yourself with the hardest questions',
      icon: '🎯',
      path: '/study-modes/challenge',
      features: [
        'Only questions with < 60% accuracy',
        'Requires ≥ 5 attempts for reliability',
        'Push your limits',
        'Track improvement on difficult topics'
      ],
      bestFor: 'Advanced learners looking to master difficult material',
      badge: challengeCount > 0 ? `${challengeCount} questions` : undefined
    },
    {
      id: 'review',
      name: 'Review Mode',
      description: 'Study questions scheduled for review today',
      icon: '🔄',
      path: '/study-modes/review',
      features: [
        'Spaced repetition algorithm (SM-2)',
        'Review questions you missed',
        'Optimal learning intervals',
        'Track mastery progress'
      ],
      bestFor: 'Reinforcing knowledge and long-term retention',
      badge: reviewCount > 0 ? `${reviewCount} due today` : 'No reviews due'
    }
  ];

  const handleModeSelect = (mode: StudyModeCard) => {
    router.push(mode.path);
  };

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        <div className="max-w-6xl mx-auto px-8 py-12">
          {/* Header */}
          <div className="mb-12">
            <h1 className="text-4xl font-bold mb-4" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Study Modes
            </h1>
            <p className="text-xl text-gray-400">
              Choose how you want to study. Each mode is designed for different learning goals.
            </p>
          </div>

          {/* Study Mode Cards Grid */}
          <div className="grid md:grid-cols-2 gap-6">
            {studyModes.map((mode) => (
              <button
                key={mode.id}
                onClick={() => handleModeSelect(mode)}
                className="group relative bg-gray-900 hover:bg-gray-800 border border-gray-700 hover:border-blue-500/50 rounded-xl p-6 text-left transition-all duration-200 hover:shadow-lg hover:shadow-blue-500/10"
              >
                {/* Badge */}
                {mode.badge && (
                  <div className="absolute top-4 right-4 bg-blue-500/20 text-blue-400 text-xs font-semibold px-3 py-1 rounded-full border border-blue-500/30">
                    {mode.badge}
                  </div>
                )}

                {/* Icon & Title */}
                <div className="flex items-start gap-4 mb-4">
                  <div className="text-5xl">{mode.icon}</div>
                  <div className="flex-1">
                    <h2 className="text-2xl font-bold mb-2">{mode.name}</h2>
                    <p className="text-gray-400 text-base">{mode.description}</p>
                  </div>
                </div>

                {/* Features */}
                <div className="mb-4 space-y-2">
                  {mode.features.map((feature, index) => (
                    <div key={index} className="flex items-start gap-2 text-sm text-gray-300">
                      <svg className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>

                {/* Best For */}
                <div className="pt-4 border-t border-gray-700">
                  <div className="text-xs text-gray-500 mb-1">BEST FOR</div>
                  <div className="text-sm text-gray-300">{mode.bestFor}</div>
                </div>

                {/* Arrow indicator on hover */}
                <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                  <svg className="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </div>
              </button>
            ))}
          </div>

          {/* Study Tips */}
          <div className="mt-12 bg-blue-500/10 border border-blue-500/30 rounded-xl p-6">
            <div className="flex items-start gap-3">
              <svg className="w-6 h-6 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h3 className="text-lg font-bold mb-2">Study Tips</h3>
                <ul className="space-y-1 text-sm text-gray-300">
                  <li>• Start with <strong>Tutor Mode</strong> to learn new concepts</li>
                  <li>• Use <strong>Timed Mode</strong> 2-3 weeks before your exam</li>
                  <li>• Check <strong>Review Mode</strong> daily for spaced repetition reviews</li>
                  <li>• Try <strong>Challenge Mode</strong> when you're ready to push your limits</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
