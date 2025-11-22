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
    <div className="border border-gray-700 rounded-lg bg-black/50 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-900/50 transition-colors group"
      >
        <div className="flex items-center gap-3">
          {/* Star Icon with Eyes */}
          <div className="relative" style={{ width: '32px', height: '32px' }}>
            {/* 8-pointed Star SVG */}
            <svg
              width="32"
              height="32"
              viewBox="0 0 32 32"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="absolute inset-0"
            >
              {/* Star shape */}
              <path
                d="M16 2 L18.5 13.5 L30 16 L18.5 18.5 L16 30 L13.5 18.5 L2 16 L13.5 13.5 Z"
                stroke="white"
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>

            {/* Animated Eyes */}
            <div className="absolute inset-0 flex items-center justify-center" style={{ paddingTop: '1px' }}>
              <div className="flex gap-2">
                {/* Left Eye */}
                <div
                  className="bg-white rounded-full transition-all duration-300 ease-out"
                  style={{
                    width: '4px',
                    height: '4px',
                    transform: isHovering ? 'translateX(2px)' : 'translateX(0)',
                  }}
                />
                {/* Right Eye */}
                <div
                  className="bg-white rounded-full transition-all duration-300 ease-out"
                  style={{
                    width: '4px',
                    height: '4px',
                    transform: isHovering ? 'translateX(2px)' : 'translateX(0)',
                  }}
                />
              </div>
            </div>
          </div>

          <span className="text-sm font-semibold text-white transition-all duration-300">
            {isHovering ? "Let's chat!" : 'Ask AI About This Question'}
          </span>
        </div>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Chat Interface */}
      {isExpanded && (
        <div className="border-t border-gray-700">
          {/* Messages */}
          <div className="max-h-32 overflow-y-auto p-3 space-y-2">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 text-sm py-8">
                Ask me anything about this question!<br />
                <span className="text-xs text-gray-600 mt-1">
                  (e.g., "Why is this the correct answer?", "Can you explain the pathophysiology?")
                </span>
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
                      ? 'bg-[#1E3A5F] text-white'
                      : 'bg-gray-800 text-gray-100'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-800 px-4 py-2 rounded-lg">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-gray-700">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your question..."
                disabled={loading}
                className="flex-1 px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#1E3A5F] disabled:opacity-50"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                className="px-4 py-2 bg-[#1E3A5F] hover:bg-[#2C5282] disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
