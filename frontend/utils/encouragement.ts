/**
 * Encouragement Utility - Warm, supportive messages throughout ShelfSense
 *
 * Design principles:
 * - Friendly and supportive like Claude
 * - Concise and genuine (not over the top)
 * - Growth mindset: mistakes = learning opportunities
 * - Variety in some places, consistency in others
 * - Time-aware and context-aware
 */

// Helper to pick a random item from an array
const pick = <T>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)];

// ============================================
// CORRECT ANSWER FEEDBACK
// Varies each time - celebrates the win
// ============================================
const correctAnswerMessages = [
  "Nice work!",
  "You got it!",
  "Exactly right.",
  "Well done.",
  "That's correct!",
  "Nailed it.",
  "Spot on.",
  "Perfect.",
  "You're getting stronger.",
  "Great reasoning.",
];

// For streaks of correct answers
const correctStreakMessages: Record<number, string> = {
  3: "Three in a row - you're in the zone!",
  5: "Five straight! You're really dialed in.",
  7: "Seven correct - impressive focus.",
  10: "Ten in a row! You're mastering this.",
};

export function getCorrectAnswerMessage(correctStreak?: number): string {
  if (correctStreak && correctStreakMessages[correctStreak]) {
    return correctStreakMessages[correctStreak];
  }
  return pick(correctAnswerMessages);
}

// ============================================
// INCORRECT ANSWER FEEDBACK
// Supportive, not discouraging - learning opportunity
// ============================================
const incorrectAnswerMessages = [
  "Not quite, but you're learning.",
  "Close! Let's see why.",
  "This one's tricky. Here's what happened.",
  "Good try - let's break this down.",
  "That's okay. Every miss teaches something.",
  "Learning moment here.",
  "Let's figure this out together.",
];

// After multiple incorrect in a row - extra supportive
const encouragementAfterStruggle = [
  "Tough stretch, but you're building knowledge with each question.",
  "These are challenging. Keep going - it's working.",
  "This is exactly how learning works. You're doing great.",
  "Stick with it. The hard ones teach the most.",
];

export function getIncorrectAnswerMessage(incorrectStreak?: number): string {
  if (incorrectStreak && incorrectStreak >= 3) {
    return pick(encouragementAfterStruggle);
  }
  return pick(incorrectAnswerMessages);
}

// ============================================
// ERROR ANALYSIS MESSAGES
// Reframes mistakes as growth opportunities
// ============================================
export const errorAnalysisMessages = {
  loading: "Let's see what happened here...",
  acknowledgeButton: "Got it - this helps me improve",
  acknowledged: "Nice! You'll remember this one.",
  sectionHeaders: {
    why: "Here's what happened:",
    missed: "Key detail to remember:",
    reasoning: "The thinking process:",
    coaching: "Something to consider:",
  },
};

// ============================================
// SESSION SUMMARY MESSAGES
// Performance-based but always encouraging
// ============================================
interface SessionContext {
  accuracy: number;
  questionsAnswered: number;
  timeOfDay: 'morning' | 'afternoon' | 'evening' | 'night';
  isPersonalBest?: boolean;
  streakDays?: number;
}

export function getSessionSummaryMessage(context: SessionContext): {
  headline: string;
  subtext: string;
} {
  const { accuracy, questionsAnswered, timeOfDay, isPersonalBest, streakDays } = context;

  // Personal best takes priority
  if (isPersonalBest) {
    return {
      headline: "New personal best!",
      subtext: "You just topped your previous record. That's real progress.",
    };
  }

  // High performance (80%+)
  if (accuracy >= 80) {
    const headlines = [
      "Outstanding session!",
      "Really strong work.",
      "You crushed it.",
      "Excellent performance.",
    ];
    const subtexts = [
      "You're clearly getting comfortable with this material.",
      "Keep this up and you'll be more than ready.",
      "This kind of consistency is exactly what you need.",
    ];
    return { headline: pick(headlines), subtext: pick(subtexts) };
  }

  // Good performance (60-79%)
  if (accuracy >= 60) {
    const headlines = [
      "Solid session.",
      "Good work today.",
      "Making progress.",
      "Nice effort.",
    ];
    const subtexts = [
      "You're building a strong foundation. Some topics need a bit more attention.",
      "Every session like this moves you forward. Review the ones you missed.",
      "You're on the right track. The weak areas will strengthen with practice.",
    ];
    return { headline: pick(headlines), subtext: pick(subtexts) };
  }

  // Lower performance (<60%) - extra supportive
  const headlines = [
    "You showed up. That matters.",
    "Challenging session.",
    "Building your foundation.",
    "Every question counts.",
  ];
  const subtexts = [
    "Tough material, but you're doing the work. That's what matters most.",
    "The questions you missed? Those are your opportunities. You'll get them next time.",
    "Progress isn't always linear. You're learning more than you realize.",
    "Keep going. The hard sessions teach you the most.",
  ];
  return { headline: pick(headlines), subtext: pick(subtexts) };
}

