'use client';

import { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import { getSpecialtyBySlug } from '@/lib/specialties';
import EyeLogo from '@/components/icons/EyeLogo';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

interface PortalReviewsProps {
  params: Promise<{ specialty: string }>;
}

interface ReviewItem {
  questionId: string;
  topic: string;
  dueDate: string;
  stage: number;
}

export default function PortalReviews({ params }: PortalReviewsProps) {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const resolvedParams = use(params);
  const specialty = getSpecialtyBySlug(resolvedParams.specialty);
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [dueCount, setDueCount] = useState(0);

  useEffect(() => {
    if (user?.userId && specialty) {
      fetchReviews();
    }
  }, [user?.userId, specialty?.apiName]);

  const fetchReviews = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const specialtyParam = specialty?.apiName
        ? `&specialty=${encodeURIComponent(specialty.apiName)}`
        : '';

      const response = await fetch(
        `${apiUrl}/api/reviews/due?user_id=${user?.userId}${specialtyParam}`
      );

      if (response.ok) {
        const data = await response.json();
        setReviews(data.reviews || []);
        setDueCount(data.due_count || 0);
      }
    } catch (error) {
      console.error('Error fetching reviews:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartReviews = () => {
    const specialtyParam = specialty?.apiName
      ? `specialty=${encodeURIComponent(specialty.apiName)}`
      : '';
    router.push(`/study?${specialtyParam}&mode=review`);
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
        Reviews Due
      </h1>
      <p
        className="text-gray-500 mb-8 text-center animate-bounce-in"
        style={{ animationDelay: '150ms' }}
      >
        Spaced repetition for long-term retention
      </p>

      {/* Reviews Content */}
      {loading ? (
        <div className="w-full max-w-sm">
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 animate-pulse">
            <div className="h-12 bg-gray-800 rounded w-16 mx-auto mb-2" />
            <div className="h-4 bg-gray-800 rounded w-24 mx-auto" />
          </div>
        </div>
      ) : dueCount > 0 ? (
        <div className="w-full max-w-sm space-y-4">
          {/* Due count card */}
          <div
            className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 text-center animate-bounce-in"
            style={{ animationDelay: '200ms' }}
          >
            <div className="text-4xl font-bold text-white mb-2">{dueCount}</div>
            <div className="text-gray-500">questions due for review</div>
          </div>

          {/* Start button */}
          <button
            onClick={handleStartReviews}
            className="w-full px-6 py-4 bg-white hover:bg-gray-100 text-black font-medium rounded-full transition-all duration-200 ease-out active:scale-95 hover:shadow-lg hover:shadow-white/10 animate-bounce-in"
            style={{ fontFamily: 'var(--font-serif)', animationDelay: '280ms' }}
          >
            Start Reviews
          </button>
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
            No reviews due right now.
          </p>
          <p className="text-gray-600 text-sm">
            Keep studying and reviews will appear as questions become due.
          </p>
        </div>
      )}

      {/* Back Button */}
      <button
        onClick={() => router.push(basePath)}
        className="mt-8 text-gray-600 hover:text-gray-400 text-sm transition-colors animate-bounce-in"
        style={{ animationDelay: dueCount > 0 ? '360ms' : '280ms' }}
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
