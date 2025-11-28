'use client';

import { useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { getSpecialtyBySlug, isValidPortalSlug } from '@/lib/specialties';
import { useExam } from '@/contexts/ExamContext';
import PortalSidebar from '@/components/PortalSidebar';

interface PortalLayoutProps {
  children: React.ReactNode;
  params: Promise<{ specialty: string }>;
}

export default function PortalLayout({ children, params }: PortalLayoutProps) {
  const router = useRouter();
  const { enterPortal, currentExam } = useExam();
  const resolvedParams = use(params);
  const specialty = getSpecialtyBySlug(resolvedParams.specialty);

  // Validate specialty slug on mount
  useEffect(() => {
    if (!isValidPortalSlug(resolvedParams.specialty)) {
      router.replace('/');
      return;
    }

    // Sync exam context with URL
    if (specialty && currentExam?.slug !== resolvedParams.specialty) {
      enterPortal(resolvedParams.specialty);
    }
  }, [resolvedParams.specialty, specialty, currentExam, enterPortal, router]);

  // Show nothing while redirecting invalid slugs
  if (!specialty) {
    return null;
  }

  return (
    <div className="flex h-screen bg-black">
      <PortalSidebar specialty={specialty} />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
