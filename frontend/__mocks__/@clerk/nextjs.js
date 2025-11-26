// Mock for @clerk/nextjs
const React = require('react')

const mockUser = {
  id: 'user_test123',
  firstName: 'Test',
  lastName: 'User',
  fullName: 'Test User',
  emailAddresses: [{ emailAddress: 'test@example.com' }],
  primaryEmailAddress: { emailAddress: 'test@example.com' },
  imageUrl: 'https://example.com/avatar.png',
}

const mockSession = {
  id: 'session_test123',
  status: 'active',
}

const useUser = jest.fn(() => ({
  isLoaded: true,
  isSignedIn: true,
  user: mockUser,
}))

const useAuth = jest.fn(() => ({
  isLoaded: true,
  isSignedIn: true,
  userId: 'user_test123',
  sessionId: 'session_test123',
  getToken: jest.fn(() => Promise.resolve('mock-token')),
  signOut: jest.fn(),
}))

const useSession = jest.fn(() => ({
  isLoaded: true,
  isSignedIn: true,
  session: mockSession,
}))

const useClerk = jest.fn(() => ({
  signOut: jest.fn(),
  openSignIn: jest.fn(),
  openSignUp: jest.fn(),
}))

const ClerkProvider = ({ children }) => React.createElement(React.Fragment, null, children)

const SignedIn = ({ children }) => React.createElement(React.Fragment, null, children)

const SignedOut = ({ children }) => null

const SignIn = () => React.createElement('div', { 'data-testid': 'clerk-sign-in' }, 'Sign In')

const SignUp = () => React.createElement('div', { 'data-testid': 'clerk-sign-up' }, 'Sign Up')

const UserButton = () => React.createElement('button', { 'data-testid': 'clerk-user-button' }, 'User')

const SignInButton = ({ children }) => React.createElement('button', { 'data-testid': 'clerk-sign-in-button' }, children || 'Sign In')

const SignUpButton = ({ children }) => React.createElement('button', { 'data-testid': 'clerk-sign-up-button' }, children || 'Sign Up')

const SignOutButton = ({ children }) => React.createElement('button', { 'data-testid': 'clerk-sign-out-button' }, children || 'Sign Out')

// Server-side exports
const auth = jest.fn(() => ({
  userId: 'user_test123',
  sessionId: 'session_test123',
  getToken: jest.fn(() => Promise.resolve('mock-token')),
}))

const currentUser = jest.fn(() => Promise.resolve(mockUser))

module.exports = {
  useUser,
  useAuth,
  useSession,
  useClerk,
  ClerkProvider,
  SignedIn,
  SignedOut,
  SignIn,
  SignUp,
  UserButton,
  SignInButton,
  SignUpButton,
  SignOutButton,
  auth,
  currentUser,
}
