"""
Session 持久化存储 — 基于 SQLite

替代原有的进程内 dict: _sessions: dict[str, list[dict]]

特性:
  - 重启不丢失
  - 自动过期清理（默认 24 小时未访问的 session）
  - 线程安全（SQLite WAL 模式）

用法:
    store = SessionStore("data/sessions.db")
    history = store.get(session_id)
    store.append(session_id, user_msg, assistant_msg)
"""
import json
import sqlite3
import time
import os
from pathlib import Path
from typing import List, Optional


class SessionStore:
    """SQLite 持久化的会话存储"""

    MAX_MESSAGES = 20       # 最多保留 20 条消息（10 轮）
    TTL_SECONDS = 86400     # 24 小时过期

    def __init__(self, db_path: str = ""):
        if not db_path:
            from config import DATA_DIR
            db_path = os.path.join(str(DATA_DIR), "sessions.db")
        self._db_path = str(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取连接（WAL 模式，线程安全）"""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        """初始化表结构"""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    history_json TEXT NOT NULL DEFAULT '[]',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_updated_at ON sessions(updated_at)
            """)
            conn.commit()

    # ── CRUD ─────────────────────────────────────────────────

    def get(self, session_id: str) -> list[dict]:
        """获取会话历史（自动续期）"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT history_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if row:
                # touch 更新时间
                conn.execute(
                    "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                    (time.time(), session_id),
                )
                conn.commit()
                try:
                    return json.loads(row[0])
                except (json.JSONDecodeError, TypeError):
                    return []

            return []

    def get_all_sessions(self) -> list[dict]:
        """列出所有会话（按更新时间倒序）"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT session_id, history_json, updated_at FROM sessions ORDER BY updated_at DESC LIMIT 50"
            ).fetchall()

            result = []
            for row in rows:
                try:
                    history = json.loads(row[1])
                except (json.JSONDecodeError, TypeError):
                    history = []
                # 提取最后一轮用户问题作为标题
                title = ""
                for msg in reversed(history):
                    if msg.get("role") == "user":
                        title = msg.get("content", "")[:50]
                        break

                result.append({
                    "session_id": row[0],
                    "title": title or "新对话",
                    "message_count": len(history),
                    "updated_at": row[2],
                })
            return result

    def save(self, session_id: str, history: list[dict]):
        """保存或更新会话历史"""
        now = time.time()
        # 裁剪到限制
        if len(history) > self.MAX_MESSAGES:
            history = history[-self.MAX_MESSAGES:]

        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO sessions (session_id, history_json, created_at, updated_at)
                   VALUES (?, ?, COALESCE((SELECT created_at FROM sessions WHERE session_id=?), ?), ?)""",
                (session_id, json.dumps(history, ensure_ascii=False), session_id, now, now),
            )
            conn.commit()

    def append(self, session_id: str, user_msg: str, assistant_msg: str):
        """追加一轮对话到会话"""
        history = self.get(session_id)
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_msg})
        self.save(session_id, history)

    def delete(self, session_id: str) -> bool:
        """删除一个会话"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def cleanup(self) -> int:
        """清理过期会话，返回清理数"""
        cutoff = time.time() - self.TTL_SECONDS
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE updated_at < ?",
                (cutoff,),
            )
            conn.commit()
            return cursor.rowcount


# ── 全局单例 ────────────────────────────────────────────────

_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """获取全局 SessionStore 实例"""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
