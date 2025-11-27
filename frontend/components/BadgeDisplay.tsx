'use client';

import { useState, useEffect } from 'react';
import {
  Flame, Trophy, Target, Star, Medal, Crown,
  Book, BookOpen, Rocket, Brain, Zap, Check,
  Flag, Sparkles, Moon, Sun, TrendingUp, Diamond,
  Award, ChevronRight
} from 'lucide-react';

interface BadgeInfo {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  earned: boolean;
  earned_at?: string;
  progress?: number;
  requirement?: string;
}

interface BadgesResponse {
  earned: BadgeInfo[];
  in_progress: BadgeInfo[];
  total_earned: number;
  total_available: number;
}

interface BadgeDisplayProps {
  compact?: boolean;
  onBadgeClick?: (badge: BadgeInfo) => void;
}

// Map icon names to Lucide icons
const iconMap: Record<string, React.ElementType> = {
  fire: Flame,
  flame: Flame,
  trophy: Trophy,
  crown: Crown,
  star: Star,
  medal: Medal,
  book: Book,
  books: BookOpen,
  library: BookOpen,
  rocket: Rocket,
  brain: Brain,
  target: Target,
  bullseye: Target,
  lightning: Zap,
  chart: TrendingUp,
  trending: TrendingUp,
  diamond: Diamond,
  check: Check,
  flag: Flag,
  sparkles: Sparkles,
  moon: Moon,
  sun: Sun,
  default: Award
};

function getIcon(iconName: string): React.ElementType {
  return iconMap[iconName] || iconMap.default;
}

// Category colors
const categoryColors: Record<string, { bg: string; text: string; border: string }> = {
  streak: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30' },
  volume: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
  accuracy: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30' },
  milestone: { bg: 'bg-violet-500/20', text: 'text-violet-400', border: 'border-violet-500/30' },
  special: { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30' }
};

function BadgeCard({ badge, size = 'normal' }: { badge: BadgeInfo; size?: 'small' | 'normal' }) {
  const Icon = getIcon(badge.icon);
  const colors = categoryColors[badge.category] || categoryColors.special;
  const isEarned = badge.earned;

  if (size === 'small') {
    return (
      <div
        className={`flex items-center gap-2 p-2 rounded-lg transition-all ${
          isEarned
            ? `${colors.bg} ${colors.border} border`
            : 'bg-zinc-800/50 border border-zinc-700/50 opacity-60'
        }`}
        title={badge.description}
      >
        <div className={`p-1.5 rounded-full ${isEarned ? colors.bg : 'bg-zinc-700'}`}>
          <Icon className={`w-4 h-4 ${isEarned ? colors.text : 'text-zinc-500'}`} />
        </div>
        <span className={`text-sm font-medium ${isEarned ? 'text-zinc-200' : 'text-zinc-500'}`}>
          {badge.name}
        </span>
      </div>
    );
  }

  return (
    <div
      className={`p-4 rounded-xl transition-all ${
        isEarned
          ? `${colors.bg} ${colors.border} border`
          : 'bg-zinc-800/30 border border-zinc-700/30 opacity-50'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-3 rounded-xl ${isEarned ? colors.bg : 'bg-zinc-700/50'}`}>
          <Icon className={`w-6 h-6 ${isEarned ? colors.text : 'text-zinc-500'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className={`font-semibold ${isEarned ? 'text-zinc-100' : 'text-zinc-500'}`}>
            {badge.name}
          </h4>
          <p className="text-sm text-zinc-400 mt-0.5">{badge.description}</p>

          {!isEarned && badge.progress !== undefined && badge.progress > 0 && (
            <div className="mt-2">
              <div className="h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                <div
                  className={`h-full ${colors.bg.replace('/20', '')} rounded-full transition-all`}
                  style={{ width: `${badge.progress * 100}%` }}
                />
              </div>
              <p className="text-xs text-zinc-500 mt-1">
                {Math.round(badge.progress * 100)}% complete
              </p>
            </div>
          )}

          {isEarned && badge.earned_at && (
            <p className="text-xs text-zinc-500 mt-1">
              Earned {new Date(badge.earned_at).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function BadgeDisplay({ compact = false, onBadgeClick }: BadgeDisplayProps) {
  const [badges, setBadges] = useState<BadgesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    fetchBadges();
  }, []);

  async function fetchBadges() {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/gamification/badges`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });

      if (res.ok) {
        const data = await res.json();
        setBadges(data);
      }
    } catch (error) {
      console.error('Failed to fetch badges:', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse bg-zinc-800/50 rounded-xl p-4">
        <div className="h-6 w-32 bg-zinc-700 rounded mb-4" />
        <div className="grid grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 bg-zinc-700/50 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (!badges) {
    return null;
  }

  // Compact mode - show summary and recent badges
  if (compact) {
    return (
      <div className="bg-zinc-800/50 rounded-xl border border-zinc-700/50 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-amber-400" />
            <h3 className="font-semibold text-zinc-100">Badges</h3>
          </div>
          <span className="text-sm text-zinc-400">
            {badges.total_earned} / {badges.total_available}
          </span>
        </div>

        {badges.earned.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {badges.earned.slice(0, 6).map(badge => (
              <BadgeCard key={badge.id} badge={badge} size="small" />
            ))}
            {badges.earned.length > 6 && (
              <button className="flex items-center gap-1 text-sm text-zinc-400 hover:text-zinc-300">
                +{badges.earned.length - 6} more
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        ) : (
          <p className="text-sm text-zinc-500">
            Start studying to earn your first badge!
          </p>
        )}
      </div>
    );
  }

  // Full display mode
  const categories = ['streak', 'volume', 'accuracy', 'milestone', 'special'];
  const allBadges = [...badges.earned, ...badges.in_progress];
  const filteredBadges = selectedCategory
    ? allBadges.filter(b => b.category === selectedCategory)
    : allBadges;

  return (
    <div className="bg-zinc-800/50 rounded-xl border border-zinc-700/50 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Award className="w-6 h-6 text-amber-400" />
          <h2 className="text-xl font-semibold text-zinc-100">Achievements</h2>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-amber-400 font-semibold">{badges.total_earned}</span>
          <span className="text-zinc-500">/ {badges.total_available} earned</span>
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
            selectedCategory === null
              ? 'bg-violet-600 text-white'
              : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
          }`}
        >
          All
        </button>
        {categories.map(cat => {
          const count = allBadges.filter(b => b.category === cat).length;
          const earnedCount = badges.earned.filter(b => b.category === cat).length;
          return (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                selectedCategory === cat
                  ? 'bg-violet-600 text-white'
                  : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
              }`}
            >
              {cat.charAt(0).toUpperCase() + cat.slice(1)} ({earnedCount}/{count})
            </button>
          );
        })}
      </div>

      {/* Badges Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredBadges.map(badge => (
          <BadgeCard
            key={badge.id}
            badge={badge}
            size="normal"
          />
        ))}
      </div>

      {filteredBadges.length === 0 && (
        <p className="text-center text-zinc-500 py-8">
          No badges in this category yet. Keep studying!
        </p>
      )}
    </div>
  );
}
