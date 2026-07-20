/**
 * DOM 操作辅助工具
 *
 * 提供简短的 DOM 查询和创建 API，减少原生 API 的样板代码
 */

const DOM = {
  /**
   * 查询单个元素
   * @param {string} selector - CSS 选择器
   * @param {Element} [parent=document] - 父元素
   */
  $(selector, parent) {
    return (parent || document).querySelector(selector);
  },

  /**
   * 查询所有匹配元素
   * @param {string} selector - CSS 选择器
   * @param {Element} [parent=document] - 父元素
   */
  $$(selector, parent) {
    return Array.from((parent || document).querySelectorAll(selector));
  },

  /**
   * 创建元素并设置属性/内容
   * @param {string} tag - HTML 标签名
   * @param {Object} [attrs={}] - 属性对象 {className, id, textContent, ...}
   * @param {(string|Node|Node[])} [children] - 子节点
   * @returns {HTMLElement}
   */
  create(tag, attrs = {}, children) {
    const el = document.createElement(tag);
    for (const [key, val] of Object.entries(attrs)) {
      if (key === 'className') {
        el.className = val;
      } else if (key === 'dataset') {
        Object.assign(el.dataset, val);
      } else if (key === 'style' && typeof val === 'object') {
        Object.assign(el.style, val);
      } else if (key.startsWith('on') && typeof val === 'function') {
        el.addEventListener(key.slice(2).toLowerCase(), val);
      } else if (key === 'html') {
        el.innerHTML = val;
      } else {
        el.setAttribute(key, val);
      }
    }
    if (children !== undefined) {
      if (typeof children === 'string') {
        el.textContent = children;
      } else if (Array.isArray(children)) {
        children.forEach(c => c && el.appendChild(
          typeof c === 'string' ? document.createTextNode(c) : c
        ));
      } else if (children instanceof Node) {
        el.appendChild(children);
      }
    }
    return el;
  },

  /**
   * 清空元素的所有子节点
   */
  empty(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
    return el;
  },

  /**
   * 安全设置 innerHTML（先清空）
   */
  setHTML(el, html) {
    el.innerHTML = html;
    return el;
  },

  /**
   * 显示/隐藏元素
   */
  show(el) { el.style.display = ''; return el; },
  hide(el) { el.style.display = 'none'; return el; },
  toggle(el, force) {
    if (force !== undefined) {
      el.style.display = force ? '' : 'none';
    } else {
      el.style.display = el.style.display === 'none' ? '' : 'none';
    }
    return el;
  },

  /**
   * 添加/移除/切换 CSS 类
   */
  addClass(el, ...classes) { el.classList.add(...classes); return el; },
  removeClass(el, ...classes) { el.classList.remove(...classes); return el; },
  toggleClass(el, cls, force) {
    el.classList.toggle(cls, force);
    return el;
  },

  /**
   * 滚动到元素位置
   */
  scrollTo(el, opts = {}) {
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest', ...opts });
    return el;
  },

  /**
   * 检查元素是否滚动到接近底部
   * @param {Element} el
   * @param {number} [threshold=100]
   */
  isNearBottom(el, threshold = 100) {
    return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  },

  /**
   * 滚动到底部
   */
  scrollToBottom(el) {
    el.scrollTop = el.scrollHeight;
    return el;
  },

  /**
   * 转义 HTML（防 XSS）
   */
  escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },

  /**
   * 防抖
   */
  debounce(fn, delay = 300) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  },

  /**
   * 节流
   */
  throttle(fn, interval = 100) {
    let last = 0;
    return function (...args) {
      const now = Date.now();
      if (now - last >= interval) {
        last = now;
        fn.apply(this, args);
      }
    };
  },
};
