'use client';

import { useEffect, useState, use } from 'react';
import Link from 'next/link';
import { useUser } from '@/contexts/UserContext';
import { getSpecialtyBySlug } from '@/lib/specialties';

interface PortalWeakAreasProps {
  params: Promise<{ specialty: string }>;
}

interface WeakArea {
  topic: string;
  accuracy: number;
  totalQuestions: number;
  lastAttempted: string | null;
}

export default function PortalWeakAreas({ params }: PortalWeakAreasProps) {
  const { user, isLoading } = useUser();
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
      const specialtyParam = specialty?.apiName ? `&specialty=${encodeURIComponent(specialty.apiName)}` : '';

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

  if (isLoading || !specialty) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  const basePath = `/portal/${specialty.slug}`;

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">Weak Areas</h1>
        <p className="text-gray-400">
          Topics in {specialty.name} where you need more practice
        </p>
      </div>

      {/* Weak Areas List */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-gray-900 rounded-xl p-6 border border-gray-800 animate-pulse">
              <div className="h-5 bg-gray-800 rounded w-1/3 mb-3" />
              <div className="h-3 bg-gray-800 rounded w-1/4" />
            </div>
          ))}
        </div>
      ) : weakAreas.length > 0 ? (
        <div className="space-y-4">
          {weakAreas.map((area, index) => (
            <div
              key={index}
              className="bg-gray-900 rounded-xl p-6 border border-gray-800 hover:border-gray-700 transition-colors"
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-medium text-white">{area.topic}</h3>
                <span className={`text-sm font-medium ${
                  area.accuracy < 0.4 ? 'text-red-400' :
                  area.accuracy < 0.6 ? 'text-yellow-400' :
                  'text-gray-400'
                }`}>
                  {Math.round(area.accuracy * 100)}% accuracy
                </span>
              </div>

              {/* Progress bar */}
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden mb-3">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    area.accuracy < 0.4 ? 'bg-red-500' :
                    area.accuracy < 0.6 ? 'bg-yellow-500' :
                    'bg-blue-500'
                  }`}
                  style={{ width: `${area.accuracy * 100}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">
                  {area.totalQuestions} questions attempted
                </span>
                <Link
                  href={`${basePath}/study?mode=weak&topic=${encodeURIComponent(area.topic)}`}
                  className="text-blue-400 hover:text-blue-300 transition-colors"
                >
                  Practice this topic &rarr;
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl p-8 border border-gray-800 text-center">
          <div className="text-4xl mb-4">🎯</div>
          <h3 className="text-lg font-medium text-white mb-2">No weak areas identified yet</h3>
          <p className="text-gray-400 mb-6">
            Complete more questions to identify areas that need improvement
          </p>
          <Link
            href={`${basePath}/study`}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
          >
            Start Practicing
          </Link>
        </div>
      )}
    </div>
  );
}
