/**
 * 聊天 API — 对话相关接口
 */

const ChatAPI = {
  /**
   * 发送消息（自动选择单轮/多轮）
   * @param {string} query
   * @param {Object} [opts]
   * @param {boolean} [opts.stream=true]
   * @param {number} [opts.maxSteps=5]
   * @returns {Promise<Response>} fetch Response（用于 SSE 流解析）
   */
  async sendMessage(query, opts = {}) {
    const settings = Store.get('settings');
    const sessionId = Store.get('currentSessionId');
    const endpoint = sessionId ? Config.ENDPOINTS.CHAT_SESSION : Config.ENDPOINTS.CHAT;

    const body = {
      query,
      stream: opts.stream ?? settings.stream ?? true,
      max_steps: opts.maxSteps ?? settings.maxSteps ?? 5,
    };

    if (sessionId) {
      body.session_id = sessionId;
    }

    // 传递选中的类别过滤
    const filters = settings.filters || {};
    if (filters.categories && filters.categories.length > 0) {
      body.categories = filters.categories;
    }

    // 传递联网搜索开关
    if (settings.webSearchEnabled) {
      body.web_search = true;
    }

    return fetch(`${Config.API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: opts.signal || undefined,
    });
  },

  /**
   * 获取会话列表
   */
  async listSessions() {
    return APIClient.get(Config.ENDPOINTS.SESSIONS);
  },

  /**
   * 删除会话
   */
  async deleteSession(sessionId) {
    return APIClient.delete(`${Config.ENDPOINTS.SESSIONS}/${sessionId}`);
  },
};
