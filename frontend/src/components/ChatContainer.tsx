import React, { useRef, useEffect } from 'react';
import { Message } from '../types/chat';
import { MessageItem } from './MessageItem';
import { WelcomeScreen } from './WelcomeScreen';

interface ChatContainerProps {
  messages: Message[];
  isStreaming: boolean;
  onSelectPrompt: (prompt: string) => void;
  onRegenerate: () => void;
  onRetry: () => void;
  onSelectFollowUp: (text: string) => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  isStreaming,
  onSelectPrompt,
  onRegenerate,
  onRetry,
  onSelectFollowUp,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  if (messages.length === 0) {
    return <WelcomeScreen onSelectPrompt={onSelectPrompt} />;
  }

  return (
    <div className="flex-1 overflow-y-auto divide-y divide-slate-800/40">
      {messages.map((msg, index) => {
        const isLast = index === messages.length - 1;
        return (
          <MessageItem
            key={msg.id || index}
            message={msg}
            isStreaming={isLast && isStreaming && msg.role === 'assistant'}
            onRegenerate={isLast && msg.role === 'assistant' ? onRegenerate : undefined}
            onRetry={isLast && msg.status === 'error' ? onRetry : undefined}
            onSelectFollowUp={isLast ? onSelectFollowUp : undefined}
          />
        );
      })}
      <div ref={bottomRef} className="h-4" />
    </div>
  );
};
