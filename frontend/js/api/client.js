/**
 * HTTP 客户端 — fetch 封装
 *
 * 提供:
 *   - 统一错误处理 + 结构化错误对象
 *   - 请求超时
 *   - 自动 JSON 解析
 *   - Admin Key 自动注入
 */

const APIClient = {
  /** 默认超时 (ms) */
  TIMEOUT: 120000,

  /**
   * 发起 HTTP 请求
   * @param {string} url - 完整的 URL 或相对路径
   * @param {Object} [options={}]
   * @param {string} [options.method='GET']
   * @param {Object} [options.body] - 请求体（自动 JSON 序列化）
   * @param {Object} [options.headers] - 额外 headers
   * @param {number} [options.timeout] - 超时 (ms)
   * @param {boolean} [options.isAdmin=false] - 是否需要 Admin Key
   * @returns {Promise<any>} 解析后的 JSON 响应
   */
  async request(url, options = {}) {
    const {
      method = 'GET',
      body,
      headers = {},
      timeout = this.TIMEOUT,
      isAdmin = false,
    } = options;

    // 构建 URL
    const fullUrl = url.startsWith('http') ? url : `${Config.API_BASE}${url}`;

    // 构建 headers
    const reqHeaders = {
      'Content-Type': 'application/json',
      ...headers,
    };

    // Admin Key
    if (isAdmin) {
      const adminKey = Store.get('settings').adminKey || 'admin-secret-change-me';
      reqHeaders['X-Admin-Key'] = adminKey;
    }

    // 构建 fetch options
    const fetchOpts = {
      method,
      headers: reqHeaders,
      signal: AbortSignal.timeout(timeout),
    };

    if (body && method !== 'GET' && method !== 'HEAD') {
      fetchOpts.body = JSON.stringify(body);
    }

    // 发起请求
    let response;
    try {
      response = await fetch(fullUrl, fetchOpts);
    } catch (err) {
      if (err.name === 'TimeoutError' || err.name === 'AbortError') {
        throw new APIError('请求超时', 'TIMEOUT', 408);
      }
      throw new APIError(`网络错误: ${err.message}`, 'NETWORK_ERROR', 0);
    }

    // 解析 JSON
    let data;
    try {
      data = await response.json();
    } catch {
      if (response.ok) {
        return null; // 空响应
      }
      throw new APIError(
        `服务器返回了无效的响应 (${response.status})`,
        'INVALID_RESPONSE',
        response.status
      );
    }

    // 检查业务错误
    if (!response.ok) {
      const errDetail = data?.detail || data?.error?.message || response.statusText;
      const errCode = data?.error?.code || 'HTTP_ERROR';
      throw new APIError(errDetail, errCode, response.status, data);
    }

    return data;
  },

  /** GET 请求 */
  get(url, opts = {}) {
    return this.request(url, { ...opts, method: 'GET' });
  },

  /** POST 请求 */
  post(url, body, opts = {}) {
    return this.request(url, { ...opts, method: 'POST', body });
  },

  /** DELETE 请求 */
  delete(url, opts = {}) {
    return this.request(url, { ...opts, method: 'DELETE' });
  },
};


/**
 * API 错误类
 */
class APIError extends Error {
  /**
   * @param {string} message
   * @param {string} code
   * @param {number} status
   * @param {Object} [data]
   */
  constructor(message, code = 'UNKNOWN', status = 0, data = null) {
    super(message);
    this.name = 'APIError';
    this.code = code;
    this.status = status;
    this.data = data;
  }
}
