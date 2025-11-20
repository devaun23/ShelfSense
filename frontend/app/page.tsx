'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { useUser } from '@/contexts/UserContext';
import { generateGreeting } from '@/utils/greetings';

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showWhyUs, setShowWhyUs] = useState(false);
  const [greeting, setGreeting] = useState('');
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);
  const router = useRouter();
  const { user, isLoading } = useUser();

  const handleStarHover = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    setMousePos({
      x: e.clientX - centerX,
      y: e.clientY - centerY
    });
    setIsHovering(true);
  };

  const handleStarLeave = () => {
    setIsHovering(false);
  };

  // Generate star spokes that follow the cursor - memoized for performance
  const spokes = useMemo(() => {
    const numSpokes = 16;
    const spokesArray = [];
    const centerX = 60;
    const centerY = 60;
    const baseLength = 50;

    for (let i = 0; i < numSpokes; i++) {
      const angle = (i * 360 / numSpokes) * (Math.PI / 180);
      const baseEndX = centerX + Math.cos(angle) * baseLength;
      const baseEndY = centerY + Math.sin(angle) * baseLength;

      let endX = baseEndX;
      let endY = baseEndY;

      if (isHovering) {
        // Calculate pull effect based on mouse position
        const dx = mousePos.x;
        const dy = mousePos.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const maxDistance = 100;
        const pullStrength = Math.max(0, 1 - distance / maxDistance) * 15;

        const angleToMouse = Math.atan2(dy, dx);
        const angleDiff = Math.abs(angle - angleToMouse);
        const angleFactor = Math.cos(angleDiff);

        endX += Math.cos(angleToMouse) * pullStrength * angleFactor;
        endY += Math.sin(angleToMouse) * pullStrength * angleFactor;
      }

      spokesArray.push(
        <line
          key={i}
          x1={centerX}
          y1={centerY}
          x2={endX}
          y2={endY}
          stroke="#4169E1"
          strokeWidth="1.5"
          strokeLinecap="round"
          style={{
            transition: isHovering ? 'none' : 'all 0.3s ease-out'
          }}
        />
      );
    }

    return spokesArray;
  }, [mousePos.x, mousePos.y, isHovering]);

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!isLoading && !user) {
      router.push('/login');
      return;
    }

    // Generate personalized greeting
    if (user) {
      const personalizedGreeting = generateGreeting({
        firstName: user.firstName,
        hour: new Date().getHours()
      });
      setGreeting(personalizedGreeting);
    }
  }, [user, isLoading, router]);

  const handleBegin = () => {
    router.push('/study');
  };

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} isHomePage={true} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        <div className="flex flex-col items-center justify-center min-h-screen px-6">
          <div className="max-w-2xl w-full space-y-16 text-center">
            {/* Personalized greeting */}
            {greeting && (
              <div className="flex flex-col items-center justify-center">
                <p className="text-4xl text-white font-bold tracking-wide" style={{ fontFamily: 'var(--font-cormorant)' }}>
                  {greeting}
                </p>
              </div>
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
