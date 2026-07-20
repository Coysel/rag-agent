/**
 * 思考过程组件 — ReAct 步骤可视化
 *
 * 用法:
 *   const block = ThinkingBlock.create();
 *   ThinkingBlock.addStep(block, 'reason', '分析问题...');
 *   ThinkingBlock.addStep(block, 'act', '执行工具: search_documents');
 *   ThinkingBlock.finalize(block, 4, 2300);  // 4 步, 2.3s
 */

const ThinkingBlock = {
  /**
   * 创建思考过程折叠块
   * @returns {HTMLElement}
   */
  create() {
    const block = DOM.create('div', { className: 'thinking-block open' });

    const header = DOM.create('div', {
      className: 'thinking-header',
      onClick() { DOM.toggleClass(block, 'open'); },
    }, [
      DOM.create('span', { className: 'thinking-icon' }, '▶'),
      DOM.create('span', { className: 'thinking-summary' }, '🧠 思考中...'),
    ]);

    const body = DOM.create('div', { className: 'thinking-body' });

    block.appendChild(header);
    block.appendChild(body);
    return block;
  },

  /**
   * 添加一个 ReAct 步骤
   * @param {HTMLElement} block
   * @param {string} nodeName - reason | act | observe | reflect | answer
   * @param {string} content - 步骤内容
   */
  addStep(block, nodeName, content) {
    const body = block.querySelector('.thinking-body');
    if (!body) return;

    const icons = {
      reason: '💭', act: '🔧', observe: '👁️', reflect: '🪞', answer: '✅',
    };

    const step = DOM.create('div', { className: 'thinking-step' },
      `${icons[nodeName] || '•'} [${nodeName}] ${content}`
    );
    body.appendChild(step);

    // 自动滚动到底部
    body.scrollTop = body.scrollHeight;
  },

  /**
   * 完成思考过程，更新摘要并折叠
   * @param {HTMLElement} block
   * @param {number} stepCount - 总步数
   * @param {number} elapsedMs - 耗时 (ms)
   */
  finalize(block, stepCount, elapsedMs) {
    const summary = block.querySelector('.thinking-summary');
    if (summary) {
      summary.textContent = `🔍 思考过程 (${stepCount} 步 · ${Format.duration(elapsedMs)})`;
    }
    DOM.removeClass(block, 'open');
  },

  /**
   * 更新实时状态（流式过程中）
   * @param {HTMLElement} block
   * @param {string} text
   */
  updateStatus(block, text) {
    const summary = block.querySelector('.thinking-summary');
    if (summary) {
      summary.textContent = `🧠 ${text}`;
    }
  },
};
