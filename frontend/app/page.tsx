'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const router = useRouter();

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

            {/* Begin button */}
            <div className="pt-8">
              <button
                onClick={handleBegin}
                className="px-8 py-4 bg-[#1E3A5F] hover:bg-[#2C5282] text-white rounded-lg transition-colors duration-200 text-lg"
              >
                Begin
              </button>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
