'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const router = useRouter();

  const greetings = [
    "Welcome to ShelfSense",
    "Good to see you",
    "Happy to help you prepare",
    "Great to have you here",
  ];

  const [greeting] = useState(greetings[Math.floor(Math.random() * greetings.length)]);

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
          <div className="max-w-2xl w-full space-y-8 text-center">
            {/* Polite greeting */}
            <p className="text-lg text-gray-400">
              {greeting}
            </p>

            {/* ShelfSense branding */}
            <h1 className="text-6xl font-semibold tracking-tight">
              ShelfSense
            </h1>

            {/* Subtitle */}
            <p className="text-gray-500">
              Adaptive learning for USMLE Step 2 CK
            </p>

            {/* Ready to begin prompt */}
            <div className="pt-8">
              <p className="text-xl text-gray-300 mb-6">
                Ready to begin?
              </p>

              <button
                onClick={handleBegin}
                className="px-8 py-4 bg-[#1E3A5F] hover:bg-[#2C5282] text-white rounded-lg transition-colors duration-200 text-lg"
              >
                Start Practice
              </button>
            </div>

            {/* Stats (optional) */}
            <div className="pt-12 text-sm text-gray-600">
              <p>1,994 questions · 8 specialties · Adaptive algorithm</p>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
