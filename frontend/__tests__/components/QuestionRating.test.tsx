import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import QuestionRating from '@/components/QuestionRating'

// Mock fetch
global.fetch = jest.fn()

describe('QuestionRating', () => {
  const mockProps = {
    questionId: 'test-question-123',
    userId: 'test-user-456',
    onRatingComplete: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    })
  })

  it('renders rating buttons', () => {
    render(<QuestionRating {...mockProps} />)

    // Check for thumbs up and down buttons (using aria-label)
    expect(screen.getByLabelText('Rate as good question')).toBeInTheDocument()
    expect(screen.getByLabelText('Report issue with question')).toBeInTheDocument()
  })

  it('opens modal when good question clicked', async () => {
    render(<QuestionRating {...mockProps} />)

    fireEvent.click(screen.getByLabelText('Rate as good question'))

    expect(screen.getByText('Good Question')).toBeInTheDocument()
    expect(screen.getByText('What made this question good?')).toBeInTheDocument()
  })

  it('opens modal when bad question clicked', async () => {
    render(<QuestionRating {...mockProps} />)

    fireEvent.click(screen.getByLabelText('Report issue with question'))

    expect(screen.getByText('Report Issue')).toBeInTheDocument()
    expect(screen.getByText('Help improve by explaining the issue')).toBeInTheDocument()
  })

  it('allows typing feedback', async () => {
    const user = userEvent.setup()
    render(<QuestionRating {...mockProps} />)

    fireEvent.click(screen.getByLabelText('Rate as good question'))

    const textarea = screen.getByPlaceholderText('Optional feedback...')
    await user.type(textarea, 'Great clinical scenario!')

    expect(textarea).toHaveValue('Great clinical scenario!')
  })

  it('submits rating with feedback', async () => {
    const user = userEvent.setup()
    render(<QuestionRating {...mockProps} />)

    fireEvent.click(screen.getByLabelText('Rate as good question'))

    const textarea = screen.getByPlaceholderText('Optional feedback...')
    await user.type(textarea, 'Great question!')

    fireEvent.click(screen.getByText('Submit'))

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/questions/rate'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('test-question-123'),
        })
      )
    })
  })

  it('calls onRatingComplete after successful submission', async () => {
    render(<QuestionRating {...mockProps} />)

    fireEvent.click(screen.getByLabelText('Rate as good question'))
    fireEvent.click(screen.getByText('Submit'))

    await waitFor(() => {
      expect(mockProps.onRatingComplete).toHaveBeenCalled()
    })
  })

  it('allows skipping feedback', async () => {
    render(<QuestionRating {...mockProps} />)

    fireEvent.click(screen.getByLabelText('Rate as good question'))
    fireEvent.click(screen.getByText('Skip'))

    expect(mockProps.onRatingComplete).toHaveBeenCalled()
    expect(screen.queryByText('Good Question')).not.toBeInTheDocument()
  })

  it('shows submitting state', async () => {
    // Make fetch take longer
    ;(global.fetch as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ ok: true }), 100))
    )

    render(<QuestionRating {...mockProps} />)

    fireEvent.click(screen.getByLabelText('Rate as good question'))
    fireEvent.click(screen.getByText('Submit'))

    expect(screen.getByText('Submitting...')).toBeInTheDocument()
  })

  it('handles API error gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
    ;(global.fetch as jest.Mock).mockRejectedValue(new Error('API Error'))

    render(<QuestionRating {...mockProps} />)

    fireEvent.click(screen.getByLabelText('Rate as good question'))
    fireEvent.click(screen.getByText('Submit'))

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })

    consoleSpy.mockRestore()
  })
})
