'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { useUser } from '@/contexts/UserContext';

interface ReviewItem {
  question_id: string;
  vignette: string;
  next_review_date: string;
  interval_days: number;
  ease_factor: number;
  repetitions: number;
  stage: string;
}

export default function ReviewModePage() {
  const router = useRouter();
  const { user, isLoading: userLoading } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [reviewStats, setReviewStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userLoading && !user) {
      router.push('/login');
      return;
    }

    if (user) {
      loadReviews();
      loadReviewStats();
    }
  }, [user, userLoading, router]);

  const loadReviews = async () => {
    if (!user) return;

    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${apiUrl}/api/study-modes/review-schedule?user_id=${user.userId}&days=1`
      );

      if (response.ok) {
        const data = await response.json();
        // Filter for today's reviews
        const today = new Date().toISOString().split('T')[0];
        const todayReviews = data.filter((review: ReviewItem) =>
          review.next_review_date.startsWith(today)
        );
        setReviews(todayReviews);
      } else {
        setError('Failed to load reviews. Please try again.');
      }
    } catch (error) {
      console.error('Error loading reviews:', error);
      setError('Network error. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadReviewStats = async () => {
    if (!user) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${apiUrl}/api/study-modes/review-stats?user_id=${user.userId}`
      );

      if (response.ok) {
        const data = await response.json();
        setReviewStats(data);
      }
    } catch (error) {
      console.error('Error loading review stats:', error);
    }
  };

  const handleStartReviews = () => {
    router.push('/reviews');
  };

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'Learning':
        return 'text-yellow-500';
      case 'Review':
        return 'text-blue-500';
      case 'Mastered':
        return 'text-green-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStageIcon = (stage: string) => {
    switch (stage) {
      case 'Learning':
        return '📖';
      case 'Review':
        return '🔄';
      case 'Mastered':
        return '✨';
      default:
        return '❓';
    }
  };

  if (loading) {
    return (
      <>
        <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}>
          <div className="flex items-center justify-center min-h-screen">
            <svg className="animate-spin h-16 w-16 text-white" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C11.172 2 10.5 2.672 10.5 3.5V5.145C9.419 5.408 8.414 5.877 7.536 6.514L6.379 5.357C5.793 4.771 4.843 4.771 4.257 5.357C3.671 5.943 3.671 6.893 4.257 7.479L5.414 8.636C4.777 9.514 4.308 10.519 4.045 11.6H2.5C1.672 11.6 1 12.272 1 13.1C1 13.928 1.672 14.6 2.5 14.6H4.145C4.408 15.681 4.877 16.686 5.514 17.564L4.357 18.721C3.771 19.307 3.771 20.257 4.357 20.843C4.943 21.429 5.893 21.429 6.479 20.843L7.636 19.686C8.514 20.323 9.519 20.792 10.6 21.055V22.5C10.6 23.328 11.272 24 12.1 24C12.928 24 13.6 23.328 13.6 22.5V20.855C14.681 20.592 15.686 20.123 16.564 19.486L17.721 20.643C18.307 21.229 19.257 21.229 19.843 20.643C20.429 20.057 20.429 19.107 19.843 18.521L18.686 17.364C19.323 16.486 19.792 15.481 20.055 14.4H21.5C22.328 14.4 23 13.728 23 12.9C23 12.072 22.328 11.4 21.5 11.4H19.855C19.592 10.319 19.123 9.314 18.486 8.436L19.643 7.279C20.229 6.693 20.229 5.743 19.643 5.157C19.057 4.571 18.107 4.571 17.521 5.157L16.364 6.314C15.486 5.677 14.481 5.208 13.4 4.945V3.5C13.4 2.672 12.728 2 11.9 2H12ZM12 8C14.209 8 16 9.791 16 12C16 14.209 14.209 16 12 16C9.791 16 8 14.209 8 12C8 9.791 9.791 8 12 8Z" />
            </svg>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className={`min-h-screen bg-black text-white transition-all duration-300 ${
        sidebarOpen ? 'md:ml-64' : 'ml-0'
      }`}>
        <div className="max-w-4xl mx-auto px-8 py-12">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-4" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              🔄 Review Mode
            </h1>
            <p className="text-xl text-gray-400">
              Spaced repetition reviews scheduled for today
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-900/20 border border-red-500/50 rounded-lg">
              <p className="text-red-400">{error}</p>
            </div>
          )}

          {/* Review Stats */}
          {reviewStats && (
            <div className="grid md:grid-cols-4 gap-4 mb-8">
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
                <div className="text-gray-400 text-sm mb-1">Total Reviews</div>
                <div className="text-3xl font-bold">{reviewStats.total_reviews}</div>
              </div>

              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
                <div className="text-yellow-400 text-sm mb-1">📖 Learning</div>
                <div className="text-3xl font-bold text-yellow-500">
                  {reviewStats.by_stage?.Learning || 0}
                </div>
              </div>

              <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
                <div className="text-blue-400 text-sm mb-1">🔄 Review</div>
                <div className="text-3xl font-bold text-blue-500">
                  {reviewStats.by_stage?.Review || 0}
                </div>
              </div>

              <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
                <div className="text-green-400 text-sm mb-1">✨ Mastered</div>
                <div className="text-3xl font-bold text-green-500">
                  {reviewStats.by_stage?.Mastered || 0}
                </div>
              </div>
            </div>
          )}

          {/* Today's Reviews */}
          {reviews.length > 0 ? (
            <>
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-6 mb-8">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold mb-2">
                      {reviews.length} {reviews.length === 1 ? 'Review' : 'Reviews'} Due Today
                    </h2>
                    <p className="text-gray-300">
                      Complete your reviews to maximize retention and long-term learning
                    </p>
                  </div>
                  <button
                    onClick={handleStartReviews}
                    className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200 text-lg font-semibold"
                  >
                    Start Reviews
                  </button>
                </div>
              </div>

              {/* Review Items */}
              <div className="space-y-4 mb-8">
                {reviews.map((review, index) => (
                  <div
                    key={index}
                    className="bg-gray-900 border border-gray-700 rounded-xl p-6 hover:border-blue-500/50 transition-all duration-200"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{getStageIcon(review.stage)}</span>
                        <div>
                          <div className={`text-sm font-semibold ${getStageColor(review.stage)}`}>
                            {review.stage}
                          </div>
                          <div className="text-xs text-gray-500">
                            Repetition {review.repetitions + 1}
                          </div>
                        </div>
                      </div>
                      <div className="text-right text-xs text-gray-500">
                        <div>Interval: {review.interval_days} days</div>
                        <div>Ease: {review.ease_factor.toFixed(2)}</div>
                      </div>
                    </div>
                    <p className="text-gray-300 line-clamp-2">
                      {review.vignette}
                    </p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-8 text-center mb-8">
              <div className="text-6xl mb-4">🎉</div>
              <h2 className="text-2xl font-bold mb-2 text-green-400">
                All caught up!
              </h2>
              <p className="text-gray-300 mb-4">
                You have no reviews scheduled for today. Great job staying on top of your studies!
              </p>
              <p className="text-sm text-gray-400">
                {reviewStats && reviewStats.total_reviews > 0
                  ? `You have ${reviewStats.total_reviews} reviews in your queue for future dates.`
                  : 'Start answering questions to build your review queue.'}
              </p>
            </div>
          )}

          {/* Spaced Repetition Info */}
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
            <h3 className="text-lg font-bold mb-4">📚 How Spaced Repetition Works</h3>
            <div className="space-y-3 text-sm text-gray-300">
              <p>
                <strong className="text-white">Learning Stage:</strong> Questions you recently got wrong.
                Reviewed frequently until you demonstrate understanding.
              </p>
              <p>
                <strong className="text-white">Review Stage:</strong> Questions you're learning.
                Review intervals gradually increase as you answer correctly.
              </p>
              <p>
                <strong className="text-white">Mastered Stage:</strong> Questions you know well.
                Reviewed at long intervals to maintain long-term retention.
              </p>
              <p className="text-blue-400">
                💡 The SM-2 algorithm automatically adjusts review timing based on your performance,
                optimizing your study time for maximum retention.
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-8 flex gap-4">
            {reviews.length > 0 && (
              <button
                onClick={handleStartReviews}
                className="flex-1 px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200 text-lg font-semibold"
              >
                Start Today's Reviews
              </button>
            )}
            <button
              onClick={() => router.push('/study-modes')}
              className="flex-1 px-8 py-4 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors duration-200 text-lg"
            >
              Back to Study Modes
            </button>
          </div>
        </div>
      </main>
    </>
  );
}
