/**
 * 类别 API — 类别列表 + 生成
 */
const CategoryAPI = {
  /**
   * 获取所有类别
   */
  async list() {
    const res = await fetch(`${Config.API_BASE}/categories`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  /**
   * 生成类别（需要 Admin Key）
   */
  async generate(adminKey) {
    const res = await fetch(`${Config.API_BASE}/admin/categories/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': adminKey,
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  /**
   * 查询生成进度（无需 Admin Key）
   */
  async progress() {
    const res = await fetch(`${Config.API_BASE}/admin/categories/progress`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
};
