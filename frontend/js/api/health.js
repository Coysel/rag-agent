/**
 * 健康检查 API
 */

const HealthAPI = {
  /** 基础健康检查 */
  async check() {
    return APIClient.get(Config.ENDPOINTS.HEALTH);
  },

  /** 深度健康检查（含 LLM 和检索验证） */
  async checkDeep() {
    return APIClient.get(Config.ENDPOINTS.HEALTH_DEEP);
  },

  /** LLM 连通测试 */
  async testLLM() {
    return APIClient.get(Config.ENDPOINTS.LLM_TEST);
  },
};
