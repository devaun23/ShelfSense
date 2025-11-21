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
      // Track visits today using localStorage
      const today = new Date().toDateString();
      const visitKey = `visits_${user.userId}_${today}`;
      const visitsToday = parseInt(localStorage.getItem(visitKey) || '0') + 1;
      localStorage.setItem(visitKey, visitsToday.toString());

      const personalizedGreeting = generateGreeting({
        firstName: user.firstName,
        hour: new Date().getHours(),
        visitsToday: visitsToday
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

            {/* Start button */}
            <div className="pt-4 flex flex-col items-center gap-4">
              <button
                onClick={handleBegin}
                className="px-8 py-4 bg-[#1E3A5F] hover:bg-[#2C5282] text-white rounded-lg transition-colors duration-200 text-xl"
                style={{ fontFamily: 'var(--font-cormorant)' }}
              >
                Start
              </button>

              {/* Three Icons Row */}
              <div className="flex items-center justify-center gap-12 pt-8">
                {/* Streak Counter - Just the Number */}
                <div
                  className="cursor-pointer hover:scale-110 transition-transform group"
                  title="Current Streak"
                >
                  <span
                    className={`text-4xl font-bold ${getStreakColor(streak)}`}
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
                    {streak}
                  </span>
                </div>

                {/* Analytics - Caduceus Medical Symbol */}
                <div
                  className="cursor-pointer hover:scale-110 transition-transform group relative"
                  title="Analytics"
                >
                  <svg className="w-10 h-10 text-gray-500 hover:text-gray-400 transition-colors" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    {/* Central staff */}
                    <line x1="12" y1="4" x2="12" y2="20" strokeLinecap="round" />
                    {/* Wings at top */}
                    <path d="M12 6 Q9 4 7 5.5 Q9 6.5 12 6" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M12 6 Q15 4 17 5.5 Q15 6.5 12 6" strokeLinecap="round" strokeLinejoin="round" />
                    {/* Intertwined snakes - left snake starts on left */}
                    <path d="M9 8 Q12 9 15 10 Q12 11 9 12 Q12 13 15 14 Q12 15 9 16" strokeLinecap="round" />
                    {/* Right snake starts on right */}
                    <path d="M15 8 Q12 9 9 10 Q12 11 15 12 Q12 13 9 14 Q12 15 15 16" strokeLinecap="round" />
                    {/* Snake heads */}
                    <circle cx="9" cy="8" r="0.8" fill="currentColor" />
                    <circle cx="15" cy="8" r="0.8" fill="currentColor" />
                    {/* Snake tails */}
                    <circle cx="9" cy="16" r="0.6" fill="currentColor" />
                    <circle cx="15" cy="16" r="0.6" fill="currentColor" />
                  </svg>
                </div>

                {/* Calendar - Heatmap Icon */}
                <div
                  className="cursor-pointer hover:scale-110 transition-transform group relative"
                  title="Calendar"
                >
                  <svg className="w-10 h-10 text-gray-500 hover:text-gray-400 transition-colors" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="3" y1="10" x2="21" y2="10" strokeLinecap="round" />
                    <line x1="8" y1="2" x2="8" y2="6" strokeLinecap="round" />
                    <line x1="16" y1="2" x2="16" y2="6" strokeLinecap="round" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
