/**
 * Greeting Utility - Context-aware greetings
 * Generates personalized greetings based on visit count
 */

export interface GreetingOptions {
  firstName: string;
  hour?: number;
  visitsToday?: number;
}

const firstVisitGreetings = [
  () => `Let's keep going`,
  () => `Ready to begin?`,
  () => `Let's get started`,
  () => `Time to study`,
  () => `Let's do this`,
];

const returningVisitGreetings = [
  () => `Welcome back`,
  () => `Let's keep going`,
  () => `Ready for more?`,
  () => `Still going strong?`,
  () => `Let's continue`,
];

/**
 * Generate a context-aware greeting
 * @param options - firstName, hour, and visitsToday
 * @returns Personalized greeting string
 */
export function generateGreeting(options: GreetingOptions): string {
  const { visitsToday = 1 } = options;

  // First visit of the day: no "Welcome back"
  if (visitsToday === 1) {
    const randomIndex = Math.floor(Math.random() * firstVisitGreetings.length);
    return firstVisitGreetings[randomIndex]();
  }

  // Second or third+ visit: can show "Welcome back" or "Let's keep going"
  const randomIndex = Math.floor(Math.random() * returningVisitGreetings.length);
  return returningVisitGreetings[randomIndex]();
}

/**
 * Extract first name from full name
 * @param fullName - User's full name
 * @returns First name only
 */
export function extractFirstName(fullName: string): string {
  return fullName.trim().split(' ')[0];
}
