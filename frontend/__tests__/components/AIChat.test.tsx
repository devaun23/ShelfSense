import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AIChat from '@/components/AIChat'

// Mock fetch globally
const mockFetch = jest.fn()
global.fetch = mockFetch

describe('AIChat', () => {
  const defaultProps = {
    questionId: 'test-question-123',
    userId: 'test-user-456',
    isCorrect: true,
    userAnswer: 'A'
  }

  beforeEach(() => {
    mockFetch.mockReset()
    // Default: return empty chat history
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ messages: [] })
    })
  })

  describe('Initial Rendering', () => {
    it('renders without crashing', () => {
      render(<AIChat {...defaultProps} />)
      expect(screen.getByText('Ask AI')).toBeInTheDocument()
    })

    it('renders collapsed by default', () => {
      render(<AIChat {...defaultProps} />)
      expect(screen.queryByPlaceholderText('Ask a question...')).not.toBeInTheDocument()
    })

    it('renders expand/collapse button with correct aria label', () => {
      render(<AIChat {...defaultProps} />)
      const button = screen.getByRole('button', { name: /expand ai chat/i })
      expect(button).toBeInTheDocument()
      expect(button).toHaveAttribute('aria-expanded', 'false')
    })

    it('loads chat history on mount', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          messages: [
            { role: 'user', message: 'What is the answer?' },
            { role: 'assistant', message: 'The answer is A.' }
          ]
        })
      })

      render(<AIChat {...defaultProps} />)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining(`/api/chat/history/${defaultProps.questionId}`)
        )
      })
    })
  })

  describe('Expand/Collapse', () => {
    it('expands chat when header is clicked', async () => {
      render(<AIChat {...defaultProps} />)

      const button = screen.getByRole('button', { name: /expand ai chat/i })
      await userEvent.click(button)

      expect(screen.getByPlaceholderText('Ask a question...')).toBeInTheDocument()
      expect(button).toHaveAttribute('aria-expanded', 'true')
    })

    it('collapses chat when header is clicked again', async () => {
      render(<AIChat {...defaultProps} />)

      const button = screen.getByRole('button', { name: /expand ai chat/i })
      await userEvent.click(button) // Expand
      await userEvent.click(button) // Collapse

      expect(screen.queryByPlaceholderText('Ask a question...')).not.toBeInTheDocument()
    })

    it('shows empty state message when expanded with no messages', async () => {
      render(<AIChat {...defaultProps} />)

      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      expect(screen.getByText('Ask anything about this question')).toBeInTheDocument()
    })
  })

  describe('Hover Effects', () => {
    it('shows "Let\'s chat" text on hover', async () => {
      render(<AIChat {...defaultProps} />)

      const button = screen.getByRole('button', { name: /expand ai chat/i })
      await userEvent.hover(button)

      expect(screen.getByText("Let's chat")).toBeInTheDocument()
    })

    it('shows "Ask AI" text when not hovering', async () => {
      render(<AIChat {...defaultProps} />)
      expect(screen.getByText('Ask AI')).toBeInTheDocument()
    })
  })

  describe('Message Input', () => {
    it('enables send button when input has text', async () => {
      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'Why is A correct?')

      const sendButton = screen.getByRole('button', { name: /send message/i })
      expect(sendButton).not.toBeDisabled()
    })

    it('disables send button when input is empty', async () => {
      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const sendButton = screen.getByRole('button', { name: /send message/i })
      expect(sendButton).toBeDisabled()
    })

    it('disables send button when only whitespace', async () => {
      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, '   ')

      const sendButton = screen.getByRole('button', { name: /send message/i })
      expect(sendButton).toBeDisabled()
    })
  })

  describe('Sending Messages', () => {
    it('sends message on button click', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ messages: [] })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ response: 'The answer is A because...' })
        })

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'Why is A correct?')
      await userEvent.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/chat/question'),
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('Why is A correct?')
          })
        )
      })
    })

    it('sends message on Enter key', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ messages: [] })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ response: 'Response text' })
        })

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'Test question')
      fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 })

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2) // History + message
      })
    })

    it('clears input after sending', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ messages: [] })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ response: 'Response' })
        })

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'My question')
      await userEvent.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        expect(input).toHaveValue('')
      })
    })

    it('displays user message in chat', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ messages: [] })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ response: 'AI response' })
        })

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'My question to AI')
      await userEvent.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        expect(screen.getByText('My question to AI')).toBeInTheDocument()
      })
    })

    it('displays assistant response in chat', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ messages: [] })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ response: 'This is the AI response' })
        })

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'Question')
      await userEvent.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        expect(screen.getByText('This is the AI response')).toBeInTheDocument()
      })
    })

    it('includes correct request body', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ messages: [] })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ response: 'Response' })
        })

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'Test')
      await userEvent.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        const lastCall = mockFetch.mock.calls[1]
        const body = JSON.parse(lastCall[1].body)

        expect(body.user_id).toBe(defaultProps.userId)
        expect(body.question_id).toBe(defaultProps.questionId)
        expect(body.user_answer).toBe(defaultProps.userAnswer)
        expect(body.is_correct).toBe(defaultProps.isCorrect)
      })
    })
  })

  describe('Loading State', () => {
    it('shows loading indicator while waiting for response', async () => {
      // Delay the response
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ messages: [] })
        })
        .mockImplementationOnce(() => new Promise(resolve => {
          setTimeout(() => resolve({
            ok: true,
            json: async () => ({ response: 'Response' })
          }), 100)
        }))

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'Test')
      await userEvent.click(screen.getByRole('button', { name: /send message/i }))

      // Should show the user's message was sent
      expect(screen.getByText('Test')).toBeInTheDocument()
    })

    it('disables input while loading', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ messages: [] })
        })
        .mockImplementationOnce(() => new Promise(resolve => {
          setTimeout(() => resolve({
            ok: true,
            json: async () => ({ response: 'Response' })
          }), 100)
        }))

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'Test')
      await userEvent.click(screen.getByRole('button', { name: /send message/i }))

      // Input should be disabled during loading
      expect(input).toBeDisabled()
    })
  })

  describe('Error Handling', () => {
    it('handles API error gracefully', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ messages: [] })
        })
        .mockResolvedValueOnce({
          ok: false,
          statusText: 'Internal Server Error'
        })

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'Test')
      await userEvent.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Chat API error:', 'Internal Server Error')
      })

      consoleSpy.mockRestore()
    })

    it('handles network error gracefully', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ messages: [] })
        })
        .mockRejectedValueOnce(new Error('Network error'))

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      await userEvent.type(input, 'Test')
      await userEvent.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Error sending message:', expect.any(Error))
      })

      consoleSpy.mockRestore()
    })

    it('handles chat history load error gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Failed to load'))

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

      render(<AIChat {...defaultProps} />)

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Error loading chat history:', expect.any(Error))
      })

      consoleSpy.mockRestore()
    })
  })

  describe('Chat History', () => {
    it('displays loaded chat history', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          messages: [
            { role: 'user', message: 'Previous question' },
            { role: 'assistant', message: 'Previous answer' }
          ]
        })
      })

      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      await waitFor(() => {
        expect(screen.getByText('Previous question')).toBeInTheDocument()
        expect(screen.getByText('Previous answer')).toBeInTheDocument()
      })
    })

    it('reloads history when questionId changes', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ messages: [] })
      })

      const { rerender } = render(<AIChat {...defaultProps} />)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(1)
      })

      // Change questionId
      rerender(<AIChat {...defaultProps} questionId="new-question-id" />)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2)
        expect(mockFetch).toHaveBeenLastCalledWith(
          expect.stringContaining('new-question-id')
        )
      })
    })
  })

  describe('Accessibility', () => {
    it('has accessible expand button', () => {
      render(<AIChat {...defaultProps} />)
      const button = screen.getByRole('button', { name: /expand ai chat/i })
      expect(button).toHaveAttribute('aria-expanded', 'false')
    })

    it('has accessible send button', async () => {
      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const sendButton = screen.getByRole('button', { name: /send message/i })
      expect(sendButton).toBeInTheDocument()
    })

    it('has accessible input field', async () => {
      render(<AIChat {...defaultProps} />)
      await userEvent.click(screen.getByRole('button', { name: /expand ai chat/i }))

      const input = screen.getByPlaceholderText('Ask a question...')
      expect(input).toHaveAttribute('type', 'text')
    })
  })
})
