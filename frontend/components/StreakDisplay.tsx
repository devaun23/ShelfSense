'use client';

import { useState, useEffect } from 'react';
import { Flame, Trophy, Target, Zap } from 'lucide-react';

interface StreakData {
  current_streak: number;
  best_streak: number;
  studied_today: boolean;
  streak_at_risk: boolean;
  next_milestone: number | null;
  current_milestone: number | null;
  days_to_next_milestone: number | null;
}

interface StreakCelebration {
  type: string;
  message: string;
  days?: number;
}

interface StreakDisplayProps {
  compact?: boolean;
  showLeaderboard?: boolean;
  celebrations?: StreakCelebration[];
  onCelebrationDismiss?: () => void;
}

export default function StreakDisplay({
  compact = false,
  showLeaderboard = false,
  celebrations = [],
  onCelebrationDismiss
}: StreakDisplayProps) {
  const [streakData, setStreakData] = useState<StreakData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCelebration, setShowCelebration] = useState(false);

  useEffect(() => {
    fetchStreakData();
  }, []);

  useEffect(() => {
    if (celebrations.length > 0) {
      setShowCelebration(true);
      const timer = setTimeout(() => {
        setShowCelebration(false);
        onCelebrationDismiss?.();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [celebrations, onCelebrationDismiss]);

  async function fetchStreakData() {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/gamification/streaks`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });

      if (res.ok) {
        const data = await res.json();
        setStreakData(data);
      }
    } catch (error) {
      console.error('Failed to fetch streak data:', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse bg-zinc-800/50 rounded-lg p-3">
        <div className="h-6 w-24 bg-zinc-700 rounded" />
      </div>
    );
  }

  if (!streakData) {
    return null;
  }

  // Celebration overlay
  const celebrationBanner = showCelebration && celebrations.length > 0 && (
    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 animate-bounce">
      <div className="bg-gradient-to-r from-amber-500 to-orange-500 text-white px-6 py-3 rounded-full shadow-lg flex items-center gap-2">
        <Flame className="w-5 h-5" />
        <span className="font-semibold">{celebrations[0].message}</span>
      </div>
    </div>
  );

  // Compact mode - just the streak count with flame icon
  if (compact) {
    return (
      <>
        {celebrationBanner}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${
          streakData.current_streak > 0
            ? 'bg-gradient-to-r from-orange-500/20 to-amber-500/20 border border-orange-500/30'
            : 'bg-zinc-800/50 border border-zinc-700/50'
        }`}>
          <Flame className={`w-4 h-4 ${
            streakData.current_streak > 0 ? 'text-orange-400' : 'text-zinc-500'
          }`} />
          <span className={`font-semibold ${
            streakData.current_streak > 0 ? 'text-orange-300' : 'text-zinc-400'
          }`}>
            {streakData.current_streak}
          </span>
          {streakData.streak_at_risk && (
            <span className="text-xs text-orange-400 animate-pulse">!</span>
          )}
        </div>
      </>
    );
  }

  // Full display mode
  return (
    <>
      {celebrationBanner}
      <div className="bg-zinc-800/50 rounded-xl border border-zinc-700/50 p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
            <Flame className="w-5 h-5 text-orange-400" />
            Study Streak
          </h3>
          {streakData.studied_today && (
            <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full">
              Studied Today
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* Current Streak */}
          <div className={`p-4 rounded-lg ${
            streakData.current_streak > 0
              ? 'bg-gradient-to-br from-orange-500/20 to-amber-600/20 border border-orange-500/30'
              : 'bg-zinc-800 border border-zinc-700'
          }`}>
            <div className="flex items-center gap-2 mb-1">
              <Zap className={`w-4 h-4 ${
                streakData.current_streak > 0 ? 'text-orange-400' : 'text-zinc-500'
              }`} />
              <span className="text-sm text-zinc-400">Current</span>
            </div>
            <div className={`text-3xl font-bold ${
              streakData.current_streak > 0 ? 'text-orange-300' : 'text-zinc-500'
            }`}>
              {streakData.current_streak}
              <span className="text-base font-normal text-zinc-500 ml-1">days</span>
            </div>
          </div>

          {/* Best Streak */}
          <div className="p-4 rounded-lg bg-zinc-800 border border-zinc-700">
            <div className="flex items-center gap-2 mb-1">
              <Trophy className="w-4 h-4 text-amber-500" />
              <span className="text-sm text-zinc-400">Personal Best</span>
            </div>
            <div className="text-3xl font-bold text-amber-400">
              {streakData.best_streak}
              <span className="text-base font-normal text-zinc-500 ml-1">days</span>
            </div>
          </div>
        </div>

        {/* Streak at risk warning */}
        {streakData.streak_at_risk && (
          <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-3 mb-4">
            <p className="text-sm text-orange-300 flex items-center gap-2">
              <Flame className="w-4 h-4 animate-pulse" />
              Your streak is at risk! Study today to keep it going.
            </p>
          </div>
        )}

        {/* Next milestone */}
        {streakData.next_milestone && streakData.days_to_next_milestone && (
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-zinc-400">
              <Target className="w-4 h-4" />
              <span>Next milestone: {streakData.next_milestone} days</span>
            </div>
            <span className="text-zinc-500">
              {streakData.days_to_next_milestone} days to go
            </span>
          </div>
        )}

        {/* Progress bar to next milestone */}
        {streakData.next_milestone && (
          <div className="mt-2 h-2 bg-zinc-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-orange-500 to-amber-500 rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, (streakData.current_streak / streakData.next_milestone) * 100)}%`
              }}
            />
          </div>
        )}
      </div>
    </>
  );
}
