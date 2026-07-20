/**
 * Tab 导航组件
 *
 * 用法:
 *   Tabs.init();  // 自动绑定所有 .tab-btn 的点击事件
 *   Tabs.switchTo('eval');  // 程序化切换
 */

const Tabs = {
  /**
   * 初始化 Tab 导航
   */
  init() {
    DOM.$$('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        if (tab) this.switchTo(tab);
      });
    });
  },

  /**
   * 切换到指定 Tab
   * @param {string} tabName - 'chat' | 'retrieval' | 'eval' | 'admin' | 'settings'
   */
  switchTo(tabName) {
    // 更新按钮状态
    DOM.$$('.tab-btn').forEach(btn => {
      DOM.toggleClass(btn, 'active', btn.dataset.tab === tabName);
    });

    // 更新页面显示
    DOM.$$('.page').forEach(page => {
      DOM.toggleClass(page, 'active', page.dataset.page === tabName);
    });

    // 更新状态
    Store.setState({ currentTab: tabName });

    // Tab 切换时的初始化逻辑
    if (tabName === 'admin') {
      if (typeof AdminPage !== 'undefined') AdminPage.loadDocuments();
    }

    // 切换 Tab 时管理输入栏显示
    const inputBar = DOM.$('.input-bar');
    if (inputBar) {
      DOM.toggle(inputBar, tabName === 'chat');
    }
  },
};
