/**
 * 评测页面 — RAGAS 评测 + 自定义评测
 */

const EvalPage = {
  _loading: false,

  init() {
    const ragasBtn = DOM.$('#eval-ragas-btn');
    const customBtn = DOM.$('#eval-custom-btn');
    const countInput = DOM.$('#eval-count');

    if (ragasBtn) {
      ragasBtn.addEventListener('click', () => {
        const count = parseInt(countInput?.value) || 5;
        this.startRagas(count);
      });
    }

    if (customBtn) {
      customBtn.addEventListener('click', () => this.startCustom());
    }
  },

  /** RAGAS 预设评测 */
  async startRagas(count) {
    if (this._loading) return;
    this._loading = true;
    Store.setState({ evalLoading: true, evalResults: [] });

    // 显示进度条并清空旧结果
    const progressEl = DOM.$('#eval-progress');
    if (progressEl) DOM.show(progressEl);
    DOM.empty(DOM.$('#eval-results'));
    DOM.empty(DOM.$('#eval-summary'));
    this._showProgress('准备 RAGAS 评测...', 0);

    try {
      const response = await EvalAPI.startRagasEval(count);

      SSEStream.stream(response, {
        progress: (data) => {
          Store.setState({ evalProgress: data });
          this._showProgress(
            `[${data.phase === 'dense' ? '纯 Dense' : '混合检索'}] ${data.question}`,
            Math.round((data.current / data.total) * 100)
          );
        },
        done: (data) => {
          Store.setState({ evalLoading: false, evalResults: data });
          try {
            this._renderResults(data);
            // RAGAS 也渲染汇总摘要
            if (data.summary) {
              this._renderSummary(data.summary);
            }
          } catch (e) {
            console.error('[Eval] _renderResults error:', e);
            Toast.error('渲染结果失败', e.message);
          }
        },
        error: (data) => {
          Store.setState({ evalLoading: false });
          Toast.error('评测出错', data.message || '');
        },
        _streamEnd: () => {
          Store.setState({ evalLoading: false });
          this._loading = false;
          // 隐藏进度条
          const pEl = DOM.$('#eval-progress');
          if (pEl) DOM.hide(pEl);
        },
      });
    } catch (err) {
      Store.setState({ evalLoading: false });
      this._loading = false;
      Toast.error('评测失败', err.message);
    }
  },

  /** 自定义评测 */
  async startCustom() {
    const textarea = DOM.$('#eval-custom-questions');
    const questions = textarea?.value.split('\n').filter(q => q.trim());
    if (!questions || questions.length === 0) {
      Toast.warning('请输入问题', '每行一个问题');
      return;
    }

    if (this._loading) return;
    this._loading = true;
    Store.setState({ evalLoading: true, evalResults: [] });

    // 显示进度条并清空旧结果
    const progressEl = DOM.$('#eval-progress');
    if (progressEl) DOM.show(progressEl);
    DOM.empty(DOM.$('#eval-results'));
    DOM.empty(DOM.$('#eval-summary'));
    this._showProgress('开始自定义评测...', 0);

    try {
      const response = await EvalAPI.startCustomEval(questions);

      SSEStream.stream(response, {
        progress: (data) => {
          Store.setState({ evalProgress: data });
          this._showProgress(
            `${data.question}`,
            Math.round((data.current / data.total) * 100)
          );
        },
        result: (data) => {
          const results = Store.get('evalResults');
          results.push(data);
          Store.setState({ evalResults: results });
        },
        done: (data) => {
          Store.setState({ evalLoading: false, evalResults: data });
          try {
            if (data.summary) {
              this._renderSummary(data.summary);
            }
          } catch (e) {
            console.error('[Eval] _renderSummary error:', e);
          }
        },
        error: (data) => {
          Store.setState({ evalLoading: false });
          Toast.error('评测出错', data.message || '');
        },
        _streamEnd: () => {
          Store.setState({ evalLoading: false });
          this._loading = false;
          const pEl = DOM.$('#eval-progress');
          if (pEl) DOM.hide(pEl);
        },
      });
    } catch (err) {
      Store.setState({ evalLoading: false });
      this._loading = false;
      Toast.error('评测失败', err.message);
    }
  },

  _showProgress(text, pct) {
    const el = DOM.$('#eval-progress-text');
    const bar = DOM.$('#eval-progress-bar');
    if (el) el.textContent = text;
    if (bar) bar.style.width = `${pct}%`;
  },

  _renderResults(data) {
    const container = DOM.$('#eval-results');
    if (!container) return;
    DOM.empty(container);

    // 汇总仪表盘
    if (data.summary) {
      container.appendChild(this._buildDashboard(data.summary));
    }

    // 逐条结果表
    if (data.per_question) {
      container.appendChild(this._buildTable(data.per_question));
    }
  },

  _buildDashboard(summary) {
    const dashboard = DOM.create('div', { className: 'metrics-dashboard' });

    const metricNames = ['faithfulness', 'answer_relevance', 'context_precision', 'context_recall'];

    metricNames.forEach(name => {
      // 只显示 hybrid 的指标
      if (summary.hybrid_avg && summary.hybrid_avg[name] !== undefined) {
        const val = summary.hybrid_avg[name];
        const labels = {
          faithfulness: '忠实度',
          answer_relevance: '相关性',
          context_precision: '精度',
          context_recall: '召回',
        };

        dashboard.appendChild(DOM.create('div', { className: 'metric-card' }, [
          DOM.create('div', { className: 'metric-label' }, labels[name] || name),
          this._buildRing(val),
          summary.improvements?.[name]
            ? DOM.create('div', { style: `font-size:10px;color:${summary.improvements[name].improvement_pct > 0 ? 'var(--success)' : 'var(--error)'}` },
                `${summary.improvements[name].improvement_pct > 0 ? '↑' : '↓'} ${Math.abs(summary.improvements[name].improvement_pct)}%`)
            : null,
        ].filter(Boolean)));
      }
    });

    return dashboard;
  },

  _buildRing(value) {
    const pct = Math.round(value * 100);
    const color = value >= 0.7 ? 'var(--success)' : value >= 0.4 ? 'var(--warning)' : 'var(--error)';
    const circumference = 2 * Math.PI * 30; // r=30

    const wrapper = DOM.create('div', { className: 'metric-ring' });
    wrapper.innerHTML = `
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle class="metric-ring-bg" cx="36" cy="36" r="30"/>
        <circle class="metric-ring-fill" cx="36" cy="36" r="30"
                stroke="${color}"
                stroke-dasharray="${circumference}"
                stroke-dashoffset="${circumference * (1 - value)}"/>
      </svg>
      <div class="metric-ring-value">${pct}%</div>
    `;
    return wrapper;
  },

  _buildTable(perQuestion) {
    const wrapper = DOM.create('div', { className: 'eval-table' });
    const table = document.createElement('table');

    table.innerHTML = `
      <thead>
        <tr>
          <th>问题</th>
          <th>类型</th>
          <th>Dense<br>忠实度</th>
          <th>Hybrid<br>忠实度</th>
          <th>Dense<br>相关性</th>
          <th>Hybrid<br>相关性</th>
        </tr>
      </thead>
      <tbody>
        ${perQuestion.map(q => `
          <tr>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${DOM.escapeHTML(q.question)}">${DOM.escapeHTML(q.question)}</td>
            <td><span class="badge badge-neutral">${q.query_type || '-'}</span></td>
            <td class="metric-cell ${q.dense.faithfulness >= 0.7 ? 'metric-good' : q.dense.faithfulness >= 0.4 ? 'metric-mid' : 'metric-poor'}">${Format.score(q.dense.faithfulness)}</td>
            <td class="metric-cell ${q.hybrid.faithfulness >= 0.7 ? 'metric-good' : q.hybrid.faithfulness >= 0.4 ? 'metric-mid' : 'metric-poor'}">${Format.score(q.hybrid.faithfulness)}</td>
            <td class="metric-cell ${q.dense.answer_relevance >= 0.7 ? 'metric-good' : q.dense.answer_relevance >= 0.4 ? 'metric-mid' : 'metric-poor'}">${Format.score(q.dense.answer_relevance)}</td>
            <td class="metric-cell ${q.hybrid.answer_relevance >= 0.7 ? 'metric-good' : q.hybrid.answer_relevance >= 0.4 ? 'metric-mid' : 'metric-poor'}">${Format.score(q.hybrid.answer_relevance)}</td>
          </tr>
        `).join('')}
      </tbody>
    `;

    wrapper.appendChild(table);
    return wrapper;
  },

  _renderSummary(summary) {
    const el = DOM.$('#eval-summary');
    if (!el) return;
    DOM.empty(el);

    // RAGAS 格式: { dense_avg, hybrid_avg, improvements }
    // Custom 格式: { avg_faithfulness, avg_answer_relevance, ... }
    const isRagas = !!(summary.hybrid_avg && summary.dense_avg);
    const metrics = isRagas
      ? [
          { key: 'faithfulness', label: '忠实度' },
          { key: 'answer_relevance', label: '相关性' },
          { key: 'context_precision', label: '精度' },
          { key: 'context_recall', label: '召回' },
        ].map(m => ({
          ...m,
          dense: summary.dense_avg[m.key],
          hybrid: summary.hybrid_avg[m.key],
          improvement: summary.improvements?.[m.key]?.improvement_pct,
        }))
      : [
          { key: 'avg_faithfulness', label: '忠实度', value: summary.avg_faithfulness },
          { key: 'avg_answer_relevance', label: '相关性', value: summary.avg_answer_relevance },
          { key: 'avg_context_precision', label: '精度', value: summary.avg_context_precision },
          { key: 'avg_context_recall', label: '召回', value: summary.avg_context_recall },
        ];

    const grid = DOM.create('div', {
      style: 'display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px',
    });

    metrics.forEach(m => {
      if (isRagas) {
        // Dual-bar comparison card
        const card = DOM.create('div', { className: 'metric-card' });
        card.innerHTML = `
          <div class="metric-label">${m.label}</div>
          <div style="display:flex;gap:8px;align-items:flex-end;justify-content:center;margin:8px 0">
            <div style="text-align:center">
              <div style="font-size:10px;color:var(--text-tertiary);margin-bottom:2px">Dense</div>
              <div style="font-size:var(--text-lg);font-weight:var(--weight-bold);color:var(--text-secondary)">${Format.score(m.dense)}</div>
            </div>
            <div style="text-align:center">
              <div style="font-size:10px;color:var(--text-tertiary);margin-bottom:2px">Hybrid</div>
              <div style="font-size:var(--text-xl);font-weight:var(--weight-bold);color:var(--primary)">${Format.score(m.hybrid)}</div>
            </div>
          </div>
          ${m.improvement !== undefined ? `
            <div style="font-size:10px;color:${m.improvement > 0 ? 'var(--success)' : m.improvement < 0 ? 'var(--error)' : 'var(--text-tertiary)'}">
              ${m.improvement > 0 ? '↑' : m.improvement < 0 ? '↓' : '—'} ${Math.abs(m.improvement)}%
            </div>
          ` : ''}
        `;
        grid.appendChild(card);
      } else {
        // Simple value card (custom eval)
        const card = DOM.create('div', { className: 'metric-card' });
        card.innerHTML = `
          <div class="metric-label">${m.label}</div>
          <div style="font-size:var(--text-xl);font-weight:var(--weight-bold);color:var(--primary)">${Format.score(m.value)}</div>
        `;
        grid.appendChild(card);
      }
    });

    el.appendChild(grid);
  },
};
