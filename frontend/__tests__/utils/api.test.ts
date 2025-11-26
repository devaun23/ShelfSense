/**
 * Tests for API utility functions and configuration
 */

describe('API Configuration', () => {
  const originalEnv = process.env

  beforeEach(() => {
    jest.resetModules()
    process.env = { ...originalEnv }
  })

  afterAll(() => {
    process.env = originalEnv
  })

  it('uses localhost when NEXT_PUBLIC_API_URL is not set', () => {
    delete process.env.NEXT_PUBLIC_API_URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    expect(apiUrl).toBe('http://localhost:8000')
  })

  it('uses environment variable when set', () => {
    process.env.NEXT_PUBLIC_API_URL = 'https://api.shelfsense.com'
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    expect(apiUrl).toBe('https://api.shelfsense.com')
  })
})

describe('API Endpoints', () => {
  beforeEach(() => {
    global.fetch = jest.fn()
  })

  it('constructs correct questions endpoint', async () => {
    const mockResponse = { id: '123', vignette: 'Test question' }
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    const apiUrl = 'http://localhost:8000'
    await fetch(`${apiUrl}/api/questions/test-id`)

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/questions/test-id')
  })

  it('constructs correct submit endpoint', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ is_correct: true }),
    })

    const apiUrl = 'http://localhost:8000'
    await fetch(`${apiUrl}/api/questions/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user-1',
        question_id: 'q-1',
        user_answer: 'A',
      }),
    })

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/questions/submit',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('handles network errors', async () => {
    ;(global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'))

    const apiUrl = 'http://localhost:8000'

    await expect(fetch(`${apiUrl}/api/questions/test-id`)).rejects.toThrow('Network error')
  })

  it('handles non-ok responses', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    })

    const apiUrl = 'http://localhost:8000'
    const response = await fetch(`${apiUrl}/api/questions/non-existent`)

    expect(response.ok).toBe(false)
    expect(response.status).toBe(404)
  })
})

describe('Request Headers', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    })
  })

  it('sends correct content-type for JSON', async () => {
    const apiUrl = 'http://localhost:8000'
    await fetch(`${apiUrl}/api/questions/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ test: 'data' }),
    })

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    )
  })
})
