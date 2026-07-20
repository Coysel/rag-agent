/**
 * Admin 管理页面 — 文档 CRUD
 */

const AdminPage = {
  _loading: false,

  init() {
    const rebuildBtn = DOM.$('#admin-rebuild-btn');
    const addBtn = DOM.$('#admin-add-btn');
    const refreshBtn = DOM.$('#admin-refresh-btn');
    const apiKeyInput = DOM.$('#admin-apikey-input');

    // 从 localStorage 恢复 API Key
    if (apiKeyInput) {
      const saved = localStorage.getItem(Config.STORAGE_KEYS.ADMIN_KEY);
      if (saved) {
        apiKeyInput.value = saved;
        Store.setState({ settings: { ...Store.get('settings'), adminKey: saved } });
      }

      apiKeyInput.addEventListener('change', () => {
        const key = apiKeyInput.value.trim();
        localStorage.setItem(Config.STORAGE_KEYS.ADMIN_KEY, key);
        Store.setState({ settings: { ...Store.get('settings'), adminKey: key } });
      });
    }

    if (rebuildBtn) {
      rebuildBtn.addEventListener('click', () => {
        Modal.confirm({
          title: '确认重建索引',
          body: '<p>重建索引将<strong>清空所有现有索引</strong>并重新扫描文档目录。此操作不可撤销，且可能需要几分钟时间。</p><p>确定要继续吗？</p>',
          confirmText: '重建',
          confirmVariant: 'danger',
          onConfirm: () => this.rebuild(),
        });
      });
    }

    if (addBtn) {
      addBtn.addEventListener('click', () => this.showAddForm());
    }

    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadDocuments());
    }

    // 上传拖拽区
    const uploadZone = DOM.$('#upload-zone');
    if (uploadZone) {
      uploadZone.addEventListener('click', () => this.showAddForm());

      uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        DOM.addClass(uploadZone, 'dragover');
      });

      uploadZone.addEventListener('dragleave', () => {
        DOM.removeClass(uploadZone, 'dragover');
      });

      uploadZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        DOM.removeClass(uploadZone, 'dragover');
        const file = e.dataTransfer.files[0];
        if (file) {
          try {
            const text = await file.text();
            this.addDocument({
              content: text,
              title: file.name.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' '),
              source: file.name,
            });
          } catch (err) {
            Toast.error('读取文件失败', err.message);
          }
        }
      });
    }
  },

  async loadDocuments() {
    if (this._loading) return;
    this._loading = true;
    Store.setState({ adminLoading: true });

    try {
      // 尝试从 admin 端点加载（需要 API Key）
      const data = await AdminAPI.listDocuments();
      Store.setState({ documents: data.documents || [], adminLoading: false });
      this._renderTable(data.documents || []);
    } catch (err) {
      // 回退到公开端点
      try {
        const data = await APIClient.get(Config.ENDPOINTS.DOCUMENTS);
        Store.setState({ documents: data.documents || [], adminLoading: false });
        this._renderTable(data.documents || []);
      } catch (err2) {
        Store.setState({ adminLoading: false });
        Toast.error('加载文档列表失败', err2.message);
      }
    }

    this._loading = false;
  },

  _renderTable(docs) {
    const container = DOM.$('#admin-doc-list');
    if (!container) return;
    DOM.empty(container);

    if (!docs || docs.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📂</div>
          <div class="empty-state-title">暂无文档</div>
          <div class="empty-state-desc">上传文档或运行索引脚本来添加文档到知识库</div>
        </div>
      `;
      return;
    }

    docs.forEach(doc => {
      const row = DOM.create('div', { className: 'doc-table-row' }, [
        DOM.create('div', { className: 'doc-title' }, doc.title || '未命名'),
        DOM.create('div', { className: 'doc-source' }, doc.source || '-'),
        DOM.create('div', { className: 'doc-chunks' }, `${doc.chunk_count || 0}`),
        DOM.create('div', { className: 'doc-actions' }, [
          DOM.create('button', {
            className: 'btn btn-ghost btn-sm',
            title: '删除',
            onClick() {
              Modal.confirm({
                title: '确认删除',
                body: `<p>确定要删除文档 <strong>"${DOM.escapeHTML(doc.title || '未命名')}"</strong> 吗？</p><p style="color:var(--text-tertiary)">此操作将移除该文档的所有索引 chunks，不可恢复。</p>`,
                confirmText: '删除',
                confirmVariant: 'danger',
                onConfirm: async () => {
                  try {
                    await AdminAPI.deleteDocument(doc.doc_id);
                    Toast.success('已删除', doc.title);
                    AdminPage.loadDocuments();
                  } catch (err) {
                    Toast.error('删除失败', err.message);
                  }
                },
              });
            },
          }, '🗑️'),
        ]),
      ]);
      container.appendChild(row);
    });
  },

  showAddForm() {
    Modal.show({
      title: '添加文档',
      content: `
        <div style="display:flex;flex-direction:column;gap:12px">
          <div>
            <label style="display:block;font-size:var(--text-sm);font-weight:var(--weight-medium);margin-bottom:4px">标题</label>
            <input type="text" id="add-doc-title" class="input" placeholder="文档标题">
          </div>
          <div>
            <label style="display:block;font-size:var(--text-sm);font-weight:var(--weight-medium);margin-bottom:4px">来源（选填）</label>
            <input type="text" id="add-doc-source" class="input" placeholder="来源文件名或路径">
          </div>
          <div>
            <label style="display:block;font-size:var(--text-sm);font-weight:var(--weight-medium);margin-bottom:4px">内容</label>
            <textarea id="add-doc-content" class="input" rows="8" placeholder="粘贴文档内容..."></textarea>
          </div>
          <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:8px">
            <button class="btn btn-secondary" onclick="document.querySelector('.modal-overlay').remove()">取消</button>
            <button class="btn btn-primary" id="add-doc-submit">添加</button>
          </div>
        </div>
      `,
      width: 560,
    });

    // 绑定提交按钮
    setTimeout(() => {
      const submitBtn = DOM.$('#add-doc-submit');
      if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
          const title = DOM.$('#add-doc-title')?.value.trim();
          const content = DOM.$('#add-doc-content')?.value.trim();
          const source = DOM.$('#add-doc-source')?.value.trim();

          if (!title) { Toast.warning('请输入标题'); return; }
          if (!content) { Toast.warning('请输入内容'); return; }

          try {
            await this.addDocument({ title, content, source });
            // 关闭模态框
            const overlay = document.querySelector('.modal-overlay');
            if (overlay) overlay.remove();
          } catch (err) {
            // error handled in addDocument
          }
        });
      }
    }, 100);
  },

  async addDocument(doc) {
    try {
      const result = await AdminAPI.addDocument(doc);

      // 显示分类结果
      const cat = result.auto_categorized;
      if (cat && !cat.skipped) {
        const verb = cat.is_new ? '📁 已创建新类别' : '📂 已归入';
        Toast.success('文档已添加并自动分类', `${verb}「${cat.category_name}」— ${cat.reason || ''}`);
      } else {
        Toast.success('文档已添加', doc.title);
      }

      this.loadDocuments();
    } catch (err) {
      Toast.error('添加失败', err.message);
      throw err;
    }
  },

  async rebuild() {
    try {
      Toast.info('重建中', '正在重新索引所有文档，请耐心等待...');
      const result = await AdminAPI.rebuildIndex();
      Toast.success('索引重建完成', `${result.documents} 篇文档, ${result.child_chunks} 个 chunks`);
      this.loadDocuments();
    } catch (err) {
      Toast.error('重建失败', err.message);
    }
  },
};
