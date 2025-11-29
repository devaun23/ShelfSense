// Warm, empathetic messages for medical students
// Focus: warmth and understanding, NOT motivation

export const LOADING_MESSAGES = [
  "Taking a moment to find the right question for you.",
  "We're here with you.",
  "No rush. Take your time.",
  "Finding something that fits where you are.",
  "One step at a time.",
];

// Personalized loading messages (use with user's name)
export const LOADING_MESSAGES_PERSONAL = [
  (name: string) => `${name}, we're getting things ready for you.`,
  (name: string) => `One moment, ${name}.`,
  (name: string) => `Finding the right question for you, ${name}.`,
];

export const CORRECT_ANSWER_MESSAGES = [
  "That's right. Here's why.",
  "You've got it. Let's build on that.",
  "Correct. Here's the full picture.",
];

export const CORRECT_ANSWER_MESSAGES_PERSONAL = [
  (name: string) => `That's right, ${name}. Here's why.`,
  (name: string) => `You've got it, ${name}. Let's build on that.`,
];

export const INCORRECT_ANSWER_MESSAGES = [
  "Let's look at this together.",
  "Here's what happened.",
  "This is part of learning. Let's understand it.",
  "No worries. Let's work through it.",
];

export const INCORRECT_ANSWER_MESSAGES_PERSONAL = [
  (name: string) => `Let's look at this together, ${name}.`,
  (name: string) => `No worries, ${name}. Here's what happened.`,
];

// Gentle acknowledgment, not celebration
export const STREAK_MESSAGES: Record<number, string> = {
  3: "Three in a row. You're finding your footing.",
  5: "Five. Steady progress.",
  10: "Ten. You're in a good rhythm.",
  15: "Fifteen. Take a breath when you need one.",
  20: "Twenty. Remember to rest.",
};

export const SESSION_START_MESSAGES = [
  "Ready when you are.",
  "Take your time.",
  "No pressure. Start when you're ready.",
];

export const SESSION_START_MESSAGES_PERSONAL = [
  (name: string) => `Ready when you are, ${name}.`,
  (name: string) => `Take your time, ${name}.`,
];

export const SESSION_END_MESSAGES = [
  "You showed up. That matters.",
  "Rest well.",
  "See you when you're ready.",
];

export const SESSION_END_MESSAGES_PERSONAL = [
  (name: string) => `You showed up today, ${name}. That matters.`,
  (name: string) => `Rest well, ${name}. See you when you're ready.`,
];

export const BREAK_REMINDER_MESSAGE =
  "You've been studying for a while. A short break can help.";

export const BREAK_REMINDER_MESSAGE_PERSONAL = (name: string) =>
  `${name}, you've been studying for a while. A short break can help.`;

// Utility functions
export const getRandomEncouragement = () =>
  LOADING_MESSAGES[Math.floor(Math.random() * LOADING_MESSAGES.length)];

export const getRandomEncouragementPersonal = (name: string) => {
  // 30% chance to use personalized message
  if (Math.random() < 0.3 && name) {
    const personalMsg = LOADING_MESSAGES_PERSONAL[Math.floor(Math.random() * LOADING_MESSAGES_PERSONAL.length)];
    return personalMsg(name);
  }
  return getRandomEncouragement();
};

export const getRandomCorrectMessage = () =>
  CORRECT_ANSWER_MESSAGES[Math.floor(Math.random() * CORRECT_ANSWER_MESSAGES.length)];

export const getRandomCorrectMessagePersonal = (name: string) => {
  if (Math.random() < 0.3 && name) {
    const personalMsg = CORRECT_ANSWER_MESSAGES_PERSONAL[Math.floor(Math.random() * CORRECT_ANSWER_MESSAGES_PERSONAL.length)];
    return personalMsg(name);
  }
  return getRandomCorrectMessage();
};

export const getRandomIncorrectMessage = () =>
  INCORRECT_ANSWER_MESSAGES[Math.floor(Math.random() * INCORRECT_ANSWER_MESSAGES.length)];

export const getRandomIncorrectMessagePersonal = (name: string) => {
  if (Math.random() < 0.3 && name) {
    const personalMsg = INCORRECT_ANSWER_MESSAGES_PERSONAL[Math.floor(Math.random() * INCORRECT_ANSWER_MESSAGES_PERSONAL.length)];
    return personalMsg(name);
  }
  return getRandomIncorrectMessage();
};

export const getStreakMessage = (streak: number): string | null => {
  return STREAK_MESSAGES[streak] || null;
};

export const getRandomSessionStartMessage = () =>
  SESSION_START_MESSAGES[Math.floor(Math.random() * SESSION_START_MESSAGES.length)];

export const getRandomSessionStartMessagePersonal = (name: string) => {
  if (Math.random() < 0.3 && name) {
    const personalMsg = SESSION_START_MESSAGES_PERSONAL[Math.floor(Math.random() * SESSION_START_MESSAGES_PERSONAL.length)];
    return personalMsg(name);
  }
  return getRandomSessionStartMessage();
};

export const getRandomSessionEndMessage = () =>
  SESSION_END_MESSAGES[Math.floor(Math.random() * SESSION_END_MESSAGES.length)];

export const getRandomSessionEndMessagePersonal = (name: string) => {
  if (Math.random() < 0.3 && name) {
    const personalMsg = SESSION_END_MESSAGES_PERSONAL[Math.floor(Math.random() * SESSION_END_MESSAGES_PERSONAL.length)];
    return personalMsg(name);
  }
  return getRandomSessionEndMessage();
};
