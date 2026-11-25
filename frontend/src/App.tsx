import React, { useState, useEffect, useRef } from 'react';
import { Conversation, Message, ToastMessage } from './types/chat';
import {
  fetchConversations,
  fetchConversation,
  createConversation,
  renameConversation,
  deleteConversation,
  clearConversationMessages,
} from './services/api';
import { streamChatResponse } from './services/stream';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ChatContainer } from './components/ChatContainer';
import { ChatInput } from './components/ChatInput';
import { KnowledgeBaseModal } from './components/KnowledgeBaseModal';
import { ToolsModal } from './components/ToolsModal';
import { SettingsModal } from './components/SettingsModal';
import { ToastContainer } from './components/Toast';

export const App: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Modals
  const [isKnowledgeOpen, setIsKnowledgeOpen] = useState(false);
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const addToast = (type: 'success' | 'error' | 'info', message: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Load conversations on mount
  useEffect(() => {
    loadConversationsList();
  }, []);

  const loadConversationsList = async () => {
    try {
      const data = await fetchConversations();
      setConversations(data);
      if (data.length > 0 && !activeId) {
        // Select first conversation
        selectConversation(data[0].id);
      }
    } catch (err: any) {
      addToast('error', 'Could not connect to backend server. Make sure FastAPI is running on port 8000.');
    }
  };

  const selectConversation = async (id: string) => {
    try {
      setActiveId(id);
      const data = await fetchConversation(id);
      setMessages(data.messages || []);
    } catch (err: any) {
      addToast('error', `Failed to load conversation: ${err.message}`);
    }
  };

  const handleNewChat = () => {
    if (isStreaming) {
      handleStop();
    }
    setActiveId(null);
    setMessages([]);
  };

  const handleRename = async (id: string, newTitle: string) => {
    try {
      await renameConversation(id, newTitle);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
      );
      addToast('success', 'Conversation renamed');
    } catch (err: any) {
      addToast('error', `Rename failed: ${err.message}`);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteConversation(id);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      if (activeId === id) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          handleNewChat();
        }
      }
      addToast('info', 'Conversation deleted');
    } catch (err: any) {
      addToast('error', `Delete failed: ${err.message}`);
    }
  };

  const handleClearHistory = async () => {
    if (!activeId) {
      setMessages([]);
      return;
    }
    try {
      await clearConversationMessages(activeId);
      setMessages([]);
      addToast('info', 'Cleared messages for this conversation');
    } catch (err: any) {
      addToast('error', `Clear failed: ${err.message}`);
    }
  };

  const handleClearAll = async () => {
    for (const c of conversations) {
      try {
        await deleteConversation(c.id);
      } catch (e) {}
    }
    setConversations([]);
    handleNewChat();
    addToast('success', 'All conversations deleted');
  };

  const handleSendMessage = async (text: string) => {
    if (isStreaming || !text.trim()) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      conversation_id: activeId || '',
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
      status: 'done',
    };

    const assistantMsgId = `assistant-${Date.now()}`;
    const assistantPlaceholder: Message = {
      id: assistantMsgId,
      conversation_id: activeId || '',
      role: 'assistant',
      content: '',
      sources: [],
      tool_activity: [],
      created_at: new Date().toISOString(),
      status: 'streaming',
    };

    setMessages((prev) => [...prev, userMsg, assistantPlaceholder]);
    setIsStreaming(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await streamChatResponse(
        text,
        activeId,
        {
          onStatus: (msg) => {
            // Optional status update
          },
          onTool: (tool, status, message) => {
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== assistantMsgId) return m;
                const existing = m.tool_activity || [];
                const updated = [...existing.filter((t) => t.tool !== tool), { tool, status, message }];
                return { ...m, tool_activity: updated };
              })
            );
          },
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== assistantMsgId) return m;
                return { ...m, content: m.content + token };
              })
            );
          },
          onSources: (sources) => {
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== assistantMsgId) return m;
                return { ...m, sources };
              })
            );
          },
          onDone: (data) => {
            setIsStreaming(false);
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== assistantMsgId) return m;
                return { ...m, status: 'done', conversation_id: data.conversation_id };
              })
            );
            // Refresh conversation list to get new thread title or order
            loadConversationsList();
            if (!activeId && data.conversation_id) {
              setActiveId(data.conversation_id);
            }
          },
          onError: (errMsg) => {
            setIsStreaming(false);
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== assistantMsgId) return m;
                return { ...m, status: 'error', content: `Error: ${errMsg}` };
              })
            );
            addToast('error', errMsg);
          },
        },
        controller.signal
      );
    } catch (err: any) {
      setIsStreaming(false);
      if (err.name !== 'AbortError') {
        addToast('error', `Connection error: ${err.message}`);
      }
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      addToast('info', 'Generation stopped.');
    }
  };

  const handleRegenerate = () => {
    // Find last user message
    const lastUser = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUser) {
      // Remove last assistant message
      setMessages((prev) => prev.slice(0, -1));
      handleSendMessage(lastUser.content);
    }
  };

  const activeTitle = conversations.find((c) => c.id === activeId)?.title || 'New Chat';

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 font-sans">
      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />

      {/* Sidebar */}
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNewChat={handleNewChat}
        onRename={handleRename}
        onDelete={handleDelete}
        onOpenKnowledgeBase={() => setIsKnowledgeOpen(true)}
        onOpenTools={() => setIsToolsOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        isOpen={isSidebarOpen}
        onCloseMobile={() => setIsSidebarOpen(false)}
      />

      {/* Main Workspace */}
      <main className="flex-1 flex flex-col h-full min-w-0 bg-slate-950">
        <Header
          title={activeTitle}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          onClearHistory={handleClearHistory}
          onOpenKnowledgeBase={() => setIsKnowledgeOpen(true)}
        />

        <ChatContainer
          messages={messages}
          isStreaming={isStreaming}
          onSelectPrompt={handleSendMessage}
          onRegenerate={handleRegenerate}
          onRetry={handleRegenerate}
          onSelectFollowUp={handleSendMessage}
        />

        <ChatInput
          onSend={handleSendMessage}
          onStop={handleStop}
          isStreaming={isStreaming}
        />
      </main>

      {/* Modals */}
      <KnowledgeBaseModal
        isOpen={isKnowledgeOpen}
        onClose={() => setIsKnowledgeOpen(false)}
        onNotify={addToast}
      />

      <ToolsModal
        isOpen={isToolsOpen}
        onClose={() => setIsToolsOpen(false)}
        onNotify={addToast}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onClearAllChats={handleClearAll}
        onNotify={addToast}
      />
    </div>
  );
};

export default App;
