import { Conversation, KnowledgeStats, Message, ToolItem } from '../types/chat';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '') + '/api';

export async function fetchConversations(): Promise<Conversation[]> {
  const res = await fetch(`${API_BASE}/conversations`);
  if (!res.ok) throw new Error('Failed to fetch conversations');
  return res.json();
}

export async function createConversation(title: string = 'New Chat'): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error('Failed to create conversation');
  return res.json();
}

export async function fetchConversation(id: string): Promise<{ conversation: Conversation; messages: Message[] }> {
  const res = await fetch(`${API_BASE}/conversations/${id}`);
  if (!res.ok) throw new Error('Failed to load conversation messages');
  return res.json();
}

export async function renameConversation(id: string, title: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error('Failed to rename conversation');
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete conversation');
}

export async function clearConversationMessages(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${id}/messages`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to clear messages');
}

export async function fetchKnowledgeStats(): Promise<KnowledgeStats> {
  const res = await fetch(`${API_BASE}/knowledge-base/stats`);
  if (!res.ok) throw new Error('Failed to fetch knowledge base stats');
  return res.json();
}

export async function updateKnowledgeBase(forceReindex: boolean = false): Promise<any> {
  const res = await fetch(`${API_BASE}/knowledge-base/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force_reindex: forceReindex }),
  });
  if (!res.ok) throw new Error('Failed to update knowledge base');
  return res.json();
}

export async function searchKnowledgeBase(query: string, top_k: number = 4): Promise<any> {
  const res = await fetch(`${API_BASE}/knowledge-base/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k }),
  });
  if (!res.ok) throw new Error('Failed to search knowledge base');
  return res.json();
}

export async function fetchTools(): Promise<ToolItem[]> {
  const res = await fetch(`${API_BASE}/tools`);
  if (!res.ok) throw new Error('Failed to fetch tools');
  const data = await res.json();
  return data.tools || [];
}

export async function fetchConfig(): Promise<any> {
  const res = await fetch(`${API_BASE}/config`);
  if (!res.ok) throw new Error('Failed to fetch config');
  return res.json();
}

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to fetch health');
  return res.json();
}
