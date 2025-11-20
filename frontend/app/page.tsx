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
  const [queueStats, setQueueStats] = useState({ completed: 0, queueSize: 10 });
  const [streak, setStreak] = useState(0);
  const router = useRouter();
  const { user, isLoading } = useUser();

  // Calculate streak color gradient
  const getStreakColor = (days: number) => {
    const cycle = days % 101; // Reset after 100
    if (cycle === 0 && days > 0) {
      // Day 100, 200, etc - rainbow gradient
      return 'bg-gradient-to-r from-red-500 via-yellow-500 via-green-500 via-blue-500 to-purple-500 bg-clip-text text-transparent';
    }

    // Gradient from deep red-orange to bright flame
    const hue = 0; // Red base
    const saturation = 100;
    const lightness = 35 + (cycle * 0.3); // 35% to 65% lightness
    return `text-[hsl(${hue},${saturation}%,${Math.min(lightness, 65)}%)]`;
  };

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

    // Generate personalized greeting and load stats
    if (user) {
      const personalizedGreeting = generateGreeting({
        firstName: user.firstName,
        hour: new Date().getHours()
      });
      setGreeting(personalizedGreeting);

      // Load user stats
      loadUserStats();
    }
  }, [user, isLoading, router]);

  const loadUserStats = async () => {
    if (!user) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/analytics/stats?user_id=${user.userId}`);
      if (response.ok) {
        const data = await response.json();

        // Adaptive queue: starts at 10, grows based on performance
        const completed = data.total_attempts || 0;
        const incorrectCount = data.incorrect_count || 0;

        // Calculate adaptive queue size (starts at 10, adds more if struggling)
        let queueSize = 10;
        if (incorrectCount > 0) {
          // Add 2 questions for every incorrect answer
          queueSize = Math.min(10 + (incorrectCount * 2), 50); // Cap at 50
        }

        setQueueStats({
          completed: completed,
          queueSize: queueSize
        });
        setStreak(data.streak || 0);
      }
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

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
          <div className="max-w-2xl w-full space-y-12 text-center">
            {/* Personalized greeting */}
            {greeting && (
              <div className="flex flex-col items-center justify-center">
                <p className="text-4xl text-white font-bold tracking-wide" style={{ fontFamily: 'var(--font-cormorant)' }}>
                  {greeting}
                </p>
              </div>
            )}

            {/* Queue Progress */}
            <div className="flex flex-col items-center space-y-3">
              <div className="text-gray-400 text-sm uppercase tracking-wide">Question Queue</div>
              <div className="text-5xl font-bold text-white" style={{ fontFamily: 'var(--font-cormorant)' }}>
                {queueStats.completed}/{queueStats.queueSize} Completed
              </div>
              {/* Progress Bar */}
              <div className="w-full max-w-md h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#1E3A5F] transition-all duration-500"
                  style={{ width: `${(queueStats.completed / queueStats.queueSize) * 100}%` }}
                />
              </div>
              <div className="text-gray-500 text-sm">
                {queueStats.queueSize - queueStats.completed} remaining in queue
              </div>
            </div>

            {/* Start button */}
            <div className="pt-4 flex flex-col items-center gap-4">
              <button
                onClick={handleBegin}
                className="px-8 py-4 bg-[#1E3A5F] hover:bg-[#2C5282] text-white rounded-lg transition-colors duration-200 text-xl"
                style={{ fontFamily: 'var(--font-cormorant)' }}
              >
                Start
              </button>

              {/* Streak Counter */}
              {streak > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-2xl">🔥</span>
                  <span
                    className={`text-3xl font-bold ${getStreakColor(streak)}`}
                    style={{
                      fontFamily: 'var(--font-cormorant)',
                      ...(streak % 101 === 0 && streak > 0 ? {
                        backgroundImage: 'linear-gradient(to right, #ef4444, #f59e0b, #10b981, #3b82f6, #8b5cf6)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text'
                      } : {})
                    }}
                  >
                    {streak} day
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
