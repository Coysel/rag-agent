/**
 * 简易 Markdown 渲染器
 *
 * 支持: 代码块 (```), 行内代码 (`), 粗体 (**), 斜体 (*),
 *       链接, 无序列表, 有序列表, 标题, 引用, 水平线
 */

const Markdown = {
  /**
   * 渲染 Markdown 文本为 HTML
   * @param {string} text
   * @returns {string} HTML 字符串
   */
  render(text) {
    if (!text) return '';

    let html = text;

    // 1. 代码块 (```language\n code \n```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
      const escaped = DOM.escapeHTML(code.trimEnd());
      return `<pre><code class="language-${lang}">${escaped}</code></pre>`;
    });

    // 2. 行内代码 (`code`)
    html = html.replace(/`([^`]+)`/g, (_, code) => {
      return `<code>${DOM.escapeHTML(code)}</code>`;
    });

    // 3. 粗体 (**text**)
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // 4. 斜体 (*text*) — 注意不要匹配列表的 *
    html = html.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>');

    // 5. 链接 [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // 6. 图片 ![alt](url)
    html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" loading="lazy">');

    // 7. 标题 (### Heading) — 先处理防止 # 被误匹配
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // 8. 引用 (> text)
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
    html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

    // 9. 水平线 (---)
    html = html.replace(/^---+$/gm, '<hr>');

    // 10. 无序列表 — 处理连续的行
    html = html.replace(/((?:^[\-\*] .+\n?)+)/gm, (match) => {
      const items = match.trim().split('\n')
        .map(line => line.replace(/^[\-\*] /, ''))
        .map(item => `<li>${item}</li>`)
        .join('');
      return `<ul>${items}</ul>`;
    });

    // 11. 有序列表
    html = html.replace(/((?:^\d+\. .+\n?)+)/gm, (match) => {
      const items = match.trim().split('\n')
        .map(line => line.replace(/^\d+\. /, ''))
        .map(item => `<li>${item}</li>`)
        .join('');
      return `<ol>${items}</ol>`;
    });

    // 12. 段落 — 连续非空行合并为 <p>
    html = html.replace(/\n\n+/g, '</p><p>');
    html = `<p>${html}</p>`;

    // 清理空段落
    html = html.replace(/<p>\s*<\/p>/g, '');
    html = html.replace(/<p>\s*(<[huo])/g, '$1');
    html = html.replace(/(<\/[huo][^>]*>)\s*<\/p>/g, '$1');

    return html;
  },

  /**
   * 渲染纯文本（去除 Markdown 标记）
   * @param {string} text
   * @returns {string}
   */
  strip(text) {
    if (!text) return '';
    return text
      .replace(/```[\s\S]*?```/g, '[代码块]')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/\*([^*\n]+)\*/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/[#>\-\*]/g, '')
      .trim();
  },
};
