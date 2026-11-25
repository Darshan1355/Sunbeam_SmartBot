"""
Thread-safe SQLite conversation persistence service for Sunbeam SmartBot.
Uses standard library sqlite3 with WAL mode for fast, rock-solid persistence.
"""
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger("app.services.session")


class SessionService:
    """
    Thread-safe SQLite session manager for persistent chat history.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent / "data"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = base_dir / "conversations.sqlite3"

        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        """Initializes database tables if they do not exist."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        sources TEXT DEFAULT '[]',
                        tools_used TEXT DEFAULT '[]',
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    );
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, created_at);"
                )
                conn.commit()
        logger.info(f"SQLite SessionService initialized at: {self.db_path}")

    def create_conversation(self, title: str = "New Chat") -> Dict[str, Any]:
        """Creates a new conversation thread."""
        conv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?);",
                    (conv_id, title, now, now),
                )
                conn.commit()

        return {
            "id": conv_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
        }

    def list_conversations(self) -> List[Dict[str, Any]]:
        """Returns all conversations ordered by last update descending."""
        query = """
            SELECT c.id, c.title, c.created_at, c.updated_at, COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id
            ORDER BY c.updated_at DESC;
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchall()
                return [dict(r) for r in rows]

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a specific conversation."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM conversations WHERE id = ?;", (conv_id,))
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_messages(self, conv_id: str) -> List[Dict[str, Any]]:
        """Retrieves all messages for a given conversation thread."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC;",
                    (conv_id,),
                )
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    try:
                        item["sources"] = json.loads(item["sources"])
                    except Exception:
                        item["sources"] = []
                    try:
                        item["tools_used"] = json.loads(item["tools_used"])
                    except Exception:
                        item["tools_used"] = []
                    results.append(item)
                return results

    def save_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        sources: Optional[List[str]] = None,
        tools_used: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Saves a message and updates the conversation's timestamp."""
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        sources_json = json.dumps(sources or [])
        tools_json = json.dumps(tools_used or [])

        with self._lock:
            with self._get_connection() as conn:
                # Ensure conversation exists
                cursor = conn.execute("SELECT id FROM conversations WHERE id = ?;", (conv_id,))
                if not cursor.fetchone():
                    # Auto-create if not existing
                    title = content[:30] + "..." if len(content) > 30 else content
                    conn.execute(
                        "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?);",
                        (conv_id, title, now, now),
                    )

                conn.execute(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, sources, tools_used, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (msg_id, conv_id, role, content, sources_json, tools_json, now),
                )
                conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?;",
                    (now, conv_id),
                )
                conn.commit()

        return {
            "id": msg_id,
            "conversation_id": conv_id,
            "role": role,
            "content": content,
            "sources": sources or [],
            "tools_used": tools_used or [],
            "created_at": now,
        }

    def rename_conversation(self, conv_id: str, title: str) -> bool:
        """Renames a conversation."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?;",
                    (title, now, conv_id),
                )
                conn.commit()
                return cursor.rowcount > 0

    def delete_conversation(self, conv_id: str) -> bool:
        """Deletes a conversation and all its messages."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM conversations WHERE id = ?;", (conv_id,))
                conn.commit()
                return cursor.rowcount > 0

    def clear_history(self, conv_id: str) -> bool:
        """Deletes all messages inside a conversation but keeps the conversation."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM messages WHERE conversation_id = ?;", (conv_id,))
                conn.commit()
                return cursor.rowcount > 0


_session_service_instance: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """Singleton provider for SessionService."""
    global _session_service_instance
    if _session_service_instance is None:
        _session_service_instance = SessionService()
    return _session_service_instance
