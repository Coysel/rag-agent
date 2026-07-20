/**
 * 设置页面 — LLM 配置、检索参数、关于信息
 */

const SettingsPage = {
  _categories: [],  // 缓存的类别列表

  init() {
    this._loadSettings();
    this._bindControls();
    this._loadCategories();
  },

  _loadSettings() {
    const settings = Store.get('settings');

    // LLM Provider
    const providerSel = DOM.$('#settings-llm-provider');
    if (providerSel) providerSel.value = settings.llmProvider || 'deepseek';

    // Max Steps
    const maxStepsInput = DOM.$('#settings-max-steps');
    const maxStepsVal = DOM.$('#settings-max-steps-val');
    if (maxStepsInput) maxStepsInput.value = settings.maxSteps || 5;
    if (maxStepsVal) maxStepsVal.textContent = settings.maxSteps || 5;

    // Stream
    const streamToggle = DOM.$('#settings-stream');
    if (streamToggle) {
      DOM.toggleClass(streamToggle, 'active', settings.stream !== false);
    }

    // Admin Key
    const adminKeyInput = DOM.$('#settings-admin-key');
    if (adminKeyInput) {
      adminKeyInput.value = settings.adminKey || '';
    }

    // Auto Categorize
    const autoCatToggle = DOM.$('#settings-auto-categorize');
    if (autoCatToggle) {
      DOM.toggleClass(autoCatToggle, 'active', settings.autoCategorize !== false);
    }
  },

  // ── 类别管理 ────────────────────────────────────────────

  async _loadCategories() {
    try {
      const data = await CategoryAPI.list();
      this._categories = data.categories || [];
      this._renderCategoryTags();
    } catch (e) {
      // 静默失败 — 使用空列表
      this._categories = [];
      this._renderCategoryTags();
    }
  },

  _renderCategoryTags() {
    const container = DOM.$('#category-tags');
    if (!container) return;
    DOM.empty(container);

    if (!this._categories.length) {
      container.appendChild(DOM.create('span', {
        style: 'font-size:var(--text-xs);color:var(--text-tertiary)'
      }, '暂无类别 — 点击"生成类别"'));
      return;
    }

    const settings = Store.get('settings');
    const selected = settings.filters?.categories || [];

    this._categories.forEach(cat => {
      const isActive = selected.includes(cat.id);
      const tag = DOM.create('span', {
        className: 'category-tag' + (isActive ? ' active' : ''),
        style: `
          display:inline-flex;align-items:center;gap:4px;
          padding:4px 12px;border-radius:var(--radius-full);
          font-size:var(--text-xs);cursor:pointer;user-select:none;
          border:1px solid ${isActive ? 'var(--primary)' : 'var(--border)'};
          background:${isActive ? 'var(--primary-light)' : 'var(--surface)'};
          color:${isActive ? 'var(--primary)' : 'var(--text-secondary)'};
          transition:all var(--transition-fast);
        `,
        title: cat.description || '',
        onClick: () => this._toggleCategory(cat.id),
      }, [
        DOM.create('span', {}, cat.name),
        DOM.create('span', {
          style: `font-size:10px;opacity:0.6`
        }, `(${cat.document_count})`),
      ]);
      container.appendChild(tag);
    });
  },

  _progressHTML(stage, current, total, message) {
    const stageNames = {
      child_summaries: '📝 第 1 步：生成 chunk 摘要',
      parent_aggregation: '📄 第 2 步：聚合章节摘要',
      doc_aggregation: '📚 第 3 步：聚合文档摘要',
      clustering: '🧩 聚类中...',
      done: '✅ 完成',
      error: '❌ 出错',
      none: '⏳ 等待中',
    };
    const name = stageNames[stage] || stage;
    const pct = total > 0 ? Math.round(current / total * 100) : 0;

    if (stage === 'done' || stage === 'error') {
      return `
        <div style="padding:8px 0;font-size:var(--text-xs);color:${stage==='done'?'var(--success)':'var(--danger)'}">
          ${name} — ${message}
        </div>`;
    }

    return `
      <div style="padding:8px 0">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:var(--text-xs);color:var(--text-secondary)">
          <span>${name}</span>
          <span>${current}/${total} (${pct}%)</span>
        </div>
        <div style="height:4px;background:var(--border);border-radius:2px;overflow:hidden">
          <div style="height:100%;width:${pct}%;background:var(--primary);border-radius:2px;transition:width 0.5s"></div>
        </div>
      </div>`;
  },

  _toggleCategory(catId) {
    const settings = { ...Store.get('settings') };
    const filters = settings.filters || {};
    let categories = [...(filters.categories || [])];

    const idx = categories.indexOf(catId);
    if (idx >= 0) {
      categories.splice(idx, 1);  // 取消选中
    } else {
      categories.push(catId);     // 选中
    }

    settings.filters = { ...filters, categories };
    Store.setState({ settings });
    Store.persist('settings', Config.STORAGE_KEYS.SETTINGS);
    this._renderCategoryTags();
  },

  _bindControls() {
    // LLM Provider
    DOM.$('#settings-llm-provider')?.addEventListener('change', (e) => {
      this._updateSetting('llmProvider', e.target.value);
    });

    // Max Steps
    DOM.$('#settings-max-steps')?.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      const display = DOM.$('#settings-max-steps-val');
      if (display) display.textContent = val;
      this._updateSetting('maxSteps', val);
    });

    // Stream Toggle
    DOM.$('#settings-stream')?.addEventListener('click', function () {
      const active = !this.classList.contains('active');
      DOM.toggleClass(this, 'active', active);
      SettingsPage._updateSetting('stream', active);
    });

    // Admin Key
    DOM.$('#settings-admin-key')?.addEventListener('change', (e) => {
      const key = e.target.value.trim();
      this._updateSetting('adminKey', key);
      localStorage.setItem(Config.STORAGE_KEYS.ADMIN_KEY, key);
    });

    // Auto Categorize Toggle
    DOM.$('#settings-auto-categorize')?.addEventListener('click', function () {
      const active = !this.classList.contains('active');
      DOM.toggleClass(this, 'active', active);
      SettingsPage._updateSetting('autoCategorize', active);
    });

    // Health Check Button
    DOM.$('#settings-health-btn')?.addEventListener('click', async () => {
      try {
        Toast.info('检查中...', '正在获取系统状态');
        const data = await HealthAPI.check();
        Toast.success('系统正常', [
          `文档: ${data.document_count} 篇`,
          `向量: ${data.chunk_count} 条`,
          `LLM: ${data.llm_provider} / ${data.llm_model}`,
          `Embedding: ${data.embedding_provider} / ${data.embedding_model}`,
        ].join(' · '));
      } catch (err) {
        Toast.error('健康检查失败', err.message);
      }
    });

    // Generate Categories
    DOM.$('#settings-gen-categories')?.addEventListener('click', async () => {
      const adminKey = Store.get('settings').adminKey;
      if (!adminKey) {
        Toast.error('需要 Admin Key', '请先在 Admin 设置中配置 API Key');
        return;
      }

      const btn = DOM.$('#settings-gen-categories');
      const progressEl = DOM.$('#category-progress');
      const origText = btn.textContent;
      btn.textContent = '⏳ 生成中...';
      btn.disabled = true;

      // 显示进度条
      if (progressEl) {
        progressEl.style.display = 'block';
        progressEl.innerHTML = this._progressHTML('child_summaries', 0, 1, '启动中...');
      }

      // 启动进度轮询
      const pollInterval = setInterval(async () => {
        try {
          const p = await CategoryAPI.progress();
          if (progressEl) {
            progressEl.innerHTML = this._progressHTML(p.stage, p.current, p.total, p.message);
          }
          if (p.stage === 'done' || p.stage === 'error') {
            clearInterval(pollInterval);
          }
        } catch (_) { /* 静默 */ }
      }, 2000);

      try {
        await CategoryAPI.generate(adminKey);
        clearInterval(pollInterval);
        Toast.success('类别已生成', '请刷新查看结果');
        await this._loadCategories();
        if (progressEl) progressEl.style.display = 'none';
      } catch (err) {
        clearInterval(pollInterval);
        Toast.error('生成失败', err.message);
        if (progressEl) progressEl.style.display = 'none';
      } finally {
        btn.textContent = origText;
        btn.disabled = false;
      }
    });

    // Clear Chat History
    DOM.$('#settings-clear-history')?.addEventListener('click', () => {
      Modal.confirm({
        title: '清空聊天历史',
        body: '确定要清空所有本地保存的聊天历史记录吗？此操作不可恢复。',
        confirmText: '清空',
        confirmVariant: 'danger',
        onConfirm: () => {
          localStorage.removeItem(Config.STORAGE_KEYS.CHAT_HISTORY);
          Toast.success('已清空', '所有聊天历史已删除');
        },
      });
    });
  },

  _updateSetting(key, value) {
    const settings = { ...Store.get('settings'), [key]: value };
    Store.setState({ settings });
    Store.persist('settings', Config.STORAGE_KEYS.SETTINGS);
  },
};
