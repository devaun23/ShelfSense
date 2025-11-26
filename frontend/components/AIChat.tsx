'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load chat history when component mounts or question changes
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/chat/history/${questionId}?user_id=${userId}`);
        if (response.ok) {
          const data = await response.json();
          const loadedMessages: Message[] = data.messages.map((msg: any) => ({
            role: msg.role,
            content: msg.message
          }));
          setMessages(loadedMessages);
        }
      } catch (error) {
        console.error('Error loading chat history:', error);
      }
    };

    loadChatHistory();
  }, [questionId, userId]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/chat/question`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          question_id: questionId,
          message: input,
          user_answer: userAnswer,
          is_correct: isCorrect,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const assistantMessage: Message = { role: 'assistant', content: data.response };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        console.error('Chat API error:', response.statusText);
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="border border-gray-800 rounded-lg bg-black overflow-hidden">
      {/* Header with Star Character (Unique Visual Signature) */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-950 transition-colors group"
        aria-label={isExpanded ? 'Collapse AI chat' : 'Expand AI chat'}
        aria-expanded={isExpanded}
      >
        <div className="flex items-center gap-3">
          {/* Star Character with Eyes - Unique ShelfSense Signature */}
          <div className="relative" style={{ width: '28px', height: '28px' }}>
            <svg
              width="28"
              height="28"
              viewBox="0 0 28 28"
              fill="none"
              className="absolute inset-0"
            >
              {/* Minimal 8-pointed star */}
              <path
                d="M14 2 L16 12 L26 14 L16 16 L14 26 L12 16 L2 14 L12 12 Z"
                stroke="#4169E1"
                strokeWidth="1.5"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>

            {/* Subtle animated eyes */}
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
          className={`w-4 h-4 text-gray-600 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Minimal Chat Interface */}
      {isExpanded && (
        <div className="border-t border-gray-800">
          {/* Messages */}
          <div className="max-h-96 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-center text-gray-600 text-sm py-8">
                Ask anything about this question
              </div>
            )}
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] px-4 py-2 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-[#4169E1] text-white'
                      : 'bg-gray-900 text-gray-300'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
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

          {/* Input */}
          <div className="p-4 border-t border-gray-800">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question..."
                disabled={loading}
                className="flex-1 px-4 py-2 bg-gray-950 border border-gray-800 rounded-lg text-white placeholder-gray-600 focus:border-[#4169E1] disabled:opacity-40"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                className="px-4 py-2 bg-[#4169E1] hover:bg-[#5B7FE8] disabled:bg-gray-900 text-white rounded-lg transition-colors"
                aria-label="Send message"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
