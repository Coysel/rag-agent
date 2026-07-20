/**
 * 检索对比页面
 *
 * 对比三种检索器 (BM25 / Dense / Hybrid) 的结果
 */

const RetrievalPage = {
  _loading: false,

  init() {
    const searchBtn = DOM.$('#retrieval-search-btn');
    const input = DOM.$('#retrieval-input');

    if (searchBtn) {
      searchBtn.addEventListener('click', () => this.search());
    }

    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') this.search();
      });
    }
  },

  async search() {
    const input = DOM.$('#retrieval-input');
    const query = input?.value.trim();
    if (!query || this._loading) return;

    this._loading = true;
    Store.setState({ retrievalQuery: query, retrievalLoading: true });

    const container = DOM.$('#retrieval-results');
    if (container) {
      DOM.setHTML(container, '<div style="text-align:center;padding:40px"><div class="spinner spinner-lg" style="margin:0 auto"></div><p style="margin-top:12px;color:var(--text-tertiary)">检索中...</p></div>');
    }

    try {
      const data = await EvalAPI.compareRetrieval(query);
      Store.setState({ retrievalResults: data, retrievalLoading: false });
      this._render(data);
    } catch (err) {
      Store.setState({ retrievalLoading: false });
      Toast.error('检索失败', err.message);
      if (container) {
        DOM.setHTML(container, `<div class="empty-state"><div class="empty-state-icon">❌</div><div class="empty-state-title">检索失败</div><div class="empty-state-desc">${DOM.escapeHTML(err.message)}</div></div>`);
      }
    }

    this._loading = false;
  },

  _render(data) {
    const container = DOM.$('#retrieval-results');
    if (!container) return;

    DOM.empty(container);

    const methods = [
      { key: 'bm25', name: 'BM25', desc: '关键词匹配', icon: '🔤', colorClass: 'bm25' },
      { key: 'dense', name: 'Dense', desc: '语义向量', icon: '🧠', colorClass: 'dense' },
      { key: 'hybrid', name: 'Hybrid', desc: 'RRF 混合', icon: '🔀', colorClass: 'hybrid' },
    ];

    // ── 汇总统计 ────────────────────────────────────────────
    const stats = methods.map(m => {
      const result = data[m.key];
      const docs = result?.docs || [];
      const avgScore = docs.length > 0
        ? docs.reduce((s, d) => s + (d.score || 0), 0) / docs.length
        : 0;
      return {
        ...m,
        count: docs.length,
        avgScore,
        latency: result?.latency || 0,
        best: false,
      };
    });

    // 标记最优
    const maxCount = Math.max(...stats.map(s => s.count), 0);
    const maxScore = Math.max(...stats.map(s => s.avgScore), 0);
    stats.forEach(s => {
      s.bestCount = s.count === maxCount && s.count > 0;
      s.bestScore = s.avgScore === maxScore && s.avgScore > 0;
    });

    // 渲染汇总条
    const summaryRow = DOM.create('div', { className: 'retrieval-summary' });
    stats.forEach(s => {
      const item = DOM.create('div', {
        className: 'retrieval-summary-item' + (s.bestScore ? ' best' : ''),
      });
      item.innerHTML = `
        <div class="retrieval-summary-label">${s.icon} ${s.name} · ${s.desc}</div>
        <div class="retrieval-summary-value">${s.count} 篇</div>
        <div class="retrieval-summary-sub">
          均分 ${Format.score(s.avgScore)} · ⏱ ${Format.duration(s.latency * 1000)}
        </div>
        ${s.bestScore ? '<div class="best-badge">🏆 最高分</div>' : ''}
        ${s.bestCount && !s.bestScore ? '<div class="best-badge">📋 最多结果</div>' : ''}
      `;
      summaryRow.appendChild(item);
    });
    container.appendChild(summaryRow);

    // ── 对比卡片 ────────────────────────────────────────────
    const grid = DOM.create('div', { className: 'retrieval-compare' });

    stats.forEach(s => {
      const result = data[s.key];
      const docs = result?.docs || [];

      const card = DOM.create('div', { className: 'retriever-card' });

      // Header
      const header = DOM.create('div', {
        className: `retriever-card-header ${s.colorClass}`,
      });
      header.innerHTML = `
        <span class="retriever-card-name">
          <span class="retriever-card-icon">${s.icon}</span> ${s.name}
          <span class="retriever-card-badge ${s.colorClass}">${s.desc}</span>
        </span>
        <span style="font-size:var(--text-xs);color:var(--text-tertiary)">⏱ ${Format.duration(s.latency * 1000)}</span>
      `;
      card.appendChild(header);

      // Body
      const body = DOM.create('div', { className: 'retriever-card-body' });

      if (docs.length === 0) {
        body.appendChild(DOM.create('div', { className: 'retrieval-doc-empty' }, [
          DOM.create('div', { className: 'retrieval-doc-empty-icon' }, '📭'),
          DOM.create('div', {}, '无匹配结果'),
        ]));
      } else {
        docs.forEach((doc, i) => {
          const score = doc.score || 0;
          const level = Format.scoreLevel(score);
          const scoreCls = level === 'high' ? 'score-high' : level === 'medium' ? 'score-medium' : 'score-low';
          const scorePct = Math.round(Math.min(score, 1) * 100);

          const item = DOM.create('div', { className: 'retrieval-doc-item' });
          item.innerHTML = `
            <div class="retrieval-doc-header">
              <span class="retrieval-doc-rank">#${i + 1}</span>
              <span class="retrieval-doc-title" title="${DOM.escapeHTML(doc.title || '未知')}">${DOM.escapeHTML(doc.title || '未知')}</span>
              <span class="retrieval-doc-score" style="color:var(--${level === 'high' ? 'success' : level === 'medium' ? 'warning' : 'error'})">${Format.score(score)}</span>
            </div>
            <div class="retrieval-score-bar">
              <div class="retrieval-score-bar-fill ${scoreCls}" style="width:${scorePct}%"></div>
            </div>
            ${doc.content ? `
              <div class="retrieval-doc-preview">${DOM.escapeHTML(doc.content.slice(0, 200))}</div>
            ` : ''}
            ${doc.source ? `
              <div style="font-size:10px;color:var(--text-tertiary);margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">📄 ${DOM.escapeHTML(doc.source)}</div>
            ` : ''}
          `;
          body.appendChild(item);
        });
      }

      card.appendChild(body);
      grid.appendChild(card);
    });

    container.appendChild(grid);
  },
};
