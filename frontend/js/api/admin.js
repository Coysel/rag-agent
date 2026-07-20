/**
 * Admin API — 文档管理接口
 */

const AdminAPI = {
  /**
   * 列出所有文档
   */
  async listDocuments() {
    return APIClient.get(Config.ENDPOINTS.ADMIN_DOCUMENTS, { isAdmin: true });
  },

  /**
   * 添加文档
   * @param {Object} doc - { content, title, source }
   */
  async addDocument(doc) {
    return APIClient.post(Config.ENDPOINTS.ADMIN_DOCUMENTS, doc, { isAdmin: true });
  },

  /**
   * 删除文档
   * @param {string} docId
   */
  async deleteDocument(docId) {
    return APIClient.delete(`${Config.ENDPOINTS.ADMIN_DOCUMENTS}/${docId}`, { isAdmin: true });
  },

  /**
   * 全量重建索引
   */
  async rebuildIndex() {
    return APIClient.post(Config.ENDPOINTS.ADMIN_REBUILD, {}, { isAdmin: true });
  },
};
