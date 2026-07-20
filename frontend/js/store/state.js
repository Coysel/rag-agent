/**
 * 轻量状态管理 — 发布-订阅模式
 *
 * 用法:
 *   Store.subscribe('chatMessages', (newVal) => { ... });
 *   Store.setState({ currentTab: 'eval' });
 *   Store.get('chatMessages');
 */

const Store = (function () {
  const _state = {
    // ── 导航 ────────────────────────────────────────────
    currentTab: 'chat',

    // ── 会话 ────────────────────────────────────────────
    currentSessionId: '',
    sessions: [],

    // ── 聊天 ────────────────────────────────────────────
    chatMessages: [],
    isStreaming: false,
    lastQuery: '',
    lastStream: true,

    // ── 检索对比 ─────────────────────────────────────────
    retrievalQuery: '',
    retrievalResults: null,
    retrievalLoading: false,

    // ── 评测 ─────────────────────────────────────────────
    evalProgress: null,
    evalResults: [],
    evalLoading: false,

    // ── 管理 ─────────────────────────────────────────────
    documents: [],
    adminLoading: false,

    // ── 设置 ─────────────────────────────────────────────
    settings: {
      llmProvider: 'deepseek',
      maxSteps: 5,
      stream: true,
      adminKey: '',
      autoCategorize: true,
      webSearchEnabled: false,
      filters: {
        categories: [],
      },
    },

    // ── UI ───────────────────────────────────────────────
    sidebarOpen: false,
    darkMode: false,
  };

  /** @type {Map<string, Set<Function>>} */
  const _subscribers = new Map();

  /**
   * 读取状态（只读副本）
   */
  function get(key) {
    if (key) return _state[key];
    return { ..._state };
  }

  /**
   * 更新状态并通知订阅者
   */
  function setState(partial) {
    const changed = [];
    for (const [key, val] of Object.entries(partial)) {
      if (_state[key] !== val) {
        _state[key] = val;
        changed.push(key);
      }
    }
    // 通知每个变更 key 的订阅者
    for (const key of changed) {
      const subs = _subscribers.get(key);
      if (subs) {
        subs.forEach(fn => {
          try { fn(_state[key], _state); }
          catch (e) { console.error(`[Store] subscriber error for "${key}":`, e); }
        });
      }
    }
    // 通知 '*' 通配订阅者
    const wildcardSubs = _subscribers.get('*');
    if (wildcardSubs) {
      wildcardSubs.forEach(fn => {
        try { fn(changed, _state); }
        catch (e) { console.error('[Store] wildcard subscriber error:', e); }
      });
    }
  }

  /**
   * 订阅状态变更
   * @param {string} key - 订阅的 key，或 '*' 通配
   * @param {Function} fn - 回调 (newValue, fullState)
   * @returns {Function} 取消订阅函数
   */
  function subscribe(key, fn) {
    if (!_subscribers.has(key)) {
      _subscribers.set(key, new Set());
    }
    _subscribers.get(key).add(fn);
    return () => _subscribers.get(key).delete(fn);
  }

  /**
   * 持久化指定 key 到 localStorage
   */
  function persist(key, storageKey) {
    const val = _state[key];
    try {
      localStorage.setItem(storageKey || key, JSON.stringify(val));
    } catch (e) { /* quota exceeded, ignore */ }
  }

  /**
   * 从 localStorage 恢复
   */
  function restore(key, storageKey, fallback) {
    try {
      const raw = localStorage.getItem(storageKey || key);
      if (raw) {
        _state[key] = JSON.parse(raw);
        return;
      }
    } catch (e) { /* ignore */ }
    if (fallback !== undefined) _state[key] = fallback;
  }

  // ── 初始化：从 localStorage 恢复设置 ──────────────────
  restore('settings', 'rag_settings', _state.settings);

  // ═══════════════════════════════════════════════════════════
  // Session management utilities
  // ═══════════════════════════════════════════════════════════

  const MAX_SESSIONS = 50;
  const MAX_MESSAGES_PER_SESSION = 200;
  const SESSIONS_KEY = 'rag_sessions';

  /** Generate a short unique session ID */
  function _genId() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID().slice(0, 8);
    }
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  }

  /** Load session metadata list from localStorage */
  function _loadSessionMeta() {
    try {
      const raw = localStorage.getItem(SESSIONS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }

  /** Save session metadata list to localStorage */
  function _saveSessionMeta(list) {
    try {
      localStorage.setItem(SESSIONS_KEY, JSON.stringify(list.slice(0, MAX_SESSIONS)));
    } catch (e) { /* quota exceeded */ }
  }

  /**
   * Create a new session and make it current.
   * @returns {string} new session ID
   */
  function createSession() {
    const id = _genId();
    const now = Date.now();
    const meta = { id, title: '新对话', messageCount: 0, updatedAt: now };

    const sessions = _loadSessionMeta();
    sessions.unshift(meta);
    _saveSessionMeta(sessions);

    setState({
      currentSessionId: id,
      sessions: sessions,
      chatMessages: [],
    });

    return id;
  }

  /**
   * Save messages for the current session.
   * Also updates the session metadata (title from first user message, count, time).
   */
  function saveSessionMessages(sessionId, messages) {
    if (!sessionId) return;

    // Trim
    const trimmed = messages.slice(-MAX_MESSAGES_PER_SESSION);

    try {
      localStorage.setItem('rag_session_' + sessionId, JSON.stringify(trimmed));
    } catch (e) { /* quota exceeded */ }

    // Update metadata
    const sessions = _loadSessionMeta();
    const idx = sessions.findIndex(s => s.id === sessionId);
    const title = _extractTitle(trimmed);
    const now = Date.now();

    if (idx >= 0) {
      sessions[idx].title = title;
      sessions[idx].messageCount = trimmed.length;
      sessions[idx].updatedAt = now;
    } else {
      sessions.unshift({ id: sessionId, title, messageCount: trimmed.length, updatedAt: now });
    }

    _saveSessionMeta(sessions);
    setState({ sessions: sessions });
  }

  /** Extract title from first user message */
  function _extractTitle(messages) {
    for (const m of messages) {
      if (m.role === 'user' && m.content) {
        return m.content.slice(0, 40);
      }
    }
    return '新对话';
  }

  /**
   * Load messages for a session from localStorage.
   * @returns {Array} messages array (empty if not found)
   */
  function loadSessionMessages(sessionId) {
    if (!sessionId) return [];
    try {
      const raw = localStorage.getItem('rag_session_' + sessionId);
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }

  /**
   * Switch to a different session, loading its messages.
   */
  function switchSession(sessionId) {
    const messages = loadSessionMessages(sessionId);
    setState({
      currentSessionId: sessionId,
      chatMessages: messages,
    });
    return messages;
  }

  /**
   * Delete a session (metadata + messages).
   */
  function deleteSession(sessionId) {
    try { localStorage.removeItem('rag_session_' + sessionId); } catch (e) { /* */ }
    const sessions = _loadSessionMeta().filter(s => s.id !== sessionId);
    _saveSessionMeta(sessions);

    if (_state.currentSessionId === sessionId) {
      setState({
        sessions: sessions,
        currentSessionId: '',
        chatMessages: [],
      });
    } else {
      setState({ sessions: sessions });
    }
  }

  /**
   * Load all session metadata (for sidebar).
   */
  function loadSessionList() {
    const sessions = _loadSessionMeta();
    // Sort by updatedAt desc
    sessions.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
    setState({ sessions: sessions });
    return sessions;
  }

  return {
    get, setState, subscribe, persist, restore,
    createSession, saveSessionMessages, loadSessionMessages,
    switchSession, deleteSession, loadSessionList,
  };
})();
