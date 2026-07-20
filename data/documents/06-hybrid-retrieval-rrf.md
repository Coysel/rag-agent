# 混合检索与 RRF 融合算法

## 为什么需要混合检索

在 RAG 系统中，单一检索方式都有其局限性：

### BM25 稀疏检索

**优势**：
- 精确词匹配能力强，搜索专用术语/API 名时准确率极高
- 计算快速，不需要 GPU
- 基于统计，可解释性强

**劣势**：
- 无法理解语义，搜"卷积"找不到只写"convolution"的文档
- 无法处理同义词和近义表达
- 对长文本查询表现较差

### Dense 语义检索（向量检索）

**优势**：
- 语义理解强，能匹配同义词和近义表达
- 搜"图像分类"能找到"image classification"相关文档
- 支持多语言跨语言检索

**劣势**：
- 精确术语匹配可能不如 BM25
- 需要 Embedding 模型，计算成本较高
- 对专有名词/缩写可能效果不好

## RRF (Reciprocal Rank Fusion) 融合算法

### 为什么用 RRF 而不是直接加权？

核心问题：两种检索器的分数值域不同。

- BM25 分数：无上界（理论上可以是任意正数）
- 余弦相似度：[-1, 1]
- 直接加权需要先归一化，但归一化方法（min-max 等）受极端值影响大

RRF 巧妙地用**排名代替分数**，绕过了值域问题。

### RRF 公式

```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```

对每个检索器 i：
- d 是文档
- rank_i(d) 是文档在检索器 i 中的排名（从 1 开始）
- k 是平滑常数，通常取 60（来自原论文）

### 核心代码（约 10 行）

```python
def reciprocal_rank_fusion(dense_results, sparse_results, k=60):
    scores = {}
    merged = {}

    for rank, (doc, _) in enumerate(dense_results, 1):
        key = doc["id"]
        scores[key] = scores.get(key, 0) + 1 / (k + rank)
        merged[key] = doc

    for rank, (doc, _) in enumerate(sparse_results, 1):
        key = doc["id"]
        scores[key] = scores.get(key, 0) + 1 / (k + rank)
        merged[key] = doc

    ranked = sorted(scores, key=scores.get, reverse=True)
    return [merged[key] for key in ranked]
```

### k 常数的作用

k 用于平滑排名差异。当 k=60 时：
- rank=1 贡献: 1/61 ≈ 0.0164
- rank=10 贡献: 1/70 ≈ 0.0143
- rank=100 贡献: 1/160 ≈ 0.0063

较小的 k 让高排名文档权重更大，较大的 k 让排名差异影响更小。

## 参考

Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009). "Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods." SIGIR 2009.
