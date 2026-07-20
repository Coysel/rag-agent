/**
 * Toast 通知系统
 *
 * 用法:
 *   Toast.success('操作成功');
 *   Toast.error('操作失败', '请重试');
 *   Toast.info('提示', '数据加载中...');
 */

const Toast = (function () {
  let _container = null;

  function _ensureContainer() {
    if (!_container || !document.contains(_container)) {
      _container = DOM.create('div', { className: 'toast-container' });
      document.body.appendChild(_container);
    }
    return _container;
  }

  /**
   * 显示 Toast
   * @param {'success'|'error'|'warning'|'info'} type
   * @param {string} title
   * @param {string} [message='']
   * @param {number} [duration=4000]
   */
  function show(type, title, message = '', duration = Config.TOAST_DURATION) {
    const container = _ensureContainer();

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };

    const toast = DOM.create('div', {
      className: `toast toast-${type}`,
    }, [
      DOM.create('div', { className: 'toast-icon' }, icons[type] || 'ℹ️'),
      DOM.create('div', { className: 'toast-body' }, [
        DOM.create('div', { className: 'toast-title' }, title),
        message ? DOM.create('div', { className: 'toast-message' }, message) : null,
      ].filter(Boolean)),
      DOM.create('button', {
        className: 'toast-close',
        onClick() { remove(toast); },
      }, '×'),
    ]);

    container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => remove(toast), duration);
    }

    return toast;
  }

  function remove(toast) {
    DOM.addClass(toast, 'removing');
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
      // 清理空容器
      if (_container && _container.children.length === 0) {
        _container.remove();
        _container = null;
      }
    }, 200);
  }

  function success(title, message = '') { return show('success', title, message); }
  function error(title, message = '') { return show('error', title, message); }
  function warning(title, message = '') { return show('warning', title, message); }
  function info(title, message = '') { return show('info', title, message); }

  return { show, success, error, warning, info };
})();
