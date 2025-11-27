'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

interface AIChatProps {
  questionId: string;
  userId: string;
  isCorrect: boolean;
  userAnswer: string;
}

export default function AIChat({ questionId, userId, isCorrect, userAnswer }: AIChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [slowResponse, setSlowResponse] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const slowResponseTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Ref for stable sendMessage callback
  const inputValueRef = useRef(input);
  inputValueRef.current = input;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Focus input when expanded
  useEffect(() => {
    if (isExpanded && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isExpanded]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      if (slowResponseTimeoutRef.current) {
        clearTimeout(slowResponseTimeoutRef.current);
      }
    };
  }, []);

  // Load chat history when component mounts or question changes
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/chat/history/${questionId}?user_id=${userId}`);
        if (response.ok) {
          const data = await response.json();
          const loadedMessages: Message[] = data.messages.map((msg: { role: string; message: string }) => ({
            role: msg.role as 'user' | 'assistant',
            content: msg.message
          }));
          setMessages(loadedMessages);
        }
      } catch (err) {
        console.error('Error loading chat history:', err);
      }
    };

    loadChatHistory();
  }, [questionId, userId]);

  const cancelRequest = useCallback(() => {
    abortControllerRef.current?.abort();
    if (slowResponseTimeoutRef.current) {
      clearTimeout(slowResponseTimeoutRef.current);
    }
    setLoading(false);
    setSlowResponse(false);
  }, []);

  const sendMessage = useCallback(async () => {
    const currentInput = inputValueRef.current;
    if (!currentInput.trim() || loading) return;

    // Cancel any existing request
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    const userMessage: Message = { role: 'user', content: currentInput };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);
    setSlowResponse(false);

    // Show "Still thinking..." after 10 seconds
    slowResponseTimeoutRef.current = setTimeout(() => {
      setSlowResponse(true);
    }, 10000);

    // Add placeholder for streaming response
    const streamingMessage: Message = { role: 'assistant', content: '', isStreaming: true };
    setMessages(prev => [...prev, streamingMessage]);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/chat/question/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          question_id: questionId,
          message: currentInput,
          user_answer: userAnswer,
          is_correct: isCorrect,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.error) {
                setError(data.error);
                // Remove the streaming message on error
                setMessages(prev => prev.filter(m => !m.isStreaming));
                break;
              }

              if (data.done) {
                // Mark streaming as complete
                setMessages(prev =>
                  prev.map(m =>
                    m.isStreaming ? { ...m, isStreaming: false } : m
                  )
                );
                break;
              }

              if (data.content) {
                accumulatedContent += data.content;
                // Update the streaming message
                setMessages(prev =>
                  prev.map(m =>
                    m.isStreaming ? { ...m, content: accumulatedContent } : m
                  )
                );
              }
            } catch {
              // Ignore JSON parse errors for incomplete chunks
            }
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Request was cancelled, remove streaming message
        setMessages(prev => prev.filter(m => !m.isStreaming));
      } else {
        setError('Connection error. Please try again.');
        // Remove the streaming message on error
        setMessages(prev => prev.filter(m => !m.isStreaming));
      }
    } finally {
      if (slowResponseTimeoutRef.current) {
        clearTimeout(slowResponseTimeoutRef.current);
      }
      setLoading(false);
      setSlowResponse(false);
    }
  }, [loading, userId, questionId, userAnswer, isCorrect]);

  const retryLastMessage = useCallback(() => {
    // Get the last user message
    const lastUserMessage = [...messages].reverse().find(m => m.role === 'user');
    if (lastUserMessage) {
      // Remove the last user message and any error state
      setMessages(prev => prev.slice(0, -1));
      setError(null);
      // Set input and send
      inputValueRef.current = lastUserMessage.content;
      setInput(lastUserMessage.content);
      // Small delay to ensure state is updated
      setTimeout(() => sendMessage(), 0);
    }
  }, [messages, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearError = () => setError(null);

  return (
    <div
      className="border border-gray-800 rounded-lg bg-black overflow-hidden"
      role="region"
      aria-label="AI Chat Assistant"
    >
      {/* Header with Star Character */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-950 transition-colors group"
        aria-label={isExpanded ? 'Collapse AI chat' : 'Expand AI chat'}
        aria-expanded={isExpanded}
        aria-controls="ai-chat-panel"
      >
        <div className="flex items-center gap-3">
          <div className="relative" style={{ width: '28px', height: '28px' }}>
            <svg
              width="28"
              height="28"
              viewBox="0 0 28 28"
              fill="none"
              className="absolute inset-0"
            >
              <path
                d="M14 2 L16 12 L26 14 L16 16 L14 26 L12 16 L2 14 L12 12 Z"
                stroke="#4169E1"
                strokeWidth="1.5"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex gap-1.5">
                <div
                  className="bg-white rounded-full transition-all duration-200"
                  style={{
                    width: '3px',
                    height: '3px',
                    transform: isHovering ? 'translateX(1px)' : 'translateX(0)',
                  }}
                />
                <div
                  className="bg-white rounded-full transition-all duration-200"
                  style={{
                    width: '3px',
                    height: '3px',
                    transform: isHovering ? 'translateX(1px)' : 'translateX(0)',
                  }}
                />
              </div>
            </div>
          </div>
          <span className="text-sm font-medium text-white">
            {isHovering ? "Let's chat" : 'Ask AI'}
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-600 motion-safe:transition-transform motion-safe:duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Chat Interface */}
      <div
        id="ai-chat-panel"
        className={`motion-safe:transition-all motion-safe:duration-200 ease-out overflow-hidden ${isExpanded ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'}`}
        ref={chatContainerRef}
      >
        <div className="border-t border-gray-800">
          {/* Messages */}
          <div
            className="max-h-96 overflow-y-auto p-4 space-y-3"
            role="log"
            aria-live="polite"
            aria-label="Chat messages"
          >
            {messages.length === 0 && (
              <div className="text-center text-gray-600 text-sm py-8">
                Ask anything about this question
              </div>
            )}
            {messages.map((msg, idx) => (
              <div
                key={`${msg.role}-${idx}-${msg.content.slice(0, 20)}`}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] px-4 py-2 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-[#4169E1] text-white'
                      : 'bg-gray-900 text-gray-300'
                  }`}
                  role="article"
                  aria-label={`${msg.role === 'user' ? 'You' : 'AI'}: ${msg.content}`}
                >
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                    {msg.isStreaming && (
                      <span className="inline-block w-2 h-4 bg-gray-500 ml-1 animate-pulse" />
                    )}
                  </p>
                </div>
              </div>
            ))}
            {loading && messages[messages.length - 1]?.content === '' && (
              <div className="flex justify-start" role="status" aria-label="AI is typing">
                <div className="bg-gray-900 px-4 py-2 rounded-lg">
                  <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-1.5 h-1.5 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-1.5 h-1.5 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Slow Response Warning */}
          {slowResponse && (
            <div className="mx-4 mb-2 px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-center justify-between" role="status">
              <span className="text-amber-400 text-sm">Still thinking... This is taking longer than usual.</span>
              <button
                onClick={cancelRequest}
                className="text-amber-400 hover:text-amber-300 px-2 py-1 text-sm border border-amber-400/50 rounded"
                aria-label="Cancel request"
              >
                Cancel
              </button>
            </div>
          )}

          {/* Error Message with Retry */}
          {error && (
            <div className="mx-4 mb-2 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg" role="alert">
              <div className="flex items-center justify-between">
                <span className="text-red-400 text-sm">{error}</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={retryLastMessage}
                    className="text-red-400 hover:text-red-300 px-2 py-1 text-sm border border-red-400/50 rounded flex items-center gap-1"
                    aria-label="Retry message"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Retry
                  </button>
                  <button
                    onClick={clearError}
                    className="text-red-400 hover:text-red-300 p-1"
                    aria-label="Dismiss error"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t border-gray-800">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question..."
                disabled={loading}
                className="flex-1 px-4 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:border-[#4169E1] focus:outline-none focus:ring-1 focus:ring-[#4169E1] disabled:opacity-40"
                aria-label="Type your message"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                className="px-4 py-2 bg-[#4169E1] hover:bg-[#5B7FE8] disabled:bg-gray-900 disabled:cursor-not-allowed text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[#4169E1] focus:ring-offset-2 focus:ring-offset-black"
                aria-label="Send message"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
