/**
 * 聊天消息气泡组件
 *
 * 支持四种类型:
 *   - user:      用户消息（右对齐，蓝色）
 *   - assistant: AI 回答（左对齐，白色带边框）
 *   - system:    系统通知（居中，黄色）
 *   - error:     错误消息（左对齐，红色）
 */

const ChatBubble = {
  /**
   * 创建消息气泡元素
   * @param {Object} opts
   * @param {'user'|'assistant'|'system'|'error'} opts.type
   * @param {string} opts.content - HTML 内容
   * @param {Object} [opts.meta] - 元信息 { timestamp, queryType, steps }
   * @param {boolean} [opts.showCopy=true] - 是否显示复制按钮
   * @param {Function} [opts.onRetry] - 重试回调（仅 error 类型）
   * @returns {HTMLElement}
   */
  create(opts = {}) {
    const { type = 'assistant', content, meta = {}, showCopy = (type === 'assistant'), onRetry } = opts;

    const message = DOM.create('div', {
      className: `message ${type}`,
      dataset: { type },
    });

    // 元信息行
    if (meta.timestamp || meta.queryType) {
      const metaEl = DOM.create('div', { className: 'message-meta' });
      if (meta.queryType) {
        const qt = Config.QUERY_TYPES[meta.queryType];
        if (qt) {
          metaEl.appendChild(DOM.create('span', { className: 'badge', style: `background:${qt.color}15;color:${qt.color}` }, `${qt.icon} ${qt.label}`));
        }
      }
      if (meta.timestamp) {
        metaEl.appendChild(DOM.create('span', {}, Format.absoluteTime(meta.timestamp)));
      }
      message.appendChild(metaEl);
    }

    // 气泡
    const bubble = DOM.create('div', { className: 'bubble' }, [
      DOM.create('div', { className: 'bubble-content', html: content }),
    ]);

    // 操作按钮（AI 消息悬停显示）
    if (showCopy || onRetry) {
      const actions = DOM.create('div', { className: 'message-actions' });

      if (showCopy) {
        actions.appendChild(DOM.create('button', {
          className: 'message-action-btn',
          title: '复制',
          onClick() {
            const text = Markdown.strip(
              bubble.querySelector('.bubble-content')?.textContent || ''
            );
            navigator.clipboard.writeText(text).then(() => {
              Toast.success('已复制', '');
            }).catch(() => {
              Toast.error('复制失败', '');
            });
          },
        }, '📋'));
      }

      if (onRetry && type === 'error') {
        actions.appendChild(DOM.create('button', {
          className: 'message-action-btn',
          title: '重试',
          onClick: onRetry,
        }, '🔄'));
      }

      bubble.appendChild(actions);
    }

    message.appendChild(bubble);
    return message;
  },

  /**
   * 快捷创建用户消息
   */
  user(text) {
    return this.create({
      type: 'user',
      content: DOM.escapeHTML(text),
      showCopy: false,
      meta: { timestamp: Date.now() },
    });
  },

  /**
   * 快捷创建 AI 回答消息
   */
  assistant(html, meta = {}) {
    return this.create({
      type: 'assistant',
      content: html,
      showCopy: true,
      meta: { timestamp: Date.now(), ...meta },
    });
  },

  /**
   * 快捷创建错误消息
   */
  error(message, onRetry) {
    return this.create({
      type: 'error',
      content: DOM.escapeHTML(message),
      showCopy: false,
      onRetry,
    });
  },

  /**
   * 快捷创建系统消息
   */
  system(message) {
    return this.create({
      type: 'system',
      content: DOM.escapeHTML(message),
      showCopy: false,
    });
  },
};
