/**
 * 全局配置 — API 端点、常量、默认参数
 */
const Config = {
  // ── API ──────────────────────────────────────────────────
  API_BASE: window.location.origin,
  ENDPOINTS: {
    CHAT: '/chat',
    CHAT_SESSION: '/chat/session',
    SESSIONS: '/chat/sessions',
    HEALTH: '/health',
    HEALTH_DEEP: '/health/deep',
    LLM_TEST: '/llm-test',
    DOCUMENTS: '/documents',
    EVAL_RETRIEVAL: '/eval/retrieval',
    EVAL_SINGLE: '/eval/single',
    EVAL_RAGAS: '/eval/ragas',
    EVAL_CUSTOM: '/eval/custom',
    ADMIN_DOCUMENTS: '/admin/documents',
    ADMIN_REBUILD: '/admin/rebuild',
    CATEGORIES: '/categories',
    CATEGORIES_GENERATE: '/admin/categories/generate',
    CATEGORIES_PROGRESS: '/admin/categories/progress',
  },

  // ── 默认参数 ─────────────────────────────────────────────
  DEFAULT_MAX_STEPS: 5,
  DEFAULT_STREAM: true,

  // ── localStorage Keys ────────────────────────────────────
  STORAGE_KEYS: {
    CHAT_HISTORY: 'rag_chat_history',
    SETTINGS: 'rag_settings',
    SESSIONS: 'rag_sessions',
    ADMIN_KEY: 'rag_admin_key',
  },

  // ── 限制 ─────────────────────────────────────────────────
  MAX_HISTORY_RECORDS: 200,
  TOAST_DURATION: 4000,
  MAX_QUERY_LENGTH: 4000,

  // ── 查询类型映射 ─────────────────────────────────────────
  QUERY_TYPES: {
    factual:   { label: '事实查询', icon: '🔍', color: '#4F6EF7' },
    conceptual:{ label: '概念解释', icon: '💡', color: '#22C55E' },
    multi_hop: { label: '多步推理', icon: '🧩', color: '#F59E0B' },
  },
};
