'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showWhyUs, setShowWhyUs] = useState(false);
  const [greeting, setGreeting] = useState('');
  const router = useRouter();

  useEffect(() => {
    // Generate time-based greeting
    const hour = new Date().getHours();
    const userName = 'Student'; // Will be replaced with real name when auth is added

    if (hour >= 5 && hour < 12) {
      setGreeting(`Good Morning, ${userName}`);
    } else if (hour >= 12 && hour < 17) {
      setGreeting(`Good Afternoon, ${userName}`);
    } else if (hour >= 17 && hour < 22) {
      setGreeting(`Good Evening, ${userName}`);
    } else {
      setGreeting(`Welcome Back, ${userName}`);
    }
  }, []);

  const handleBegin = () => {
    router.push('/study');
  };

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        <div className="flex flex-col items-center justify-center min-h-screen px-6">
          <div className="max-w-2xl w-full space-y-12 text-center">
            {/* ShelfSense branding with elegant font */}
            <h1 className="text-7xl tracking-wide font-light" style={{ fontFamily: 'var(--font-cormorant)' }}>
              ShelfSense
            </h1>

            {/* Personalized greeting */}
            {greeting && (
              <p className="text-2xl text-gray-400" style={{ fontFamily: 'var(--font-cormorant)' }}>
                {greeting}
              </p>
            )}

            {/* Begin button */}
            <div className="pt-8">
              <button
                onClick={handleBegin}
                className="px-8 py-4 bg-[#1E3A5F] hover:bg-[#2C5282] text-white rounded-lg transition-colors duration-200 text-xl"
                style={{ fontFamily: 'var(--font-cormorant)' }}
              >
                Ready to Begin?
              </button>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
