# Transformer 与 Self-Attention 机制详解

## Transformer 架构概述

Transformer 是 2017 年由 Vaswani 等人在 "Attention Is All You Need" 论文中提出的神经网络架构。它完全基于注意力机制，摒弃了传统的循环和卷积结构，在 NLP 和 CV 领域都取得了革命性的成功。

## Self-Attention 核心原理

Self-Attention（自注意力）允许模型在处理序列中的每个元素时，关注序列中的所有其他元素。

### 计算步骤

1. **生成 Q、K、V 向量**：对每个输入 token，通过三个不同的线性变换生成：
   - Q (Query): 查询向量，表示"我在找什么"
   - K (Key): 键向量，表示"我包含什么信息"
   - V (Value): 值向量，表示"我的实际内容"

2. **计算注意力分数**：Query 与所有 Key 做点积
   ```
   Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V
   ```

3. **缩放 (Scaling)**：除以 sqrt(d_k) 防止点积值过大导致 softmax 梯度消失。d_k 是 Key 向量的维度。

4. **Softmax 归一化**：将分数转换为概率分布（权重）。

5. **加权求和**：用注意力权重对 Value 向量加权求和，得到最终输出。

## Multi-Head Attention（多头注意力）

多头注意力通过并行运行多个 Self-Attention "头"，每个头关注不同的表示子空间：

```
MultiHead(Q, K, V) = Concat(head_1, ..., head_h) * W_O

其中 head_i = Attention(Q*W_i^Q, K*W_i^K, V*W_i^V)
```

## 为什么 Self-Attention 比 RNN 更好

- **并行计算**：不需要像 RNN 那样顺序处理，可以并行计算所有位置
- **长距离依赖**：直接连接任意两个位置（O(1) 路径长度），RNN 需要 O(n)
- **可解释性**：注意力权重可以直接可视化，展示模型"关注"的位置

## 位置编码 (Positional Encoding)

由于 Self-Attention 本身不包含位置信息，需要加入位置编码：

```
PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
```
