'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useUser as useClerkUser, useAuth } from '@clerk/nextjs';

// ==================== Types ====================

interface User {
  userId: string;
  fullName: string;
  firstName: string;
  email: string;
  emailVerified: boolean;
  targetScore: number | null;
  examDate: string | null;
  imageUrl?: string;
  isAdmin: boolean;
}

interface UserContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  // Token methods
  getAccessToken: () => Promise<string | null>;
  // Profile methods
  updateTargetScore: (score: number) => Promise<void>;
  updateExamDate: (date: string) => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

// ==================== Storage Keys ====================

const USER_PREFERENCES_KEY = 'shelfsense_user_prefs';

// ==================== API Helpers ====================

const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ==================== Provider ====================

export function UserProvider({ children }: { children: ReactNode }) {
  const { user: clerkUser, isLoaded: clerkLoaded } = useClerkUser();
  const { getToken } = useAuth();
  const [targetScore, setTargetScore] = useState<number | null>(null);
  const [examDate, setExamDate] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);
  const [prefsLoaded, setPrefsLoaded] = useState(false);

  // Load user preferences from localStorage on mount
  useEffect(() => {
    if (typeof window === 'undefined') {
      setPrefsLoaded(true);
      return;
    }

    if (clerkUser?.id) {
      const storedPrefs = localStorage.getItem(`${USER_PREFERENCES_KEY}_${clerkUser.id}`);
      if (storedPrefs) {
        try {
          const prefs = JSON.parse(storedPrefs);
          setTargetScore(prefs.targetScore || null);
          setExamDate(prefs.examDate || null);
        } catch (error) {
          console.error('Failed to parse stored preferences:', error);
        }
      }
    }
    setPrefsLoaded(true);
  }, [clerkUser?.id]);

  // Save preferences to localStorage when they change
  useEffect(() => {
    if (typeof window === 'undefined') return;

    if (clerkUser?.id && prefsLoaded) {
      localStorage.setItem(
        `${USER_PREFERENCES_KEY}_${clerkUser.id}`,
        JSON.stringify({ targetScore, examDate })
      );
    }
  }, [clerkUser?.id, targetScore, examDate, prefsLoaded]);

  // Sync user with backend when Clerk user is available
  useEffect(() => {
    if (clerkUser) {
      syncUserWithBackend();
    }
  }, [clerkUser?.id]);

  const syncUserWithBackend = async () => {
    if (!clerkUser) return;

    try {
      const token = await getToken();
      const response = await fetch(`${getApiUrl()}/api/auth/clerk-sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          clerk_user_id: clerkUser.id,
          email: clerkUser.primaryEmailAddress?.emailAddress,
          full_name: clerkUser.fullName || clerkUser.firstName || 'User',
          first_name: clerkUser.firstName || 'User',
          image_url: clerkUser.imageUrl,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setIsAdmin(data.is_admin || false);
      } else {
        console.error('Failed to sync user with backend');
      }
    } catch (error) {
      console.error('Error syncing user:', error);
    }
  };

  // ==================== Token Management ====================

  const getAccessToken = useCallback(async (): Promise<string | null> => {
    try {
      const token = await getToken();
      return token;
    } catch (error) {
      console.error('Error getting access token:', error);
      return null;
    }
  }, [getToken]);

  // ==================== Profile Methods ====================

  const updateTargetScore = async (score: number) => {
    setTargetScore(score);

    // Optionally sync with backend
    if (clerkUser) {
      try {
        const token = await getToken();
        await fetch(`${getApiUrl()}/api/profile/me/target`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            user_id: clerkUser.id,
            target_score: score,
          }),
        });
      } catch (error) {
        console.error('Error updating target score:', error);
      }
    }
  };

  const updateExamDate = async (date: string) => {
    setExamDate(date);

    // Optionally sync with backend
    if (clerkUser) {
      try {
        const token = await getToken();
        await fetch(`${getApiUrl()}/api/profile/me/exam-date`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            user_id: clerkUser.id,
            exam_date: date,
          }),
        });
      } catch (error) {
        console.error('Error updating exam date:', error);
      }
    }
  };

  // ==================== Derived User Object ====================

  const user: User | null = clerkUser
    ? {
        userId: clerkUser.id,
        fullName: clerkUser.fullName || clerkUser.firstName || 'User',
        firstName: clerkUser.firstName || 'User',
        email: clerkUser.primaryEmailAddress?.emailAddress || '',
        emailVerified: clerkUser.primaryEmailAddress?.verification?.status === 'verified',
        targetScore,
        examDate,
        imageUrl: clerkUser.imageUrl,
        isAdmin,
      }
    : null;

  // ==================== Context Value ====================

  const value: UserContextType = {
    user,
    isLoading: !clerkLoaded,
    isAuthenticated: !!clerkUser,
    getAccessToken,
    updateTargetScore,
    updateExamDate,
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
}

// ==================== Hook ====================

export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}
