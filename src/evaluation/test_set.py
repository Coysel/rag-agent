"""
RAGAS 评估测试集 — 20 条测试问题 + 标准答案

覆盖三种查询类型:
  - factual (事实查询): 精确的事实/参数/API 信息
  - conceptual (概念解释): 概念、原理、方法的解释
  - multi_hop (多步推理): 需要综合多个信息源的比较/推理问题
"""

from dataclasses import dataclass
from typing import List


@dataclass
class TestQuestion:
    """测试问题"""
    id: str
    question: str
    ground_truth: str
    query_type: str  # "factual" | "conceptual" | "multi_hop"


TEST_QUESTIONS: List[TestQuestion] = [
    # ── 事实查询 (factual) ────────────────────────────────
    TestQuestion(
        id="F001",
        question="PyTorch 中 Conv2d 的默认参数有哪些？stride 和 padding 的默认值是什么？",
        ground_truth="PyTorch 的 nn.Conv2d 主要参数包括: in_channels (输入通道数), out_channels (输出通道数), kernel_size (卷积核大小)。stride 默认为 1，padding 默认为 0。其他参数包括 dilation (默认为 1), groups (默认为 1), bias (默认为 True), padding_mode (默认为 'zeros')。",
        query_type="factual",
    ),
    TestQuestion(
        id="F002",
        question="Python 的 asyncio.run() 函数是在哪个版本引入的？它的主要作用是什么？",
        ground_truth="asyncio.run() 在 Python 3.7 中引入。它的主要作用是创建一个事件循环，运行一个异步协程，并在完成后关闭事件循环。它简化了异步程序的入口编写，替代了之前需要手动获取/创建/关闭事件循环的繁琐流程。",
        query_type="factual",
    ),
    TestQuestion(
        id="F003",
        question="Claude API 中 max_tokens 参数的默认值和最大值分别是多少？",
        ground_truth="Claude API 中 max_tokens 参数需要显式指定，没有默认值。最大值取决于具体模型: Claude Opus 4 支持最高 32000 tokens 输出，Claude Sonnet 4 支持最高 32000 tokens 输出。必须设置 max_tokens 参数，否则 API 会返回错误。",
        query_type="factual",
    ),
    TestQuestion(
        id="F004",
        question="ChromaDB 支持哪些距离度量方式？默认使用哪种？",
        ground_truth="ChromaDB 支持三种距离度量方式: 'l2' (欧几里得距离)、'ip' (内积)、'cosine' (余弦距离)。默认使用 'l2'，但可以通过 metadata 中的 'hnsw:space' 参数来指定，常用的设置为 'cosine'。",
        query_type="factual",
    ),
    TestQuestion(
        id="F005",
        question="LangGraph 中 StateGraph 的三个核心概念是什么？分别有什么作用？",
        ground_truth="LangGraph 中 StateGraph 的三个核心概念是: State (状态) — 定义图中流转的数据结构，使用 TypedDict 定义字段并可通过 reducer 控制更新逻辑；Node (节点) — 处理状态的函数，接收当前 State 并返回部分更新；Edge (边) — 连接节点，分为普通边(固定路由)和条件边(根据 State 动态路由)。",
        query_type="factual",
    ),
    TestQuestion(
        id="F006",
        question="RRF 融合算法中 k 常数的作用是什么？通常设为多少？",
        ground_truth="RRF (Reciprocal Rank Fusion) 中的 k 是平滑常数，用于降低极高排名和极低排名之间的差异。通常设为 60 (来自原论文的实验结果)。k 的作用是防止 1/rank 在 rank=1 时对结果影响过大，使得融合更稳定。",
        query_type="factual",
    ),
    TestQuestion(
        id="F007",
        question="tiktoken 库支持哪些编码模型？用于估算 GPT 系列模型的是什么编码？",
        ground_truth="tiktoken 支持多种编码: cl100k_base (GPT-4/GPT-3.5-turbo/text-embedding-ada-002 使用), p50k_base (GPT-3 Codex 使用), r50k_base (GPT-3 Davinci 使用), o200k_base (GPT-4o 使用)。cl100k_base 是最常用的。",
        query_type="factual",
    ),

    # ── 概念解释 (conceptual) ─────────────────────────────
    TestQuestion(
        id="C001",
        question="什么是 RAG (Retrieval-Augmented Generation)？它解决了 LLM 的什么问题？",
        ground_truth="RAG (检索增强生成) 是一种将信息检索与文本生成相结合的技术架构。它在 LLM 生成答案之前，先从外部知识库中检索相关文档，然后将检索结果作为上下文提供给 LLM。RAG 主要解决了 LLM 的三大问题: (1) 知识截止日期限制 — 可以检索最新信息；(2) 幻觉问题 — 基于检索到的真实文档生成，减少编造；(3) 领域知识不足 — 可以接入特定领域的专业文档。",
        query_type="conceptual",
    ),
    TestQuestion(
        id="C002",
        question="请解释 Transformer 模型中的 Self-Attention 机制是如何工作的？",
        ground_truth="Self-Attention (自注意力) 是 Transformer 的核心机制。其工作流程为: (1) 对每个输入 token 生成 Q (Query)、K (Key)、V (Value) 三个向量；(2) 计算注意力分数 — Q 与所有 K 的点积除以 sqrt(d_k) 进行缩放；(3) 通过 softmax 归一化得到注意力权重；(4) 权重加权求和 V 得到输出。这使得每个 token 都能直接关注到序列中的所有其他 token，捕获长距离依赖关系。",
        query_type="conceptual",
    ),
    TestQuestion(
        id="C003",
        question="什么是向量嵌入 (Embedding)？为什么在 RAG 系统中需要它？",
        ground_truth="向量嵌入 (Embedding) 是将文本、图像等非结构化数据映射到高维向量空间的技术。语义相似的文本在向量空间中的距离也更近。在 RAG 系统中，Embedding 的作用是: (1) 将文档库中的文本转为向量存储；(2) 将用户查询也转为向量；(3) 通过向量相似度计算 (如余弦相似度) 快速找到与查询最相关的文档。这使得 RAG 可以理解语义而不仅仅是关键词匹配。",
        query_type="conceptual",
    ),
    TestQuestion(
        id="C004",
        question="MCP (Model Context Protocol) 协议的设计目标是什么？它解决了什么问题？",
        ground_truth="MCP (Model Context Protocol) 是 Anthropic 提出的开放协议，设计目标是标准化 AI 模型与外部工具/数据源之间的交互方式。它解决的问题: (1) 工具碎片化 — 每个模型/框架有自己定义工具的方式，MCP 提供统一标准；(2) 工具复用性 — MCP Server 可以被任何支持 MCP 的模型直接调用；(3) 可发现性 — Client 可以动态发现 Server 提供的工具。MCP 将工具抽象为独立 Server，实现了工具定义与模型的解耦。",
        query_type="conceptual",
    ),
    TestQuestion(
        id="C005",
        question="请解释 LangGraph 中的 Checkpoint 机制及其在 Agent 系统中的作用？",
        ground_truth="LangGraph 的 Checkpoint 机制允许在图的每个节点执行后保存 State 快照。作用包括: (1) 中断恢复 — Agent 运行中断后可以从最近的 checkpoint 恢复，不需要从头开始；(2) 调试可观测 — 可以回溯查看每一步的 State 变化；(3) 人类审批 — 在关键节点暂停等待人工确认后继续；(4) 分支回溯 — 可以回到某个历史状态尝试不同的执行路径。",
        query_type="conceptual",
    ),
    TestQuestion(
        id="C006",
        question="什么是 ReAct (Reasoning + Acting) 模式？它比传统的 Chain-of-Thought 有什么优势？",
        ground_truth="ReAct (Reasoning + Acting) 是一种将推理 (Reasoning) 与行动 (Acting) 交错执行的 Agent 模式。与 Chain-of-Thought (纯推理链) 相比，ReAct 的优势在于: (1) 可以与外部环境交互 — 不只是脑子里想，还能查资料、调工具；(2) 动态调整 — 根据行动结果调整后续推理，而非一次性规划；(3) 减少幻觉 — 行动结果提供事实依据，约束推理方向；(4) 适合信息不完全的任务 — 可以通过多次行动逐步获取所需信息。",
        query_type="conceptual",
    ),

    # ── 多步推理 (multi_hop) ───────────────────────────────
    TestQuestion(
        id="M001",
        question="BM25 和 Dense Embedding 检索各自的优劣是什么？为什么要用 RRF 融合两者而不是直接加权分数？",
        ground_truth="BM25 优势: 精确词匹配强，搜专用术语/API 名时准确率高，计算快无需 GPU。BM25 劣势: 无法理解语义，搜'卷积'找不到只写'convolution'的文档。Dense 优势: 语义理解强，能匹配同义词和近义表达。Dense 劣势: 精确术语匹配可能不如 BM25，需要 Embedding 模型和 GPU，成本较高。用 RRF 融合的原因: BM25 分数无上界 (可以是任意正数)，而余弦相似度在 [-1, 1] 范围，两种分数值域不同。直接加权需要先归一化，但归一化方法 (如 min-max) 受极端值影响大。RRF 用排名代替分数，巧妙绕过了值域不一致的问题。",
        query_type="multi_hop",
    ),
    TestQuestion(
        id="M002",
        question="在构建 RAG 系统时，什么时候应该选择 Agentic RAG (ReAct 循环) 而不是标准 RAG (一次检索即生成)？请举例说明。",
        ground_truth="选择 Agentic RAG 而非标准 RAG 的场景: (1) 复杂多步问题 — 如'比较 A 方法和 B 方法在 X 场景下的优劣'，需要先查 A、再查 B、然后对比分析，标准 RAG 一次检索可能遗漏某一方信息；(2) 信息不确定时 — 用户问题模糊，Agent 可以先用关键词检索试探，根据结果调整检索策略；(3) 需要多源信息整合 — 同时需要文档知识和数据库统计数据时。简单场景 (如'XXX 的参数有哪些？') 用标准 RAG 即可，Agentic RAG 反而增加延迟和成本。关键是: 评估查询复杂度，按需决定是否启动多轮推理。",
        query_type="multi_hop",
    ),
    TestQuestion(
        id="M003",
        question="MCP 协议和传统的 Function Calling 在架构设计上有什么本质区别？为什么 MCP 被认为是更面向未来的方案？",
        ground_truth="本质区别: (1) 耦合度 — Function Calling 的工具定义和 LLM API 调用耦合在一起，每次请求都要传完整的工具定义 JSON；MCP 将工具抽象为独立 Server，与 LLM 调用解耦。(2) 复用性 — FC 的工具定义绑定在特定模型的 API 格式中，换模型需要重写；MCP Server 可以被任何支持 MCP Client 的模型直接使用。(3) 可发现性 — MCP 支持工具的动态发现 (list_tools)，Client 不需要事先知道有哪些工具；FC 需要在每次请求中静态声明。(4) 生命周期 — MCP Server 独立运行，有自己的状态和生命周期管理；FC 是无状态的。MCP 更面向未来因为: 随着 AI Agent 生态发展，工具会越来越多，标准化和复用性比定制化更重要。类比: FC 是每次点菜手写菜单，MCP 是固定菜单本（可复用、标准化）。",
        query_type="multi_hop",
    ),
    TestQuestion(
        id="M004",
        question="在 RAG 系统中，如何平衡检索精度和召回率？Parent-Document Retriever 和混合检索分别是如何解决这个问题的？",
        ground_truth="检索精度 vs 召回率的平衡是 RAG 系统的核心挑战。小块 (如 256 token) 检索精度高 (向量能精确匹配相关段落)，但可能丢失上下文导致召回不足；大块 (如 1024 token) 召回率高 (包含更多相关上下文)，但精度下降 (噪声增多)。Parent-Document Retriever 解决方式: 用小块做检索保证精度，检索命中后将所属的大块 (parent) 作为上下文返回，兼顾精度和召回。混合检索解决方式: BM25 保证精确词匹配的召回，Dense 保证语义相关的召回，RRF 融合确保两者各自命中的结果都不会丢失。两者结合: 混合检索 + Parent-Document 策略可以在精度和召回之间取得最优平衡。",
        query_type="multi_hop",
    ),
    TestQuestion(
        id="M005",
        question="RAGAS 评估框架的四个核心指标分别衡量什么？它们之间有什么关系？为什么单看一个指标不够？",
        ground_truth="RAGAS 四个核心指标: (1) Faithfulness (忠实度) — 生成的回答是否有检索到的文档作为依据，衡量是否'瞎编'；(2) Answer Relevance (答案相关性) — 回答是否切合用户问题，衡量是否'跑题'；(3) Context Precision (上下文精度) — 检索到的文档中相关文档的比例，衡量检索'是不是搜到了有用的'；(4) Context Recall (上下文召回) — 所有相关文档中被检索到的比例，衡量'有用的搜没搜到'。关系: Precision 和 Recall 相互制约 (提高一个可能降低另一个)，Faithfulness 依赖检索质量 (检索不到相关文档就容易瞎编)，Relevance 依赖生成质量。单看一个指标不够因为: 高 Faithfulness 低 Relevance 说明检索到了相关文档但回答偏题；高 Precision 低 Recall 说明搜到的都对但遗漏了很多。四个指标一起看才能全面评估 RAG 系统质量。",
        query_type="multi_hop",
    ),
    TestQuestion(
        id="M006",
        question="为什么 LangGraph 比直接用 while 循环 + if-else 更适合构建 Agent 系统？请从工程角度分析。",
        ground_truth="LangGraph 优于 while+if-else 的原因: (1) 显式状态管理 — State TypedDict 明确定义了流转数据，配合 reducer 自动处理状态更新，避免手动管理状态变量的混乱；(2) Checkpoint 机制 — 自动在每个节点保存状态快照，支持中断恢复和调试回溯，while 循环需要手动实现；(3) 图结构可视化 — 图结构可以导出为可视化图，直观展示 Agent 的工作流，便于沟通和调试；(4) 多分支路由 — 条件边 (conditional edges) 原生支持多分支决策，while 循环中的嵌套 if-else 在复杂场景下可读性差；(5) 流式支持 — LangGraph 原生支持 streaming，while 循环需要手动实现异步和流式输出；(6) 可组合性 — 可以将多个 Graph 组合为更大的系统。工程上的核心收益: 可观测性、可维护性、可复用性。",
        query_type="multi_hop",
    ),
    TestQuestion(
        id="M007",
        question="在 Agentic RAG 中如何防止死循环？请从 ReAct 循环设计和 Prompt 工程两个角度分析。",
        ground_truth="防止死循环的策略: ReAct 循环设计层面: (1) State 中维护 step_count，在 reflect 节点设置最大步数上限 (如 5 轮)，超限强制返回当前最佳答案；(2) 每轮评估信息增量 — 如果新一轮检索没有返回新的文档，直接进入 answer；(3) 工具调用去重 — 缓存相同查询的检索结果，避免重复调用。Prompt 工程层面: (1) 在 system prompt 中注入'如果反复检索仍无结果，请直接说明无法回答'的指令；(2) 温度参数设低 (0.2-0.3)，减少 LLM 随机性导致的无意义重试；(3) 每轮 prompt 中包含已执行步数和剩余步数，让模型意识到步数限制。两者结合才能确保 Agent 既不会过早放弃 (简单问题一轮过)，也不会无限循环 (复杂问题最多 N 轮)。",
        query_type="multi_hop",
    ),
]


def get_test_questions() -> List[TestQuestion]:
    """获取全部测试问题"""
    return TEST_QUESTIONS


def get_by_type(query_type: str) -> List[TestQuestion]:
    """按类型筛选测试问题"""
    return [q for q in TEST_QUESTIONS if q.query_type == query_type]
