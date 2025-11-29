'use client';

import { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import { getSpecialtyBySlug } from '@/lib/specialties';
import PortalSidebar from '@/components/PortalSidebar';

interface PortalStudyProps {
  params: Promise<{ specialty: string }>;
}

export default function PortalStudy({ params }: PortalStudyProps) {
  const router = useRouter();
  const resolvedParams = use(params);
  const specialty = getSpecialtyBySlug(resolvedParams.specialty);
  const [isNavigating, setIsNavigating] = useState(false);

  useEffect(() => {
    if (specialty && !isNavigating) {
      setIsNavigating(true);
      // Navigate to main study page with specialty and portal context
      const specialtyParam = specialty.apiName ? `specialty=${encodeURIComponent(specialty.apiName)}` : '';
      const portalParam = `portal=${encodeURIComponent(specialty.slug)}`;
      const params = [specialtyParam, portalParam].filter(Boolean).join('&');
      router.push(`/study?${params}`);
    }
  }, [specialty, router, isNavigating]);

  // Show portal layout while navigating (no jarring spinner)
  if (!specialty) {
    return (
      <div className="flex h-screen bg-black text-white">
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-500">Specialty not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-black text-white">
      <PortalSidebar specialty={specialty} />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="text-center space-y-4">
              <h2 className="text-xl font-medium text-gray-400">Loading Study Mode...</h2>
              <p className="text-sm text-gray-600">Preparing your {specialty.name} questions</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
