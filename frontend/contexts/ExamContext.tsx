'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useUser } from './UserContext';
import { Specialty, getSpecialtyBySlug, ALL_PORTALS } from '@/lib/specialties';

// ==================== Types ====================

interface ExamContextType {
  // Current exam state
  currentExam: Specialty | null;
  isInPortal: boolean;

  // Actions
  enterPortal: (slug: string) => void;
  exitPortal: () => void;

  // Helpers
  getApiParam: () => string; // Returns apiName for API calls (empty string if no filter)
  getPortalPath: (subPath?: string) => string; // Returns full portal path

  // Loading state
  isHydrated: boolean;
}

const ExamContext = createContext<ExamContextType | undefined>(undefined);

// ==================== Storage Key ====================

const CURRENT_EXAM_KEY = 'shelfsense_current_exam';

// ==================== Provider ====================

export function ExamProvider({ children }: { children: ReactNode }) {
  const { user } = useUser();
  const [currentExam, setCurrentExam] = useState<Specialty | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  // Hydrate from localStorage on mount
  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsHydrated(true);
      return;
    }

    // Only hydrate once we have a user
    if (user?.userId) {
      const storedSlug = localStorage.getItem(`${CURRENT_EXAM_KEY}_${user.userId}`);
      if (storedSlug) {
        const exam = getSpecialtyBySlug(storedSlug);
        setCurrentExam(exam);
      }
    }
    setIsHydrated(true);
  }, [user?.userId]);

  // Persist to localStorage when exam changes
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!isHydrated) return;

    if (user?.userId) {
      if (currentExam) {
        localStorage.setItem(`${CURRENT_EXAM_KEY}_${user.userId}`, currentExam.slug);
      } else {
        localStorage.removeItem(`${CURRENT_EXAM_KEY}_${user.userId}`);
      }
    }
  }, [currentExam, user?.userId, isHydrated]);

  // ==================== Actions ====================

  const enterPortal = useCallback((slug: string) => {
    const exam = getSpecialtyBySlug(slug);
    if (exam) {
      setCurrentExam(exam);
    }
  }, []);

  const exitPortal = useCallback(() => {
    setCurrentExam(null);
  }, []);

  // ==================== Helpers ====================

  const getApiParam = useCallback((): string => {
    // Returns the apiName for backend API calls
    // Empty string means no specialty filter (all questions)
    return currentExam?.apiName || '';
  }, [currentExam]);

  const getPortalPath = useCallback((subPath: string = ''): string => {
    if (!currentExam) return '/';
    const base = `/portal/${currentExam.slug}`;
    return subPath ? `${base}/${subPath}` : base;
  }, [currentExam]);

  // ==================== Context Value ====================

  const value: ExamContextType = {
    currentExam,
    isInPortal: !!currentExam,
    enterPortal,
    exitPortal,
    getApiParam,
    getPortalPath,
    isHydrated,
  };

  return (
    <ExamContext.Provider value={value}>
      {children}
    </ExamContext.Provider>
  );
}

// ==================== Hook ====================

export function useExam() {
  const context = useContext(ExamContext);
  if (context === undefined) {
    throw new Error('useExam must be used within an ExamProvider');
  }
  return context;
}

// ==================== Utility Hook ====================

// Hook to get exam from URL params (for portal pages)
export function useExamFromParams(slug: string | undefined): Specialty | null {
  if (!slug) return null;
  return getSpecialtyBySlug(slug);
}
