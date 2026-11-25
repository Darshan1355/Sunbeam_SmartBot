import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  User,
  Bot,
  Copy,
  Check,
  RotateCcw,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Cpu,
  Sparkles,
  ExternalLink,
  AlertTriangle
} from 'lucide-react';
import { Message } from '../types/chat';

interface MessageItemProps {
  message: Message;
  isStreaming?: boolean;
  onRegenerate?: () => void;
  onRetry?: () => void;
  onSelectFollowUp?: (text: string) => void;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  isStreaming = false,
  onRegenerate,
  onRetry,
  onSelectFollowUp,
}) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [showTools, setShowTools] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const copyText = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Extract clean follow-up questions if any
  const followUps = React.useMemo(() => {
    if (isUser || !message.content || isStreaming) return [];
    if (message.content.toLowerCase().includes('java')) {
      return ['What is the fee for Core Java?', 'What is the batch timing?', 'Compare Java and C++'];
    }
    if (message.content.toLowerCase().includes('internship')) {
      return ['What are the batch timings?', 'What is the fee for 1 month internship?', 'Is hostel accommodation available?'];
    }
    return ['What other courses are available?', 'Tell me about the Hinjawadi campus', 'How do I register?'];
  }, [message.content, isUser, isStreaming]);

  return (
    <div className={`py-6 px-4 md:px-6 flex gap-4 ${isUser ? 'bg-slate-950/40' : 'bg-slate-900/50 border-y border-slate-800/40'}`}>
      {/* Avatar */}
      <div className="shrink-0">
        {isUser ? (
          <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
            <User className="w-4 h-4" />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-orange-600 to-amber-500 flex items-center justify-center text-white shadow-md shadow-orange-500/20">
            <Bot className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Message Content */}
      <div className="flex-1 min-w-0 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-300">
            {isUser ? 'You' : 'Sunbeam SmartBot'}
          </span>
          <span className="text-[10px] text-slate-500 font-mono">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Live Tool Activity Badge / Panel */}
        {!isUser && message.tool_activity && message.tool_activity.length > 0 && (
          <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-2.5 text-xs">
            <button
              onClick={() => setShowTools(!showTools)}
              className="w-full flex items-center justify-between text-slate-400 hover:text-slate-200"
            >
              <div className="flex items-center gap-2">
                <Cpu className="w-3.5 h-3.5 text-orange-400 animate-spin" />
                <span className="font-semibold text-slate-300">
                  Agent Tool Execution ({message.tool_activity.length})
                </span>
              </div>
              {showTools ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showTools && (
              <div className="mt-2 pt-2 border-t border-slate-800/60 space-y-1.5 font-mono text-[11px]">
                {message.tool_activity.map((t, idx) => (
                  <div key={idx} className="flex items-center justify-between text-slate-400">
                    <span className="text-orange-400 font-medium">{t.tool}</span>
                    <span className="text-emerald-400">{t.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Text Body */}
        {message.status === 'error' ? (
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/50 text-rose-200 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span>{message.content}</span>
            </div>
            {onRetry && (
              <button
                onClick={onRetry}
                className="px-2.5 py-1 rounded bg-rose-900/60 hover:bg-rose-900 text-rose-100 font-medium text-xs flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" /> Retry
              </button>
            )}
          </div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none text-slate-200 leading-relaxed break-words">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>,
                table: ({ children }) => (
                  <div className="overflow-x-auto my-3 border border-slate-800 rounded-lg">
                    <table className="min-w-full divide-y divide-slate-800 text-left text-xs">{children}</table>
                  </div>
                ),
                th: ({ children }) => <th className="px-3 py-2 bg-slate-800/80 font-semibold text-slate-200">{children}</th>,
                td: ({ children }) => <td className="px-3 py-2 border-t border-slate-800/60 text-slate-300">{children}</td>,
                code: ({ className, children }) => {
                  return (
                    <code className="bg-slate-800 px-1.5 py-0.5 rounded text-orange-300 font-mono text-xs">
                      {children}
                    </code>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Live Streaming Indicator */}
        {isStreaming && (
          <span className="inline-block w-2 h-4 bg-orange-500 animate-pulse ml-1 align-middle rounded-sm" />
        )}

        {/* Sources Accordion */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="pt-2">
            <button
              onClick={() => setShowSources(!showSources)}
              className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition-colors font-medium"
            >
              <BookOpen className="w-3.5 h-3.5 text-orange-400" />
              <span>{message.sources.length} Verified Sources</span>
              {showSources ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {showSources && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {message.sources.map((src, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] text-slate-300 font-mono"
                  >
                    <ExternalLink className="w-3 h-3 text-orange-400" />
                    {src}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Action bar for assistant message */}
        {!isUser && !isStreaming && message.content && (
          <div className="pt-2 flex items-center gap-2">
            <button
              onClick={copyText}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800/40 hover:bg-slate-800 text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>

            {onRegenerate && (
              <button
                onClick={onRegenerate}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800/40 hover:bg-slate-800 text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Regenerate</span>
              </button>
            )}
          </div>
        )}

        {/* Follow-up question suggestion chips */}
        {!isUser && !isStreaming && followUps.length > 0 && onSelectFollowUp && (
          <div className="pt-3 flex flex-wrap gap-1.5 items-center">
            <span className="text-[11px] text-slate-500 font-medium mr-1 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-orange-400" /> Related:
            </span>
            {followUps.map((q, idx) => (
              <button
                key={idx}
                onClick={() => onSelectFollowUp(q)}
                className="text-[11px] px-2.5 py-1 rounded-full bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-slate-300 hover:text-orange-300 hover:border-orange-500/40 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
