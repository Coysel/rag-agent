/**
 * 格式化工具函数
 */

const Format = {
  /**
   * 格式化时间差（相对时间）
   * @param {number} timestamp - Unix 毫秒时间戳
   * @returns {string} "刚刚" | "3分钟前" | "2小时前" | "昨天" | ...
   */
  relativeTime(timestamp) {
    const now = Date.now();
    const diff = now - timestamp;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 30) return '刚刚';
    if (seconds < 60) return `${seconds}秒前`;
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days === 1) return '昨天';
    if (days < 7) return `${days}天前`;
    if (days < 30) return `${Math.floor(days / 7)}周前`;
    return new Date(timestamp).toLocaleDateString('zh-CN');
  },

  /**
   * 格式化绝对时间
   * @param {number} timestamp - Unix 毫秒时间戳
   * @returns {string} "14:30" 或 "2024-01-15 14:30"
   */
  absoluteTime(timestamp) {
    const d = new Date(timestamp);
    const now = new Date();
    const time = d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    if (d.toDateString() === now.toDateString()) return time;
    return `${d.toLocaleDateString('zh-CN')} ${time}`;
  },

  /**
   * 格式化时长
   * @param {number} ms - 毫秒
   * @returns {string} "1.2s" | "320ms"
   */
  duration(ms) {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    if (ms < 10000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.round(ms / 1000)}s`;
  },

  /**
   * 格式化字节大小
   */
  bytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  },

  /**
   * 格式化数字（添加千分位）
   */
  number(n) {
    return Number(n).toLocaleString('zh-CN');
  },

  /**
   * 截断文本
   * @param {string} text
   * @param {number} maxLen - 最大字符数
   * @param {string} [suffix='...']
   */
  truncate(text, maxLen, suffix = '...') {
    if (!text) return '';
    if (text.length <= maxLen) return text;
    return text.slice(0, maxLen - suffix.length) + suffix;
  },

  /**
   * 格式化分数（百分比或原始值）
   * @param {number} score - 0-1 之间的分数
   * @param {boolean} [pct=true] - 是否转为百分比
   */
  score(score, pct = true) {
    if (pct) return `${(score * 100).toFixed(1)}%`;
    return score.toFixed(3);
  },

  /**
   * 分数对应的颜色等级
   * @param {number} score - 0-1
   * @returns {'high'|'medium'|'low'}
   */
  scoreLevel(score) {
    if (score >= 0.7) return 'high';
    if (score >= 0.4) return 'medium';
    return 'low';
  },

  /**
   * JSON 安全序列化
   */
  safeStringify(obj, fallback = '{}') {
    try { return JSON.stringify(obj, null, 2); }
    catch { return fallback; }
  },
};