// ============================================
// STREAK CELEBRATIONS
// Milestone-based encouragement
// ============================================
export function getStreakMessage(days: number): string | null {
  const milestones: Record<number, string> = {
    3: "3 days in a row! You're building momentum.",
    5: "5-day streak! Consistency is key.",
    7: "A full week! That's real commitment.",
    14: "Two weeks strong. You're serious about this.",
    21: "21 days - they say that's when habits form.",
    30: "30-day streak! You're unstoppable.",
    60: "60 days. This is elite-level dedication.",
    100: "100 days. Incredible discipline.",
  };
  return milestones[days] || null;
}

export function getStreakDisplayMessage(days: number): string {
  if (days === 0) return "Start your streak today";
  if (days === 1) return "1 day - keep it going!";
  if (days < 7) return `${days} days - building momentum`;
  if (days < 30) return `${days} days - you're on fire`;
  return `${days} days - incredible`;
}

// ============================================
// EMPTY STATES
// Positive framing for empty content
// ============================================
export const emptyStates = {
  noQuestions: {
    title: "No questions here yet",
    message: "Check back soon or try a different specialty.",
  },
  noReviews: {
    title: "You're all caught up!",
    message: "Keep studying to build your review queue.",
  },
  noFlagged: {
    title: "Nothing flagged yet",
    message: "Mark tricky questions while studying to revisit them here.",
  },
  noWeakAreas: {
    title: "Looking strong across the board!",
    message: "Keep practicing to maintain your skills.",
  },
  noAnalytics: {
    title: "Your stats will appear here",
    message: "Complete some questions to see your progress.",
  },
  noActivity: {
    title: "Your activity will show up here",
    message: "Start studying to build your heatmap.",
  },
};

// ============================================
// LOADING STATES
// Friendly loading messages
// ============================================
export const loadingMessages = {
  question: "Finding your next question...",
  analytics: "Crunching your numbers...",
  reviews: "Loading your reviews...",
  submitting: "Recording your answer...",
  errorAnalysis: "Let's see what happened...",
  generic: "Just a moment...",
};

// ============================================
// WEAK AREAS (Reframed as Growth Opportunities)
// ============================================
export const weakAreasMessages = {
  sectionTitle: "Areas to Strengthen",
  sectionSubtitle: "Focus here for the biggest gains",
  noWeakAreas: "You're solid across all topics - nice work!",
  encouragement: "These topics are your biggest opportunities to improve.",
};

// ============================================
// TIME-OF-DAY ACKNOWLEDGMENTS
// ============================================
export function getTimeAcknowledgment(): string | null {
  const hour = new Date().getHours();

  // Late night (11pm - 4am)
  if (hour >= 23 || hour < 4) {
    const messages = [
      "Late night session - take care of yourself too.",
      "Burning the midnight oil. Respect.",
      "Don't forget to rest. Sleep helps memory consolidation.",
    ];
    return pick(messages);
  }

  // Early morning (5am - 7am)
  if (hour >= 5 && hour < 7) {
    const messages = [
      "Early riser! Fresh mind, focused study.",
      "Up early and getting after it.",
    ];
    return pick(messages);
  }

  return null; // No special acknowledgment for normal hours
}

// ============================================
// RETURN VISITOR MESSAGES
// When user comes back after absence
// ============================================
export function getReturnMessage(daysAway: number): string | null {
  if (daysAway <= 1) return null;

  if (daysAway <= 3) {
    return "Welcome back! Ready to pick up where you left off?";
  }
  if (daysAway <= 7) {
    return "Good to see you again! Let's get back into it.";
  }
  if (daysAway <= 30) {
    return "Welcome back! No worries about the break - just start where you are.";
  }
  return "It's been a while! Great to have you back. Fresh start, let's go.";
}

// ============================================
// AI CHAT ENCOURAGEMENT
// ============================================
export const aiChatMessages = {
  placeholder: "Ask anything about this question - I'm here to help.",
  afterResponse: "Does that help? Feel free to ask more.",
  encourageAsking: "Confused about something? That's what I'm here for.",
};

// ============================================
// QUESTION RATING MESSAGES
// ============================================
export const questionRatingMessages = {
  goodQuestion: {
    title: "Glad this one helped!",
    prompt: "What made it useful?",
  },
  badQuestion: {
    title: "Thanks for the feedback",
    prompt: "What could be better?",
  },
  submitted: "Thanks! Your feedback helps improve ShelfSense.",
};
