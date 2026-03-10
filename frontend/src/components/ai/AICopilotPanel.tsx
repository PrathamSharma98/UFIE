import React, { useState, useRef, useEffect, useCallback } from 'react';
import { MessageSquare, Send, Bot, User, Sparkles, X, Loader2, Cpu, Brain, Zap } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { queryAI } from '../../services/api';
import type { AIResponse } from '../../types';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  suggestions?: string[];
  timestamp: Date;
  error?: boolean;
}

type AIMode = 'auto' | 'chatgpt' | 'gemini';

interface AICopilotPanelProps {
  isOpen: boolean;
  onToggle: () => void;
}

const WELCOME_MESSAGE: Message = {
  id: 'welcome',
  role: 'assistant',
  content:
    "Welcome to the **UFIE AI Copilot**. I can help you analyze flood risks, understand ward readiness scores, simulate rainfall scenarios, and provide infrastructure recommendations.\n\nTry asking me a question below.",
  suggestions: [
    'Which wards will flood if rainfall exceeds 60mm/hr?',
    'What infrastructure upgrades reduce risk the most?',
    'Generate a pre-monsoon preparedness report',
  ],
  timestamp: new Date(),
};

const modeConfig: Record<AIMode, { label: string; icon: React.ElementType; color: string }> = {
  auto: { label: 'Auto', icon: Zap, color: 'text-cyan-400' },
  chatgpt: { label: 'ChatGPT', icon: Brain, color: 'text-green-400' },
  gemini: { label: 'Gemini', icon: Cpu, color: 'text-purple-400' },
};

export default function AICopilotPanel({ isOpen, onToggle }: AICopilotPanelProps) {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [aiMode, setAiMode] = useState<AIMode>('auto');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen]);

  const sendMessage = useCallback(
    async (text?: string) => {
      const query = (text || input).trim();
      if (!query || loading) return;

      const userMsg: Message = {
        id: `u-${Date.now()}`,
        role: 'user',
        content: query,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      setLoading(true);

      try {
        const response = await queryAI(query, undefined, aiMode);
        const aiMsg: Message = {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: response.response,
          sources: response.sources,
          suggestions: response.suggestions,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      } catch (err: any) {
        const errorMsg: Message = {
          id: `e-${Date.now()}`,
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date(),
          error: true,
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setLoading(false);
      }
    },
    [input, loading, aiMode]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const cycleMode = () => {
    const modes: AIMode[] = ['auto', 'chatgpt', 'gemini'];
    const idx = modes.indexOf(aiMode);
    setAiMode(modes[(idx + 1) % modes.length]);
  };

  const currentMode = modeConfig[aiMode];
  const ModeIcon = currentMode.icon;

  return (
    <div className="chat-widget">
      {/* Chat Window */}
      {isOpen && (
        <div className="chat-window mb-4">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-blue-600/20 to-purple-600/20 border-b border-slate-700/50">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center shadow-lg">
                <Bot size={16} className="text-white" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white leading-none">AI Copilot</h3>
                <p className="text-[10px] text-slate-400 mt-0.5">ChatGPT + Gemini</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              {/* Mode toggle */}
              <button
                onClick={cycleMode}
                className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold bg-slate-800/80 border border-slate-600/50 hover:bg-slate-700/80 transition-colors ${currentMode.color}`}
                title={`Mode: ${currentMode.label}`}
              >
                <ModeIcon size={11} />
                {currentMode.label}
              </button>
              <button
                onClick={onToggle}
                className="p-1.5 hover:bg-slate-700/60 rounded-lg text-slate-400 hover:text-white transition-colors"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 panel-scroll">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
              >
                {msg.role === 'assistant' && (
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${
                      msg.error
                        ? 'bg-red-500/20 border border-red-500/40'
                        : 'bg-gradient-to-br from-blue-500 to-purple-500'
                    }`}
                  >
                    <Sparkles size={11} className="text-white" />
                  </div>
                )}

                <div
                  className={`max-w-[82%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-tr-sm'
                      : msg.error
                      ? 'bg-red-950/40 text-red-300 rounded-tl-sm border border-red-800/30'
                      : 'bg-slate-800/80 text-slate-200 rounded-tl-sm border border-slate-700/40'
                  }`}
                >
                  {msg.role === 'assistant' ? (
                    <div className="prose prose-invert prose-sm max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_p]:my-1.5 [&_li]:my-0.5 [&_ul]:my-1 [&_ol]:my-1 [&_h1]:text-base [&_h2]:text-sm [&_h3]:text-sm [&_table]:text-[11px] [&_th]:px-2 [&_td]:px-2 [&_strong]:text-blue-300 [&_code]:text-cyan-300 [&_code]:bg-slate-900/60 [&_code]:px-1 [&_code]:rounded">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p>{msg.content}</p>
                  )}

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-1.5 border-t border-slate-700/30">
                      <p className="text-[10px] text-slate-500">
                        Source: {msg.sources.join(', ')}
                      </p>
                    </div>
                  )}

                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="mt-2.5 space-y-1">
                      {msg.suggestions.map((s, j) => (
                        <button
                          key={j}
                          onClick={() => sendMessage(s)}
                          disabled={loading}
                          className="block w-full text-left text-[11px] px-2.5 py-1.5 bg-slate-700/40 hover:bg-slate-600/50 rounded-lg text-blue-300 hover:text-blue-200 transition-colors disabled:opacity-40"
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="w-6 h-6 rounded-full bg-slate-600 flex items-center justify-center flex-shrink-0 mt-1">
                    <User size={11} className="text-white" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-2 items-start animate-fade-in">
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center flex-shrink-0">
                  <Sparkles size={11} className="text-white" />
                </div>
                <div className="bg-slate-800/80 rounded-2xl rounded-tl-sm px-4 py-3 border border-slate-700/40">
                  <div className="flex items-center gap-1.5">
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:0ms]" />
                      <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:150ms]" />
                      <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:300ms]" />
                    </div>
                    <span className="text-[11px] text-slate-500 ml-1">Analyzing...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="px-3 py-2.5 border-t border-slate-700/40 bg-slate-900/60">
            <div className="flex items-center gap-2 bg-slate-800/80 rounded-xl px-3 py-0.5 border border-slate-700/40 focus-within:border-blue-500/50 transition-colors">
              <MessageSquare size={14} className="text-slate-500 flex-shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about flood risks, readiness..."
                className="flex-1 bg-transparent text-[13px] text-white placeholder-slate-500 outline-none py-2 min-w-0"
                disabled={loading}
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || loading}
                className="p-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-25 disabled:hover:bg-blue-600 text-white transition-colors flex-shrink-0"
              >
                <Send size={13} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Action Button */}
      <button
        onClick={onToggle}
        className={`chat-fab ${isOpen ? 'open' : ''}`}
        aria-label={isOpen ? 'Close AI Copilot' : 'Open AI Copilot'}
      >
        {isOpen ? <X size={22} /> : <Bot size={24} />}
      </button>
    </div>
  );
}
