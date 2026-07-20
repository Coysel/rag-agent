/**
 * SSE (Server-Sent Events) 流解析器 — 基于 ReadableStream
 *
 * 所有 SSE 端点共用此解析器。
 *
 * 用法:
 *   const response = await fetch('/chat', { method: 'POST', body: ... });
 *   SSEStream.stream(response, {
 *     reason(data) { ... },
 *     answer(data) { ... },
 *     done(data) { ... },
 *     error(data) { ... },
 *     _streamEnd() { ... },   // 流结束回调
 *   });
 */

const SSEStream = {
  /**
   * 解析 SSE 流并分发事件
   * @param {Response} response - fetch 返回的 Response 对象
   * @param {Object} handlers - 事件处理器对象 { eventName: handler(data), '*': (event, data), _streamEnd: () }
   * @returns {Promise<void>}
   */
  async stream(response, handlers = {}) {
    if (!response.ok) {
      if (handlers.error) {
        handlers.error({ message: `HTTP ${response.status}: ${response.statusText}` });
      }
      if (handlers._streamEnd) handlers._streamEnd();
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    function processLines() {
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      let eventType = '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let parsed = null;
          try {
            parsed = JSON.parse(raw);
          } catch (e) {
            // 非 JSON 数据，当作纯文本
            parsed = { text: raw };
          }

          if (parsed != null) {
            if (handlers[eventType]) {
              handlers[eventType](parsed);
            } else if (handlers['*']) {
              handlers['*'](eventType, parsed);
            }
          }
        }
      }
    }

    function pump() {
      reader.read().then(({ done, value }) => {
        // 先处理 value（最后一帧可能同时有 done=true 和 value）
        if (value && value.length) {
          buffer += decoder.decode(value, { stream: true });
          processLines();
        }

        if (done) {
          // 流结束，清空 buffer 中剩余数据
          if (buffer.trim()) {
            processLines();
          }
          if (handlers._streamEnd) handlers._streamEnd();
          return;
        }

        pump();
      }).catch(e => {
        if (handlers.error) handlers.error({ message: `SSE 流错误: ${e.message}` });
        if (handlers._streamEnd) handlers._streamEnd();
      });
    }

    pump();
  },
};
