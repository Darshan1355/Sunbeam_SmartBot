export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  tools_used?: string[];
  created_at: string;
  status?: 'sending' | 'streaming' | 'done' | 'error';
  tool_activity?: {
    tool: string;
    status: string;
    message?: string;
  }[];
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface KnowledgeStats {
  collection_name: string;
  persist_directory: string;
  total_documents: number;
  dimension: number;
  sources_breakdown: Record<string, number>;
  status: string;
}

export interface ToolItem {
  name: string;
  description: string;
  category: string;
  is_available: boolean;
  parameters: Record<string, any>;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}
