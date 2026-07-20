/**
 * 打字指示器组件 — 三跳动点动画
 *
 * 用法:
 *   const el = TypingDots.show(container);  // 插入到容器末尾
 *   TypingDots.remove(el);                   // 移除
 */

const TypingDots = {
  /**
   * 在容器末尾插入打字指示器
   * @param {HTMLElement} container
   * @returns {HTMLElement} 指示器元素
   */
  show(container, scrollContainer) {
    const el = DOM.create('div', { className: 'message assistant' }, [
      DOM.create('div', { className: 'bubble' }, [
        DOM.create('div', { className: 'typing-indicator' }, [
          DOM.create('span', { className: 'typing-dot' }),
          DOM.create('span', { className: 'typing-dot' }),
          DOM.create('span', { className: 'typing-dot' }),
        ]),
      ]),
    ]);
    container.appendChild(el);
    DOM.scrollToBottom(scrollContainer || container);
    return el;
  },

  /**
   * 移除打字指示器
   * @param {HTMLElement} el - 由 show() 返回的元素
   */
  remove(el) {
    if (el && el.parentNode) {
      el.parentNode.removeChild(el);
    }
  },
};
