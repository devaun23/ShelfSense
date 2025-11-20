/**
 * Greeting Utility - Claude-style varied greetings
 * Generates personalized, time-based greetings with variation
 */

export interface GreetingOptions {
  firstName: string;
  hour?: number;
}

const morningGreetings = [
  (name: string) => `Good Morning, ${name}`,
  (name: string) => `Morning, ${name}`,
  (name: string) => `Rise and shine, ${name}`,
  (name: string) => `Hey ${name}, ready to start?`,
  (name: string) => `Let's get started, ${name}`,
  (name: string) => `Fresh start, ${name}`,
  (name: string) => `Early bird, ${name}?`,
  (name: string) => `Hello ${name}`,
  (name: string) => `Hey there, ${name}`,
  (name: string) => `Good to see you, ${name}`,
];

const afternoonGreetings = [
  (name: string) => `Good Afternoon, ${name}`,
  (name: string) => `Hey, ${name}`,
  (name: string) => `Welcome back, ${name}`,
  (name: string) => `Afternoon, ${name}`,
  (name: string) => `Hey you're back, ${name}`,
  (name: string) => `Hi ${name}`,
  (name: string) => `Hello ${name}`,
  (name: string) => `Good to see you, ${name}`,
  (name: string) => `Ready to continue, ${name}?`,
  (name: string) => `Let's keep going, ${name}`,
];

const eveningGreetings = [
  (name: string) => `Good Evening, ${name}`,
  (name: string) => `Evening, ${name}`,
  (name: string) => `Hey you're back, ${name}`,
  (name: string) => `Welcome back, ${name}`,
  (name: string) => `Still going strong, ${name}?`,
  (name: string) => `Hey ${name}`,
  (name: string) => `Hello ${name}`,
  (name: string) => `Evening study session, ${name}?`,
  (name: string) => `Ready for more, ${name}?`,
  (name: string) => `Let's finish strong, ${name}`,
];

const lateNightGreetings = [
  (name: string) => `Late night studying, ${name}?`,
  (name: string) => `Burning the midnight oil, ${name}?`,
  (name: string) => `Still at it, ${name}?`,
  (name: string) => `Night owl, ${name}?`,
  (name: string) => `Can't stop, won't stop, ${name}?`,
  (name: string) => `Dedicated, ${name}`,
  (name: string) => `One more question, ${name}?`,
  (name: string) => `Hey ${name}`,
  (name: string) => `Welcome back, ${name}`,
  (name: string) => `Pushing through, ${name}?`,
];

/**
 * Get a time-based period (morning, afternoon, evening, late night)
 */
function getTimePeriod(hour: number): 'morning' | 'afternoon' | 'evening' | 'lateNight' {
  if (hour >= 5 && hour < 12) return 'morning';
  if (hour >= 12 && hour < 17) return 'afternoon';
  if (hour >= 17 && hour < 22) return 'evening';
  return 'lateNight';
}

/**
 * Get greeting array for time period
 */
function getGreetingsForPeriod(period: 'morning' | 'afternoon' | 'evening' | 'lateNight') {
  switch (period) {
    case 'morning':
      return morningGreetings;
    case 'afternoon':
      return afternoonGreetings;
    case 'evening':
      return eveningGreetings;
    case 'lateNight':
      return lateNightGreetings;
  }
}

/**
 * Generate a varied, time-based greeting
 * @param options - firstName and optional hour (defaults to current hour)
 * @returns Personalized greeting string
 */
export function generateGreeting(options: GreetingOptions): string {
  const { firstName, hour = new Date().getHours() } = options;

  // Get appropriate greetings for time of day
  const period = getTimePeriod(hour);
  const greetingOptions = getGreetingsForPeriod(period);

  // Randomly select one greeting
  const randomIndex = Math.floor(Math.random() * greetingOptions.length);
  const greetingFunc = greetingOptions[randomIndex];

  return greetingFunc(firstName);
}

/**
 * Extract first name from full name
 * @param fullName - User's full name
 * @returns First name only
 */
export function extractFirstName(fullName: string): string {
  return fullName.trim().split(' ')[0];
}
