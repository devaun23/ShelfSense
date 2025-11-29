import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Sidebar from '@/components/Sidebar'

// Mock Next.js router
const mockPush = jest.fn()
const mockPathname = jest.fn(() => '/study')
const mockSearchParams = { get: jest.fn((): string | null => null) }

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  usePathname: () => mockPathname(),
  useSearchParams: () => mockSearchParams,
}))

// Mock UserContext
const mockLogout = jest.fn()
const mockUser = {
  userId: 'test-user-123',
  fullName: 'John Doe',
  firstName: 'John',
  email: 'john@test.com',
}

jest.mock('@/contexts/UserContext', () => ({
  useUser: () => ({
    user: mockUser,
    logout: mockLogout,
  }),
}))

// Mock fetch
const mockFetch = jest.fn()
global.fetch = mockFetch

describe('Sidebar', () => {
  const defaultProps = {
    isOpen: true,
    onToggle: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ sessions: [] }),
    })
  })

  describe('Initial Rendering', () => {
    it('renders without crashing', () => {
      render(<Sidebar {...defaultProps} />)
      expect(screen.getByText('ShelfSense')).toBeInTheDocument()
    })

    it('displays Clerk UserButton', () => {
      render(<Sidebar {...defaultProps} />)
      // Clerk UserButton is mocked and rendered
      expect(screen.getByTestId('clerk-user-button')).toBeInTheDocument()
    })

    it('displays all shelf exam buttons', () => {
      render(<Sidebar {...defaultProps} />)

      expect(screen.getByText('Internal Medicine')).toBeInTheDocument()
      expect(screen.getByText('Surgery')).toBeInTheDocument()
      expect(screen.getByText('Pediatrics')).toBeInTheDocument()
      expect(screen.getByText('Psychiatry')).toBeInTheDocument()
      expect(screen.getByText('OBGYN')).toBeInTheDocument()
      expect(screen.getByText('Family Medicine')).toBeInTheDocument()
      expect(screen.getByText('Emergency')).toBeInTheDocument()
      expect(screen.getByText('Neurology')).toBeInTheDocument()
    })

    it('displays Step 2 CK all topics button', () => {
      render(<Sidebar {...defaultProps} />)
      expect(screen.getByText('Step 2 CK (All Topics)')).toBeInTheDocument()
    })

    it('displays navigation links', () => {
      render(<Sidebar {...defaultProps} />)
      expect(screen.getByText('Analytics')).toBeInTheDocument()
      expect(screen.getByText('Reviews')).toBeInTheDocument()
    })
  })

  describe('Open/Close State', () => {
    it('shows content when open', () => {
      render(<Sidebar {...defaultProps} isOpen={true} />)
      expect(screen.getByText('ShelfSense')).toBeVisible()
    })

    it('renders toggle button with correct aria-label when open', () => {
      render(<Sidebar {...defaultProps} isOpen={true} />)
      expect(screen.getByRole('button', { name: /close sidebar/i })).toBeInTheDocument()
    })

    it('renders toggle button with correct aria-label when closed', () => {
      render(<Sidebar {...defaultProps} isOpen={false} />)
      expect(screen.getByRole('button', { name: /open sidebar/i })).toBeInTheDocument()
    })

    it('calls onToggle when toggle button is clicked', async () => {
      const onToggle = jest.fn()
      render(<Sidebar {...defaultProps} onToggle={onToggle} />)

      await userEvent.click(screen.getByRole('button', { name: /close sidebar/i }))
      expect(onToggle).toHaveBeenCalledTimes(1)
    })

    it('calls onToggle when mobile overlay is clicked', async () => {
      const onToggle = jest.fn()
      const { container } = render(<Sidebar isOpen={true} onToggle={onToggle} />)

      // Find overlay by class
      const overlay = container.querySelector('.bg-black\\/60')
      if (overlay) {
        fireEvent.click(overlay)
        expect(onToggle).toHaveBeenCalledTimes(1)
      }
    })
  })

  describe('Specialty Navigation', () => {
    it('navigates to specialty when shelf exam button is clicked', async () => {
      render(<Sidebar {...defaultProps} />)

      await userEvent.click(screen.getByText('Internal Medicine'))

      expect(mockPush).toHaveBeenCalledWith('/study?specialty=Internal%20Medicine')
    })

    it('navigates to all topics when Step 2 CK button is clicked', async () => {
      render(<Sidebar {...defaultProps} />)

      await userEvent.click(screen.getByText('Step 2 CK (All Topics)'))

      expect(mockPush).toHaveBeenCalledWith('/study')
    })

    it('highlights current specialty', () => {
      mockSearchParams.get = jest.fn(() => 'Internal Medicine')

      render(<Sidebar {...defaultProps} />)

      const imButton = screen.getByText('Internal Medicine')
      expect(imButton).toHaveClass('bg-gray-800')
    })

    it('navigates to analytics', async () => {
      render(<Sidebar {...defaultProps} />)

      await userEvent.click(screen.getByText('Analytics'))

      expect(mockPush).toHaveBeenCalledWith('/analytics')
    })

    it('navigates to reviews', async () => {
      render(<Sidebar {...defaultProps} />)

      await userEvent.click(screen.getByText('Reviews'))

      expect(mockPush).toHaveBeenCalledWith('/reviews')
    })
  })

  describe('Logo Navigation', () => {
    it('navigates to home when logo is clicked', async () => {
      render(<Sidebar {...defaultProps} />)

      await userEvent.click(screen.getByText('ShelfSense'))

      expect(mockPush).toHaveBeenCalledWith('/')
    })
  })

  describe('User Settings', () => {
    it('renders Clerk UserButton for auth management', () => {
      render(<Sidebar {...defaultProps} />)
      // Clerk UserButton is rendered (handles sign out etc.)
      expect(screen.getByTestId('clerk-user-button')).toBeInTheDocument()
    })
  })

  describe('Session History', () => {
    it('loads session history on mount', async () => {
      render(<Sidebar {...defaultProps} />)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/analytics/sessions')
        )
      })
    })

    it('displays empty state when no sessions', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ sessions: [] }),
      })

      render(<Sidebar {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('No study sessions yet')).toBeInTheDocument()
        expect(screen.getByText('Start studying to see your history')).toBeInTheDocument()
      })
    })

    it('displays session history grouped by date', async () => {
      const today = new Date().toISOString()
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          sessions: [
            {
              id: 'session-1',
              date: today,
              questionsAnswered: 20,
              correctCount: 15,
              topic: 'Cardiology',
            },
          ],
        }),
      })

      render(<Sidebar {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('Today')).toBeInTheDocument()
        expect(screen.getByText('Cardiology')).toBeInTheDocument()
        expect(screen.getByText('75%')).toBeInTheDocument()
      })
    })

    it('displays session count when no topic', async () => {
      const today = new Date().toISOString()
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          sessions: [
            {
              id: 'session-1',
              date: today,
              questionsAnswered: 25,
              correctCount: 20,
              // No topic
            },
          ],
        }),
      })

      render(<Sidebar {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('25 questions')).toBeInTheDocument()
      })
    })

    it('handles session load error gracefully', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'))

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

      render(<Sidebar {...defaultProps} />)

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Error loading sessions:', expect.any(Error))
      })

      consoleSpy.mockRestore()
    })
  })


  describe('Active State Highlighting', () => {
    it('highlights analytics link when on analytics page', () => {
      mockPathname.mockReturnValue('/analytics')

      render(<Sidebar {...defaultProps} />)

      const analyticsButton = screen.getByText('Analytics').closest('button')
      expect(analyticsButton).toHaveClass('bg-gray-900')
    })

    it('highlights reviews link when on reviews page', () => {
      mockPathname.mockReturnValue('/reviews')

      render(<Sidebar {...defaultProps} />)

      const reviewsButton = screen.getByText('Reviews').closest('button')
      expect(reviewsButton).toHaveClass('bg-gray-900')
    })

    it('highlights Step 2 CK when on study page without specialty', () => {
      mockPathname.mockReturnValue('/study')
      mockSearchParams.get = jest.fn(() => null)

      render(<Sidebar {...defaultProps} />)

      const step2Button = screen.getByText('Step 2 CK (All Topics)')
      expect(step2Button).toHaveClass('bg-gray-800')
    })
  })

  describe('Accessibility', () => {
    it('has accessible toggle button', () => {
      render(<Sidebar {...defaultProps} />)
      const toggleButton = screen.getByRole('button', { name: /close sidebar/i })
      expect(toggleButton).toBeInTheDocument()
    })

    it('all buttons are focusable', () => {
      render(<Sidebar {...defaultProps} />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach(button => {
        expect(button).not.toHaveAttribute('tabIndex', '-1')
      })
    })
  })
})
