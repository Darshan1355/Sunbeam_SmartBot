export interface StreamCallbacks {
  onStatus?: (message: string) => void;
  onTool?: (tool: string, status: string, message?: string) => void;
  onToken?: (token: string) => void;
  onSources?: (sources: string[]) => void;
  onDone?: (data: any) => void;
  onError?: (error: string) => void;
}

export async function streamChatResponse(
  message: string,
  conversationId: string | null,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '') + '/api';
  const response = await fetch(`${apiBase}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
    }),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Server returned error ${response.status}: ${errorText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('ReadableStream not supported by browser.');

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = 'message';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          currentEvent = 'message';
          continue;
        }

        if (trimmed.startsWith('event:')) {
          currentEvent = trimmed.slice(6).trim();
          continue;
        }

        if (trimmed.startsWith('data:')) {
          const jsonStr = trimmed.slice(5).trim();
          try {
            const data = JSON.parse(jsonStr);

            if (currentEvent === 'status' && callbacks.onStatus) {
              callbacks.onStatus(data.message || 'Processing...');
            } else if (currentEvent === 'tool' && callbacks.onTool) {
              callbacks.onTool(data.tool, data.status, data.message);
            } else if (currentEvent === 'token' && callbacks.onToken) {
              callbacks.onToken(data.content || '');
            } else if (currentEvent === 'sources' && callbacks.onSources) {
              callbacks.onSources(data.sources || []);
            } else if (currentEvent === 'done' && callbacks.onDone) {
              callbacks.onDone(data);
            } else if (currentEvent === 'error' && callbacks.onError) {
              callbacks.onError(data.error || 'Unknown streaming error');
            }
          } catch (e) {
            // Raw text fallback
            if (currentEvent === 'token' && callbacks.onToken) {
              callbacks.onToken(jsonStr);
            }
          }
        }
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      callbacks.onStatus?.('Generation stopped.');
    } else {
      callbacks.onError?.(err.message || 'Stream interrupted.');
    }
    throw err;
  }
}
