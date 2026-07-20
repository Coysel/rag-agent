# tiktoken — Token 估算工具

## 概述

tiktoken 是 OpenAI 开源的快速分词库，用于将文本转换为 token 并估算 token 数量。

## 支持的编码

| 编码名称 | 对应模型 |
|---------|---------|
| cl100k_base | GPT-4, GPT-3.5-turbo, text-embedding-ada-002 |
| p50k_base | GPT-3 Codex (code-davinci-002) |
| r50k_base | GPT-3 Davinci |
| o200k_base | GPT-4o |

**cl100k_base** 是最常用的编码，几乎所有现代 OpenAI 和 Anthropic 模型都使用类似的 tokenization 方式。

## 基本用法

```python
import tiktoken

# 获取编码器
enc = tiktoken.get_encoding("cl100k_base")

# 编码为 token
tokens = enc.encode("Hello, world!")
print(len(tokens))  # 4

# 估算 token 数
num_tokens = len(enc.encode("这是一段中文文本"))
```

## 在 RAG 中的应用：动态截断

tiktoken 在 RAG 系统中用于预估 Token 用量，实现动态截断：

```python
def truncate_context(docs, max_tokens=8000):
    """tiktoken 预估 + 动态截断低相关文档"""
    enc = tiktoken.get_encoding("cl100k_base")
    selected = []
    total = 0

    # 按相关度排序
    for doc in sorted(docs, key=lambda d: d["score"], reverse=True):
        tokens = len(enc.encode(doc["content"]))
        if total + tokens <= max_tokens:
            selected.append(doc)
            total += tokens
        else:
            break  # 低相关度文档被截断

    return selected
```

这个策略确保：
- 高相关文档优先保留
- 总 token 数不超过模型上下文窗口
- 低相关文档自动被截断，不占用宝贵的上下文空间
