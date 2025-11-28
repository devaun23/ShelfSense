'use client';

import { useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { getSpecialtyBySlug } from '@/lib/specialties';

interface PortalReviewsProps {
  params: Promise<{ specialty: string }>;
}

export default function PortalReviews({ params }: PortalReviewsProps) {
  const router = useRouter();
  const resolvedParams = use(params);
  const specialty = getSpecialtyBySlug(resolvedParams.specialty);

  useEffect(() => {
    if (specialty) {
      // Redirect to main reviews page
      // TODO: In Phase 4, we'll add specialty scoping to reviews
      router.replace('/reviews');
    }
  }, [specialty, router]);

  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4" />
        <p className="text-gray-400">Loading reviews...</p>
      </div>
    </div>
  );
}
