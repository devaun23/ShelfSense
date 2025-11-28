'use client';

import { useEffect, use } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getSpecialtyBySlug } from '@/lib/specialties';

interface PortalStudyProps {
  params: Promise<{ specialty: string }>;
}

export default function PortalStudy({ params }: PortalStudyProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resolvedParams = use(params);
  const specialty = getSpecialtyBySlug(resolvedParams.specialty);

  useEffect(() => {
    if (specialty) {
      // Redirect to main study page with specialty parameter
      // This leverages the existing study page implementation
      const mode = searchParams.get('mode') || '';
      const modeParam = mode ? `&mode=${mode}` : '';
      const specialtyParam = specialty.apiName ? `specialty=${encodeURIComponent(specialty.apiName)}` : '';
      router.replace(`/study?${specialtyParam}${modeParam}`);
    }
  }, [specialty, router, searchParams]);

  // Show loading while redirecting
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4" />
        <p className="text-gray-400">Loading study session...</p>
      </div>
    </div>
  );
}
