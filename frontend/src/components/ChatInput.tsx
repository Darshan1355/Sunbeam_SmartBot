import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Square, Sparkles } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  onStop,
  isStreaming,
  disabled = false,
}) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming || disabled) return;
    onSend(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="p-4 bg-gradient-to-t from-slate-950 via-slate-950/95 to-transparent">
      <div className="max-w-3xl mx-auto">
        <form
          onSubmit={handleSubmit}
          className="relative flex items-end gap-2 bg-slate-900 border border-slate-800 rounded-2xl p-2 shadow-xl focus-within:border-orange-500/60 focus-within:ring-2 focus-within:ring-orange-500/20 transition-all"
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about Sunbeam courses, fees, batch schedules, internships..."
            disabled={disabled}
            className="w-full pl-3 pr-10 py-2 bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none max-h-44 leading-relaxed"
          />

          <div className="shrink-0 mb-1 mr-1">
            {isStreaming ? (
              <button
                type="button"
                onClick={onStop}
                title="Stop Generation"
                className="w-8 h-8 rounded-xl bg-slate-800 hover:bg-slate-700 text-rose-400 flex items-center justify-center transition-colors active:scale-95"
              >
                <Square className="w-4 h-4 fill-current" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim() || disabled}
                title="Send Message"
                className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all ${
                  input.trim() && !disabled
                    ? 'bg-orange-500 text-white hover:bg-orange-600 shadow-md shadow-orange-500/20 active:scale-95'
                    : 'bg-slate-800 text-slate-600 cursor-not-allowed'
                }`}
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            )}
          </div>
        </form>

        <p className="text-[11px] text-slate-500 text-center mt-2 flex items-center justify-center gap-1">
          <Sparkles className="w-3 h-3 text-orange-400" /> Grounded in official Sunbeam Institute records and ChromaDB.
        </p>
      </div>
    </div>
  );
};
