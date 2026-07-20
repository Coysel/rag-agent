/**
 * App 主入口 — 初始化所有模块、绑定全局事件
 */

(function () {
  'use strict';

  // ── DOM Ready ────────────────────────────────────────────

  function init() {
    // 恢复深色模式
    _initTheme();

    // 初始化 Tab 导航
    Tabs.init();

    // 初始化各页面
    ChatPage.init();
    RetrievalPage.init();
    EvalPage.init();
    AdminPage.init();
    SettingsPage.init();

    // 初始化 Sidebar（先恢复会话列表）
    _initSidebar();

    // 自动恢复上次会话
    _restoreLastSession();

    // 全局键盘快捷键
    _initKeyboardShortcuts();

    // 自动健康检查
    _autoHealthCheck();

    // 监听会话切换 → 刷新聊天 UI
    Store.subscribe('currentSessionId', (newId) => {
      if (newId) _highlightSession(newId);
    });

    // 监听会话列表变更 → 刷新侧栏
    Store.subscribe('sessions', () => {
      _renderSessionList();
    });

    console.log('[App] Agentic RAG v2.0 初始化完成');
  }

  // ── 主题 ────────────────────────────────────────────────
  function _initTheme() {
    const darkMode = Store.get('darkMode');
    if (darkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }

  // ── Sidebar ─────────────────────────────────────────────
  function _initSidebar() {
    const toggleBtn = DOM.$('#sidebar-toggle');
    const sidebar = DOM.$('.sidebar');
    const overlay = DOM.$('#sidebar-overlay');

    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        const open = !sidebar.classList.contains('open');
        DOM.toggleClass(sidebar, 'open', open);
        if (overlay) DOM.toggleClass(overlay, 'open', open);
        Store.setState({ sidebarOpen: open });
      });
    }

    if (overlay) {
      overlay.addEventListener('click', () => {
        DOM.removeClass(sidebar, 'open');
        DOM.removeClass(overlay, 'open');
        Store.setState({ sidebarOpen: false });
      });
    }

    // 新建会话按钮
    DOM.$('#sidebar-new-session')?.addEventListener('click', () => {
      if (Store.get('isStreaming')) return;
      const id = Store.createSession();
      ChatPage.clear();
      _renderSessionList();
      Toast.info('新会话', '已创建新对话');
    });

    // 加载会话列表
    _renderSessionList();
  }

  /** 恢复上次会话 */
  function _restoreLastSession() {
    const sessions = Store.loadSessionList();
    if (sessions.length > 0) {
      const lastId = sessions[0].id;
      const messages = Store.switchSession(lastId);
      if (messages.length > 0) {
        _renderMessagesFromHistory(messages);
      }
      _renderSessionList();
    }
  }

  /** 从历史消息渲染聊天界面 */
  function _renderMessagesFromHistory(messages) {
    const container = DOM.$('#chat-messages');
    if (!container) return;
    DOM.empty(container);

    messages.forEach(msg => {
      if (msg.role === 'user') {
        container.appendChild(ChatBubble.user(msg.content));
      } else if (msg.role === 'assistant') {
        const bubble = ChatBubble.create({
          type: 'assistant',
          content: Markdown.render(msg.content),
          showCopy: true,
          meta: {
            queryType: msg.queryType || '',
            timestamp: msg.timestamp,
          },
        });
        // Render sources if present
        if (msg.sources && msg.sources.length > 0) {
          const panel = SourcePanel.create(msg.sources);
          bubble.querySelector('.bubble')?.appendChild(panel);
        }
        container.appendChild(bubble);
      } else if (msg.role === 'error') {
        container.appendChild(ChatBubble.error(msg.content));
      }
    });

    // Scroll to bottom
    requestAnimationFrame(() => {
      DOM.scrollToBottom(DOM.$('.page[data-page="chat"]'));
    });
  }

  /** 渲染侧栏会话列表 */
  function _renderSessionList() {
    const container = DOM.$('#sidebar-sessions');
    if (!container) return;

    // 直接从 Store 读取，不调用 loadSessionList()（否则 setState 触发无限循环）
    const sessions = Store.get('sessions');
    const currentId = Store.get('currentSessionId');
    DOM.empty(container);

    if (!sessions.length) {
      container.appendChild(
        DOM.create('div', {
          style: 'text-align:center;color:var(--text-tertiary);font-size:var(--text-xs);padding:var(--space-4)',
        }, '暂无历史会话')
      );
      return;
    }

    sessions.forEach(s => {
      const isActive = s.id === currentId;

      const item = DOM.create('div', {
        className: 'session-item' + (isActive ? ' active' : ''),
        style: `
          padding: var(--space-2) var(--space-3);
          border-radius: var(--radius-sm);
          cursor: pointer;
          font-size: var(--text-xs);
          margin-bottom: 2px;
          transition: background var(--transition-fast);
          background: ${isActive ? 'var(--primary-light)' : ''};
          position: relative;
        `,
        title: s.title,
      });

      // Click → switch session
      item.addEventListener('click', () => {
        if (Store.get('isStreaming')) return;
        if (Store.get('currentSessionId') === s.id) return;

        const messages = Store.switchSession(s.id);
        _renderMessagesFromHistory(messages);
        _renderSessionList();
      });

      // Title
      const titleEl = DOM.create('div', {
        style: `overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:${isActive ? 'var(--weight-semibold)' : 'var(--weight-medium)'};color:${isActive ? 'var(--primary)' : 'var(--text-primary)'}`,
      }, s.title || '新对话');

      // Meta line
      const metaEl = DOM.create('div', {
        style: 'color:var(--text-tertiary);font-size:10px;margin-top:2px;display:flex;justify-content:space-between;align-items:center',
      }, [
        DOM.create('span', {}, `${s.messageCount} 条 · ${Format.relativeTime(s.updatedAt)}`),
      ]);

      // Delete button
      const delBtn = DOM.create('button', {
        className: 'session-delete-btn',
        style: `
          position:absolute;top:4px;right:4px;
          width:20px;height:20px;border-radius:var(--radius-xs);
          display:none;align-items:center;justify-content:center;
          font-size:10px;color:var(--text-tertiary);
          transition: all var(--transition-fast);
        `,
        title: '删除会话',
        onClick(e) {
          e.stopPropagation();
          Store.deleteSession(s.id);
          if (Store.get('currentSessionId') === '') {
            ChatPage.clear();
          }
          _renderSessionList();
          Toast.info('已删除', s.title);
        },
      }, '✕');

      item.appendChild(titleEl);
      item.appendChild(metaEl);
      item.appendChild(delBtn);

      // Hover effects
      item.addEventListener('mouseenter', () => {
        if (!item.classList.contains('active')) {
          item.style.background = 'var(--surface-tertiary)';
        }
        delBtn.style.display = 'flex';
      });
      item.addEventListener('mouseleave', () => {
        if (!item.classList.contains('active')) {
          item.style.background = '';
        }
        delBtn.style.display = 'none';
      });

      container.appendChild(item);
    });
  }

  /** 高亮侧栏当前会话 */
  function _highlightSession(sessionId) {
    const items = DOM.$$('.session-item');
    items.forEach(item => {
      // 简化高亮 — 重新渲染
    });
    _renderSessionList();
  }

  // ── 键盘快捷键 ───────────────────────────────────────────
  function _initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Ctrl+K — 清空聊天
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        ChatPage.clear();
      }

      // Escape — 停止生成
      if (e.key === 'Escape' && Store.get('isStreaming')) {
        ChatPage.stop();
      }

      // Ctrl+N — 新建会话
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        if (!Store.get('isStreaming')) {
          Store.createSession();
          ChatPage.clear();
          _renderSessionList();
        }
      }
    });
  }

  // ── 健康检查 ─────────────────────────────────────────────
  async function _autoHealthCheck() {
    try {
      const data = await HealthAPI.check();
      const statusEl = DOM.$('#system-status');
      if (statusEl) {
        if (data.index_ready) {
          statusEl.innerHTML = `<span style="color:var(--success)">●</span> ${data.document_count} 篇文档`;
        } else {
          statusEl.innerHTML = `<span style="color:var(--warning)">●</span> 索引未就绪`;
        }
      }
    } catch (e) {
      // 静默失败
    }
  }

  // ── 启动 ─────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
