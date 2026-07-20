/**
 * 评测 API
 */

const EvalAPI = {
  /**
   * 检索对比 (非流式)
   */
  async compareRetrieval(query) {
    return APIClient.post(Config.ENDPOINTS.EVAL_RETRIEVAL, { query });
  },

  /**
   * 单条评测 (非流式)
   */
  async evaluateSingle(query) {
    return APIClient.post(Config.ENDPOINTS.EVAL_SINGLE, { query });
  },

  /**
   * RAGAS 评测 — SSE 流式
   * @param {number} count - 测试问题数量
   * @returns {Promise<Response>}
   */
  async startRagasEval(count = 5) {
    return fetch(`${Config.API_BASE}${Config.ENDPOINTS.EVAL_RAGAS}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count }),
    });
  },

  /**
   * 自定义评测 — SSE 流式
   * @param {string[]} questions
   * @returns {Promise<Response>}
   */
  async startCustomEval(questions) {
    return fetch(`${Config.API_BASE}${Config.ENDPOINTS.EVAL_CUSTOM}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ questions }),
    });
  },
};
