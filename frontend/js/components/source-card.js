/**
 * 来源引用卡片组件
 *
 * 用法:
 *   const panel = SourcePanel.create(sources);
 *   SourcePanel.toggle(panel);
 */

const SourcePanel = {
  /**
   * 创建来源面板
   * @param {Object[]} sources - [{ title, source, score, content }]
   * @returns {HTMLElement}
   */
  create(sources = []) {
    if (!sources.length) return DOM.create('div');

    const panel = DOM.create('div', { className: 'sources-panel' });

    const header = DOM.create('div', {
      className: 'sources-header',
      onClick() { DOM.toggleClass(panel, 'open'); },
    }, [
      DOM.create('span', { className: 'thinking-icon' }, '▶'),
      DOM.create('span', {}, `📚 引用来源 (${sources.length})`),
    ]);

    const list = DOM.create('div', { className: 'sources-list' });

    sources.forEach((src, i) => {
      const level = Format.scoreLevel(src.score || 0);
      const scoreText = Format.score(src.score || 0);

      const item = DOM.create('div', {
        className: 'source-item',
        dataset: { title: src.title },
        id: `source-${i}`,
      }, [
        DOM.create('div', { className: 'source-item-header' }, [
          DOM.create('span', { className: 'source-item-title' }, src.title || '未知来源'),
          DOM.create('div', { style: 'display:flex;align-items:center;gap:6px' }, [
            DOM.create('span', { className: 'source-item-score' }, scoreText),
            DOM.create('div', { className: 'score-bar' }, [
              DOM.create('div', {
                className: `score-bar-fill score-${level}`,
                style: `width:${Math.round((src.score || 0) * 100)}%`,
              }),
            ]),
          ]),
        ]),
        src.source ? DOM.create('div', { className: 'source-item-path' }, src.source) : null,
        src.content ? DOM.create('div', { className: 'source-item-preview' }, DOM.escapeHTML(src.content.slice(0, 200))) : null,
      ].filter(Boolean));

      list.appendChild(item);
    });

    panel.appendChild(header);
    panel.appendChild(list);
    return panel;
  },

  /**
   * 展开/折叠来源面板
   */
  toggle(panel) {
    DOM.toggleClass(panel, 'open');
  },

  /**
   * 展开并高亮指定来源
   * @param {HTMLElement} panel
   * @param {string} title - 来源标题（部分匹配）
   */
  highlight(panel, title) {
    if (!panel) return;
    DOM.addClass(panel, 'open');

    const items = panel.querySelectorAll('.source-item');
    items.forEach(item => {
      DOM.removeClass(item, 'highlight');
      if (item.dataset.title && item.dataset.title.includes(title)) {
        DOM.addClass(item, 'highlight');
        DOM.scrollTo(item);
      }
    });
  },
};
