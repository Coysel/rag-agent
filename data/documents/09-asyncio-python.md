# Python asyncio 异步编程

## asyncio.run()

`asyncio.run()` 是 Python 3.7 引入的核心函数，用于运行异步协程。

```python
import asyncio

async def main():
    await asyncio.sleep(1)
    return "done"

# Python 3.7+
result = asyncio.run(main())
```

### 主要作用

1. 创建事件循环 (event loop)
2. 运行传入的协程
3. 完成后关闭事件循环
4. 返回协程的执行结果

### Python 3.7 之前的方式

```python
# Python 3.6 及之前需要手动管理事件循环
loop = asyncio.get_event_loop()
try:
    result = loop.run_until_complete(main())
finally:
    loop.close()
```

`asyncio.run()` 简化了这个流程，成为推荐的异步程序入口。

## 核心概念

- **coroutine**：async def 定义的函数，调用时返回 coroutine 对象
- **await**：等待一个协程完成，让出控制权
- **Task**：将协程包装为 Task 后并发执行
- **gather**：并发运行多个协程并收集结果

## 在 RAG 系统中的应用

asyncio 在 Agentic RAG 中的关键应用：
- ReAct 循环中每个步骤的异步执行
- 多个检索器（BM25 + Dense）的并发调用
- SSE 流式输出的异步推送
