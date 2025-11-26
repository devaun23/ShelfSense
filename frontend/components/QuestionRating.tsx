'use client';

import { useState } from 'react';

interface QuestionRatingProps {
  questionId: string;
  userId: string;
  onRatingComplete: () => void;
}

export default function QuestionRating({ questionId, userId, onRatingComplete }: QuestionRatingProps) {
  const [showModal, setShowModal] = useState(false);
  const [selectedRating, setSelectedRating] = useState<boolean | null>(null);
  const [feedback, setFeedback] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleRatingClick = (rating: boolean) => {
    setSelectedRating(rating);
    setShowModal(true);
  };

  const handleSubmit = async () => {
    if (selectedRating === null) return;

    setSubmitting(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/questions/rate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question_id: questionId,
          user_id: userId,
          rating: selectedRating,
          feedback_text: feedback.trim() || null,
        }),
      });

      if (response.ok) {
        // Close modal and trigger next question
        setShowModal(false);
        setFeedback('');
        setSelectedRating(null);
        onRatingComplete();
      } else {
        console.error('Failed to submit rating');
      }
    } catch (error) {
      console.error('Error submitting rating:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSkip = () => {
    setShowModal(false);
    setFeedback('');
    setSelectedRating(null);
    onRatingComplete();
  };

  return (
    <>
      {/* Minimal Floating Rating Buttons - Bottom Right */}
      <div className="fixed bottom-6 right-6 flex gap-2 z-50">
        <button
          onClick={() => handleRatingClick(true)}
          className="w-12 h-12 rounded-lg bg-gray-900 hover:bg-[#10b981] border border-gray-800 hover:border-[#10b981] text-gray-400 hover:text-white flex items-center justify-center transition-all"
          title="Good question"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </button>
        <button
          onClick={() => handleRatingClick(false)}
          className="w-12 h-12 rounded-lg bg-gray-900 hover:bg-[#ef4444] border border-gray-800 hover:border-[#ef4444] text-gray-400 hover:text-white flex items-center justify-center transition-all"
          title="Bad question"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Minimal Feedback Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[100] p-4">
          <div className="bg-gray-950 rounded-lg max-w-md w-full p-6 border border-gray-800">
            <h2 className="text-xl font-semibold text-white mb-2">
              {selectedRating ? 'Good Question' : 'Report Issue'}
            </h2>
            <p className="text-gray-500 text-sm mb-4">
              {selectedRating
                ? 'What made this question good?'
                : 'Help improve by explaining the issue'}
            </p>

            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder={
                selectedRating
                  ? 'Optional feedback...'
                  : 'What was wrong with this question?'
              }
              className="w-full h-24 px-4 py-3 bg-black border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:border-[#4169E1] resize-none"
              autoFocus
            />

            <div className="flex gap-2 mt-4">
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="flex-1 px-4 py-3 bg-[#4169E1] hover:bg-[#5B7FE8] disabled:bg-gray-800 text-white rounded-lg transition-colors"
              >
                {submitting ? 'Submitting...' : 'Submit'}
              </button>
              <button
                onClick={handleSkip}
                disabled={submitting}
                className="px-4 py-3 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-900 text-gray-400 rounded-lg transition-colors"
              >
                Skip
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
