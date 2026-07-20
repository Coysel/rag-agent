/**
 * 通用模态框组件
 *
 * 用法:
 *   Modal.confirm({
 *     title: '确认删除',
 *     body: '确定要删除该文档吗？此操作不可恢复。',
 *     confirmText: '删除',
 *     onConfirm: async () => { ... },
 *   });
 */

const Modal = (function () {
  /**
   * 显示确认对话框
   * @param {Object} opts
   * @param {string} opts.title
   * @param {string} opts.body - HTML 或纯文本
   * @param {string} [opts.confirmText='确认']
   * @param {string} [opts.cancelText='取消']
   * @param {'primary'|'danger'} [opts.confirmVariant='primary']
   * @param {Function} [opts.onConfirm] - 异步确认回调
   * @param {Function} [opts.onCancel]
   */
  function confirm(opts = {}) {
    const {
      title = '确认',
      body = '',
      confirmText = '确认',
      cancelText = '取消',
      confirmVariant = 'primary',
      onConfirm,
      onCancel,
    } = opts;

    const overlay = DOM.create('div', { className: 'modal-overlay' });

    const modal = DOM.create('div', { className: 'modal' }, [
      DOM.create('div', { className: 'modal-header' }, [
        DOM.create('h3', { className: 'modal-title' }, title),
        DOM.create('button', {
          className: 'btn btn-ghost btn-icon',
          onClick() { close(); },
        }, '×'),
      ]),
      DOM.create('div', { className: 'modal-body', html: body }),
      DOM.create('div', { className: 'modal-footer' }, [
        DOM.create('button', {
          className: 'btn btn-secondary',
          onClick() { close(); },
        }, cancelText),
        DOM.create('button', {
          className: `btn btn-${confirmVariant}`,
          async onClick() {
            const btn = this;
            btn.disabled = true;
            btn.textContent = '处理中...';
            try {
              if (onConfirm) await onConfirm();
            } finally {
              btn.disabled = false;
              btn.textContent = confirmText;
            }
            close();
          },
        }, confirmText),
      ]),
    ]);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // 点击遮罩关闭
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });

    // Esc 关闭
    function onKey(e) {
      if (e.key === 'Escape') close();
    }
    document.addEventListener('keydown', onKey);

    function close() {
      document.removeEventListener('keydown', onKey);
      overlay.remove();
      if (onCancel) onCancel();
    }

    return { close };
  }

  /**
   * 显示自定义内容模态框
   * @param {Object} opts
   * @param {string} opts.title
   * @param {HTMLElement|string} opts.content - DOM 元素或 HTML 字符串
   * @param {number} [opts.width] - 宽度 (px)
   */
  function show(opts = {}) {
    const { title = '', content = '', width } = opts;

    const overlay = DOM.create('div', { className: 'modal-overlay' });

    const modal = DOM.create('div', { className: 'modal', style: width ? { maxWidth: `${width}px` } : {} }, [
      DOM.create('div', { className: 'modal-header' }, [
        DOM.create('h3', { className: 'modal-title' }, title),
        DOM.create('button', {
          className: 'btn btn-ghost btn-icon',
          onClick() { close(); },
        }, '×'),
      ]),
      DOM.create('div', { className: 'modal-body' }),
    ]);

    const body = modal.querySelector('.modal-body');
    if (typeof content === 'string') {
      body.innerHTML = content;
    } else if (content instanceof HTMLElement) {
      body.appendChild(content);
    }

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });

    function onKey(e) {
      if (e.key === 'Escape') close();
    }
    document.addEventListener('keydown', onKey);

    function close() {
      document.removeEventListener('keydown', onKey);
      overlay.remove();
    }

    return { close, el: modal };
  }

  return { confirm, show };
})();
