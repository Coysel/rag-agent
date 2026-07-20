# Agentic RAG 项目概览

> 核心实现 · 当前效果 · 待解决问题

---

## 一、核心实现

### 1. 智能问答引擎

系统的核心是一个基于 LangGraph 构建的 ReAct Agent。它的工作方式是：用户提问后，先由查询路由器自动判断问题类型——是事实查询、概念理解、还是需要多步推理——然后进入 reason → act → observe → reflect → answer 的循环。每一轮，Agent 决定是继续检索更多信息还是信息已经足够可以回答，最多迭代 5 轮。回答生成后，按句子拆分通过 SSE 流式推送到前端，用户可以看到思考过程和答案逐句呈现。

关键模块：[src/agent/graph.py](src/agent/graph.py)（图编排）、[src/agent/nodes.py](src/agent/nodes.py)（节点逻辑）、[src/agent/llm_client.py](src/agent/llm_client.py)（LLM 客户端）。

值得提一下的是上下文管理——系统用 tiktoken 做了精确的 token 计数，当检索到的文档总量超出 LLM 上下文窗口时，会按相关性分数从低到高动态截断，保证不会因为超长而报错。

### 2. 混合检索

检索部分做了 BM25 稀疏检索 + 向量稠密检索的混合方案，用加权 RRF（倒数排名融合）把两边的结果合并。之所以用 RRF 而不是直接加权原始分数，是因为 BM25 的分数无上界而余弦相似度在 0 到 1 之间，两者不可比——用排名代替分数就绕过了这个问题。

文档分块用了父子策略：子块 256 token 用于检索（精度高），父块 1024 token 作为上下文喂给 LLM（信息完整）。这样既不会因为块太小丢上下文，也不会因为块太大降低检索精度。

关键模块：[src/retrieval/hybrid_retriever.py](src/retrieval/hybrid_retriever.py)（RRF 融合）、[src/retrieval/pipeline.py](src/retrieval/pipeline.py)（检索管线）、[src/retrieval/parent_retriever.py](src/retrieval/parent_retriever.py)（父子展开）。

### 3. 联网搜索

联网搜索作为 MCP 工具集成在 Agent 里。Agent 在推理阶段会自己判断——如果用户问的是实时信息（天气、新闻、最新版本），就直接调 web_search；如果是普通知识问答，先查本地知识库，检索结果不够再补一刀联网。

实现位于 [src/mcp/web_server.py](src/mcp/web_server.py)。

### 4. 多轮对话与历史记录

对话历史通过 SQLite 做后端持久化，前端用 localStorage 做双重备份。用户可以创建、切换、删除会话，刷新页面后历史消息自动恢复。后端自动清理过期会话，不会无限膨胀。

### 5. 文档管理

文档的上传、删除和索引重建通过 Admin API 管理。上传后自动走一遍增量分类——先对文档内容做层次化摘要，再判断是归入已有类别还是创建新类别。前端管理界面支持拖拽上传和可视化操作。

关键模块：[src/api/routes/admin.py](src/api/routes/admin.py)、[src/indexing/index_manager.py](src/indexing/index_manager.py)、[src/categorization/](src/categorization/)。

### 6. 幻觉检测

系统内置了 RAGAS 风格的评测框架，用 LLM-as-Judge 方式从四个维度检测回答质量。最核心的是 Faithfulness（忠实度）——它会逐条检查回答中的陈述是否能在检索到的文档中找到依据，低了就说明模型在瞎编。另外三个指标分别衡量答案是否切题、检索结果是否相关、以及该检索到的文档是否漏了。

前端的评测仪表盘用 SVG 环形图展示四项分数，按绿（≥0.7）/ 黄（≥0.4）/ 红（<0.4）三档着色，一眼就能看出当前系统的幻觉程度。支持预设 20 题测试集的 Dense vs Hybrid 对比实验，也可以输入自定义问题即时评测。

关键模块：[src/evaluation/ragas_eval.py](src/evaluation/ragas_eval.py)、[frontend/js/pages/eval.js](frontend/js/pages/eval.js)。

### 7. 系统健康自检

提供了三级健康检查端点：`/health` 看索引状态和配置概况，`/health/deep` 真实调用一次 LLM 和检索管线验证连通性，`/llm-test` 单独测 LLM 返回完整响应内容和 token 用量。前端设置页有一键检查按钮，方便随时确认知识库和大模型是否正常。

关键模块：[src/api/routes/health.py](src/api/routes/health.py)。

### 8. 安全中间件

中间件层做了四件事：CORS 白名单控制跨域、滑动窗口速率限制（chat 30 次/分钟，eval 10 次/分钟）、安全响应头（CSP、X-Frame-Options 等），以及每个请求注入 Correlation ID 方便日志追踪。

关键模块：[src/api/middleware.py](src/api/middleware.py)。

### 9. 前端

前端是零框架的原生 JavaScript SPA，共五个页面。Chat 页面做 SSE 流式对话，思考过程的每一步（推理→调用工具→观察结果→反思→回答）都可视化为可折叠的时间线。Admin 页面管文档，Eval 页面看评测仪表盘，Retrieval 页面做三种检索器的并排对比，Settings 页面管配置和健康检查。

关键模块：[frontend/](frontend/)。

---

## 二、目前效果

在 115 篇文档、572 个文本块的索引规模下（DeepSeek-chat + BGE 本地 Embedding），实测三个典型查询：

| 查询 | 耗时 | 步数 | 分类 | 来源 |
|------|------|------|------|------|
| RRF 融合检索的原理是什么？ | 9.3s | 1 轮 | conceptual ✓ | 7 篇 |
| LangGraph 的 ReAct 循环是如何工作的？ | 4.8s | 1 轮 | conceptual ✓ | 8 篇 |
| BM25 和向量检索在混合检索中分别起什么作用？ | 5.9s | 1 轮 | multi_hop ✓ | 8 篇 |

三个查询全部正确分类、准确检索、回答有据可查且标注来源。

系统目前具备的完整能力：基础问答（带来源引用）、Agent 自主判断联网搜索、多轮对话（历史持久化）、文档管理（上传/删除/重建/自动分类）、四维幻觉评测（环形仪表盘可视化）、系统自检（三级健康检查）、SSE 流式输出（思考过程可见）、以及按文档类别限定检索范围。

---

## 三、未解决的问题

**文档格式支持有限。** 当前只处理纯文本（`.txt` `.md` `.py` `.html` `.json` 等 13 种格式），PDF、Word、Excel、PPT、图片都不支持。这直接限制了知识库的多样性——论文、报告、扫描件这类常见的企业文档全部无法索引。

**没有用户认证系统。** 系统是按个人使用设计的，Admin API 通过 HTTP Header 明文传密钥做鉴权，默认密钥是硬编码的。多人使用或对外开放的话需要引入完整的登录和权限体系。

**LLM 生态单一。** 目前只接了 DeepSeek 和 Anthropic (Claude) 两个 API。OpenAI、Gemini、国内模型、以及 Ollama 等本地部署方案都不支持，加新提供商需要改 [llm_client.py](src/agent/llm_client.py) 的核心逻辑。

**网络搜索靠 HTML 抓取而非 API。** [web_server.py](src/mcp/web_server.py) 是用正则从 Bing 搜索结果页 HTML 里提取内容，没有用官方的 Search API。Bing 的页面结构一变动搜索功能就会挂。SerpAPI、Tavily 这类规范的搜索服务也没有接入。
