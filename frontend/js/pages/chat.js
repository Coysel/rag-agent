/**
 * 聊天页面 — 核心交互逻辑
 *
 * 管理: 消息列表、SSE 流式接收、思考过程折叠、来源引用、输入发送
 */

const ChatPage = {
  _answerBubble: null,
  _typingEl: null,
  _thinkingBlock: null,
  _currentAnswer: '',
  _currentSources: [],
  _steps: [],
  _stepStartTime: 0,
  _abortController: null,

  /** 初始化 */
  init() {
    const input = DOM.$('#chat-input');
    const sendBtn = DOM.$('#send-btn');
    const stopBtn = DOM.$('#stop-btn');

    // Enter 发送 / Shift+Enter 换行
    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.send();
        }
      });

      // Auto-resize
      input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 200) + 'px';
      });
    }

    // 发送按钮
    if (sendBtn) {
      sendBtn.addEventListener('click', () => this.send());
    }

    // 联网搜索 toggle
    const webToggle = DOM.$('#web-search-toggle');
    if (webToggle) {
      // 恢复状态
      const settings = Store.get('settings');
      const enabled = !!settings.webSearchEnabled;
      DOM.toggleClass(webToggle, 'active', enabled);
      webToggle.title = enabled ? '联网搜索（已开启）' : '联网搜索（默认关闭）';

      webToggle.addEventListener('click', () => {
        const active = !webToggle.classList.contains('active');
        DOM.toggleClass(webToggle, 'active', active);
        webToggle.title = active ? '联网搜索（已开启）' : '联网搜索（默认关闭）';
        const s = { ...Store.get('settings'), webSearchEnabled: active };
        Store.setState({ settings: s });
        Store.persist('settings', Config.STORAGE_KEYS.SETTINGS);
      });
    }

    // 停止按钮
    if (stopBtn) {
      stopBtn.addEventListener('click', () => this.stop());
    }

    // 滚动由 .page[data-page="chat"] 的 overflow-y: auto 原生处理
    // 页面全宽滚动，统一惯性/动量/滚动条体验
  },

  /** 发送消息 */
  async send() {
    const input = DOM.$('#chat-input');
    const query = input.value.trim();
    if (!query || Store.get('isStreaming')) return;

    // 自动创建会话
    if (!Store.get('currentSessionId')) {
      Store.createSession();
    }

    const messagesEl = DOM.$('#chat-messages');
    const scrollEl = DOM.$('.page[data-page="chat"]');

    // 清空输入
    input.value = '';
    input.style.height = 'auto';

    // 添加用户消息
    messagesEl.appendChild(ChatBubble.user(query));
    DOM.scrollToBottom(scrollEl);

    // 重置并创建思考过程块，立即插入 DOM
    this._thinkingBlock = null;
    this._thinkingBlock = ThinkingBlock.create();
    messagesEl.appendChild(this._thinkingBlock);
    DOM.scrollToBottom(scrollEl);

    // 显示打字指示器
    this._typingEl = TypingDots.show(messagesEl, scrollEl);

    this._currentAnswer = '';
    this._currentSources = [];
    this._steps = [];
    this._stepStartTime = Date.now();
    this._answerBubble = null;

    // 创建 AbortController 供停止按钮使用
    this._abortController = new AbortController();

    // 状态
    Store.setState({
      isStreaming: true,
      lastQuery: query,
      lastStream: true,
    });
    this._updateSendButton();

    try {
      const response = await ChatAPI.sendMessage(query, {
        stream: true,
        signal: this._abortController.signal,
      });

      const stepLabels = {
        reason: '分析问题', act: '执行工具', observe: '处理结果', reflect: '评估信息',
      };
      const _handleStep = (type, data) => {
        if (type === 'reason') {
          TypingDots.remove(this._typingEl);
          this._typingEl = null;
        }
        this._steps.push({ type, ...data });
        if (this._thinkingBlock) {
          ThinkingBlock.addStep(this._thinkingBlock, type, data.content || stepLabels[type] || type);
        }
      };

      SSEStream.stream(response, {
        reason: (data) => _handleStep('reason', data),
        act: (data) => _handleStep('act', data),
        observe: (data) => _handleStep('observe', data),
        reflect: (data) => _handleStep('reflect', data),
        answer: (data) => {
          // 首次收到 answer 事件 → 准备 UI（不添加内容，首事件含思考步骤文案）
          if (!this._answerBubble) {
            TypingDots.remove(this._typingEl);
            this._typingEl = null;

            // 添加 Answer 步骤到思考过程
            if (this._thinkingBlock) {
              ThinkingBlock.addStep(this._thinkingBlock, 'answer',
                data.content || '✍️ 生成回答');
            }

            // 完成思考过程（已在 DOM 中，直接折叠即可）
            if (this._thinkingBlock && this._thinkingBlock.parentNode) {
              const elapsed = Date.now() - this._stepStartTime;
              ThinkingBlock.finalize(this._thinkingBlock, this._steps.length + 1, elapsed);
              this._thinkingBlock = null;
            }

            // 创建 AI 回答气泡（逐句流式更新内容）
            this._answerBubble = ChatBubble.create({
              type: 'assistant',
              content: '',
              showCopy: true,
              meta: {
                queryType: data.data?.query_type || '',
              },
            });
            messagesEl.appendChild(this._answerBubble);
            DOM.scrollToBottom(scrollEl);
            return;  // 首事件只做初始化，不累积内容
          }

          // 后续事件 → 逐句流式累积
          if (data.content) {
            this._currentAnswer += data.content;
            const contentEl = this._answerBubble?.querySelector('.bubble-content');
            if (contentEl) {
              contentEl.innerHTML = Markdown.render(this._currentAnswer);
              // 仅当用户在底部时才自动滚动（上翻时不强制跳回）
              if (DOM.isNearBottom(scrollEl, 400)) {
                DOM.scrollToBottom(scrollEl);
              }
            }
          }
        },
        done: (data) => {
          const inner = data.data || data;
          const answer = inner.answer || '';
          const sources = inner.sources || [];
          const queryType = inner.query_type || '';

          // 更新完整答案
          if (answer && answer !== this._currentAnswer) {
            this._currentAnswer = answer;
            const contentEl = this._answerBubble?.querySelector('.bubble-content');
            if (contentEl) {
              contentEl.innerHTML = Markdown.render(answer);
            }
          }

          // 更新元信息
          if (this._answerBubble && queryType) {
            const meta = this._answerBubble.querySelector('.message-meta');
            if (meta) {
              const qt = Config.QUERY_TYPES[queryType];
              if (qt) {
                meta.innerHTML = `<span class="badge" style="background:${qt.color}15;color:${qt.color}">${qt.icon} ${qt.label}</span>`;
              }
            }
          }

          // 处理来源引用（在回答中渲染为可点击链接）
          this._currentSources = sources;
          this._renderSourceLinks();

          // 添加来源面板
          if (sources.length && this._answerBubble) {
            const panel = SourcePanel.create(sources);
            this._answerBubble.querySelector('.bubble').appendChild(panel);
            DOM.scrollToBottom(scrollEl);
          }

          this._finish();
        },
        error: (data) => {
          TypingDots.remove(this._typingEl);
          this._typingEl = null;
          // 用户主动停止（AbortError）不显示错误气泡
          const msg = typeof data === 'string' ? data : (data.content || data.message || '未知错误');
          const isAbort = /abort|cancel/i.test(msg);
          if (!isAbort) {
            messagesEl.appendChild(ChatBubble.error(msg, () => this.send()));
            DOM.scrollToBottom(scrollEl);
          }
          this._finish();
        },
        '*': (eventType, data) => {
          // 未识别的 SSE 事件类型
          if (eventType === 'progress') return; // 评测进度，聊天中忽略
        },
        _streamEnd: () => {
          if (Store.get('isStreaming')) {
            this._finish();
          }
        },
      });
    } catch (err) {
      TypingDots.remove(this._typingEl);
      this._typingEl = null;
      messagesEl.appendChild(ChatBubble.error(err.message || '请求失败', () => this.send()));
      DOM.scrollToBottom(scrollEl);
      this._finish();
    }
  },

  /** 在回答中渲染来源引用链接 */
  _renderSourceLinks() {
    if (!this._answerBubble || !this._currentSources.length) return;

    const contentEl = this._answerBubble.querySelector('.bubble-content');
    if (!contentEl) return;

    // 替换 [来源: XXX] 为可点击链接
    let html = contentEl.innerHTML;
    const panel = this._answerBubble.querySelector('.sources-panel');

    html = html.replace(/\[来源:\s*([^\]]+)\]/g, (match, ref) => {
      const escapedRef = DOM.escapeHTML(ref);
      return `<span class="source-cite" onclick="ChatPage._activateSource('${escapedRef}')" title="点击查看来源">📎 ${escapedRef}</span>`;
    });

    contentEl.innerHTML = html;
  },

  /** 点击来源引用时展开面板并高亮 */
  _activateSource(ref) {
    const panel = DOM.$('.sources-panel');
    if (panel) {
      SourcePanel.highlight(panel, ref);
    }
  },

  /** 停止生成 */
  stop() {
    if (this._abortController) {
      this._abortController.abort();
    }
    this._finish();
  },

  /** 完成本轮对话 */
  _finish() {
    Store.setState({ isStreaming: false });
    this._updateSendButton();

    // 清理思考过程块（已在 DOM 中或未插入）
    if (this._thinkingBlock && this._steps.length > 0) {
      if (!this._thinkingBlock.parentNode) {
        const messagesEl = DOM.$('#chat-messages');
        messagesEl.appendChild(this._thinkingBlock);
      }
      const elapsed = Date.now() - this._stepStartTime;
      ThinkingBlock.finalize(this._thinkingBlock, this._steps.length, elapsed);
      this._thinkingBlock = null;
    }

    // 清理打字指示器
    if (this._typingEl) {
      TypingDots.remove(this._typingEl);
      this._typingEl = null;
    }

    // 清理本轮引用（防止跨轮泄漏）
    this._answerBubble = null;
    this._abortController = null;

    // 保存到 localStorage
    if (this._currentAnswer) {
      this._saveToHistory();
    }

    // 聚焦输入框
    setTimeout(() => DOM.$('#chat-input')?.focus(), 100);
  },

  /** 保存当前对话到 session */
  _saveToHistory() {
    const sessionId = Store.get('currentSessionId');
    if (!sessionId) return;

    try {
      // Load existing messages for this session
      let messages = Store.loadSessionMessages(sessionId);

      // Append user message
      messages.push({
        role: 'user',
        content: Store.get('lastQuery'),
        timestamp: Date.now(),
      });

      // Append assistant message
      messages.push({
        role: 'assistant',
        content: this._currentAnswer,
        sources: this._currentSources,
        steps: this._steps.length,
        queryType: this._steps.find(s => s.data?.query_type)?.data?.query_type || '',
        timestamp: Date.now(),
      });

      Store.saveSessionMessages(sessionId, messages);
    } catch (e) { /* quota exceeded */ }
  },

  /** 更新发送/停止按钮状态 */
  _updateSendButton() {
    const isStreaming = Store.get('isStreaming');
    const sendBtn = DOM.$('#send-btn');
    const stopBtn = DOM.$('#stop-btn');

    if (sendBtn) {
      sendBtn.disabled = isStreaming;
    }
    if (stopBtn) {
      DOM.toggleClass(stopBtn, 'visible', isStreaming);
    }
  },

  /** 清空聊天 */
  clear() {
    const messagesEl = DOM.$('#chat-messages');
    DOM.empty(messagesEl);
    // 显示欢迎消息
    messagesEl.appendChild(ChatBubble.system('👋 欢迎使用 <strong>Agentic RAG 智能问答系统</strong>。基于 LangGraph ReAct 循环 + MCP 工具协议 + 混合检索（BM25 + Dense + RRF）。请在下方输入你的问题，系统将检索知识库并生成回答。'));
  },

  /** 渲染历史消息到界面 */
  renderHistory(messages) {
    const container = DOM.$('#chat-messages');
    if (!container) return;
    DOM.empty(container);

    if (!messages || messages.length === 0) {
      this.clear();
      return;
    }

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
        if (msg.sources && msg.sources.length > 0) {
          const panel = SourcePanel.create(msg.sources);
          bubble.querySelector('.bubble')?.appendChild(panel);
        }
        container.appendChild(bubble);
      }
    });

    requestAnimationFrame(() => {
      DOM.scrollToBottom(DOM.$('.page[data-page="chat"]'));
    });
  },
};
