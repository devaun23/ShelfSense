'use client';

import { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { getSpecialtyBySlug } from '@/lib/specialties';
import EyeLogo from '@/components/icons/EyeLogo';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

interface PortalWeakAreasProps {
  params: Promise<{ specialty: string }>;
}

interface WeakArea {
  topic: string;
  accuracy: number;
  totalQuestions: number;
}

export default function PortalWeakAreas({ params }: PortalWeakAreasProps) {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const resolvedParams = use(params);
  const specialty = getSpecialtyBySlug(resolvedParams.specialty);
  const [weakAreas, setWeakAreas] = useState<WeakArea[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.userId && specialty) {
      fetchWeakAreas();
    }
  }, [user?.userId, specialty?.apiName]);

  const fetchWeakAreas = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const specialtyParam = specialty?.apiName
        ? `&specialty=${encodeURIComponent(specialty.apiName)}`
        : '';

      const response = await fetch(
        `${apiUrl}/api/analytics/weak-areas?user_id=${user?.userId}${specialtyParam}`
      );

      if (response.ok) {
        const data = await response.json();
        setWeakAreas(data.weak_areas || []);
      }
    } catch (error) {
      console.error('Error fetching weak areas:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePracticeTopic = (topic: string) => {
    const specialtyParam = specialty?.apiName
      ? `specialty=${encodeURIComponent(specialty.apiName)}`
      : '';
    router.push(`/study?${specialtyParam}&topic=${encodeURIComponent(topic)}`);
  };

  if (userLoading || !specialty) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </main>
    );
  }

  const basePath = `/portal/${specialty.slug}`;

  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center px-4 py-12 animate-fade-in">
      {/* Header */}
      <div className="mb-8 animate-bounce-in" style={{ animationDelay: '0ms' }}>
        <EyeLogo size={40} />
      </div>

      {/* Title */}
      <h1
        className="text-2xl font-semibold text-white mb-2 text-center animate-bounce-in"
        style={{ fontFamily: 'var(--font-serif)', animationDelay: '100ms' }}
      >
        Weak Areas
      </h1>
      <p
        className="text-gray-500 mb-8 text-center animate-bounce-in"
        style={{ animationDelay: '150ms' }}
      >
        Topics that need more attention
      </p>

      {/* Weak Areas List */}
      {loading ? (
        <div className="w-full max-w-md space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 animate-pulse"
            >
              <div className="h-5 bg-gray-800 rounded w-2/3 mb-2" />
              <div className="h-2 bg-gray-800 rounded w-full" />
            </div>
          ))}
        </div>
      ) : weakAreas.length > 0 ? (
        <div className="w-full max-w-md space-y-3">
          {weakAreas.map((area, index) => (
            <button
              key={index}
              onClick={() => handlePracticeTopic(area.topic)}
              className="w-full bg-gray-900/50 border border-gray-800 hover:border-gray-700 rounded-xl p-4 text-left transition-all duration-200 animate-bounce-in"
              style={{ animationDelay: `${200 + index * 80}ms` }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-white font-medium">{area.topic}</span>
                <span
                  className={`text-sm ${
                    area.accuracy < 0.4
                      ? 'text-red-400'
                      : area.accuracy < 0.6
                      ? 'text-yellow-400'
                      : 'text-gray-400'
                  }`}
                >
                  {Math.round(area.accuracy * 100)}%
                </span>
              </div>
              {/* Progress bar */}
              <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    area.accuracy < 0.4
                      ? 'bg-red-500'
                      : area.accuracy < 0.6
                      ? 'bg-yellow-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${area.accuracy * 100}%` }}
                />
              </div>
              <div className="mt-2 text-xs text-gray-600">
                {area.totalQuestions} questions
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div
          className="text-center py-8 animate-bounce-in"
          style={{ animationDelay: '200ms' }}
        >
          <p
            className="text-gray-500 mb-4"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            No weak areas identified yet.
          </p>
          <p className="text-gray-600 text-sm">
            Complete more questions to identify areas that need improvement.
          </p>
        </div>
      )}

      {/* Back Button */}
      <button
        onClick={() => router.push(basePath)}
        className="mt-8 text-gray-600 hover:text-gray-400 text-sm transition-colors animate-bounce-in"
        style={{ animationDelay: `${200 + weakAreas.length * 80 + 80}ms` }}
      >
        Back to {specialty.name}
      </button>

      {/* Animation styles */}
      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes bounceIn {
          0% {
            opacity: 0;
            transform: scale(0.3) translateY(20px);
          }
          50% { transform: scale(1.05) translateY(-5px); }
          70% { transform: scale(0.95) translateY(2px); }
          100% {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        .animate-fade-in {
          animation: fadeIn 0.3s ease-out forwards;
        }
        .animate-bounce-in {
          opacity: 0;
          animation: bounceIn 0.5s ease-out forwards;
        }
      `}</style>
    </main>
  );
}
