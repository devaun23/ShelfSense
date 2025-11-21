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
      {/* Floating Rating Buttons - Bottom Right */}
      <div className="fixed bottom-8 right-8 flex gap-3 z-50">
        <button
          onClick={() => handleRatingClick(true)}
          className="w-14 h-14 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white flex items-center justify-center shadow-lg transition-all hover:scale-110"
          title="Approve question (✓)"
        >
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </button>
        <button
          onClick={() => handleRatingClick(false)}
          className="w-14 h-14 rounded-full bg-red-600 hover:bg-red-700 text-white flex items-center justify-center shadow-lg transition-all hover:scale-110"
          title="Reject question (✗)"
        >
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Feedback Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[100] p-4">
          <div className="bg-gray-900 rounded-lg max-w-md w-full p-6 border border-gray-700">
            <h2 className="text-xl font-bold text-white mb-2">
              {selectedRating ? '✓ Great!' : '✗ What went wrong?'}
            </h2>
            <p className="text-gray-400 text-sm mb-4">
              {selectedRating
                ? 'Optional: Tell us what made this question good'
                : 'Help the AI improve by explaining the issue'}
            </p>

            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder={
                selectedRating
                  ? 'e.g., "Excellent clinical vignette, realistic distractors"'
                  : 'e.g., "Distractors too obvious" or "Lab values unrealistic"'
              }
              className="w-full h-32 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#1E3A5F] resize-none"
              autoFocus
            />

            <div className="flex gap-3 mt-4">
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="flex-1 px-4 py-3 bg-[#1E3A5F] hover:bg-[#2C5282] disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-semibold"
              >
                {submitting ? 'Submitting...' : 'Submit & Next Question'}
              </button>
              <button
                onClick={handleSkip}
                disabled={submitting}
                className="px-4 py-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-gray-300 rounded-lg transition-colors"
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
