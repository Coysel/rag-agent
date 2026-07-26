"""
ReAct 循环节点实现 — Reason → Act → Observe → Reflect → Answer

每个节点都是一个独立的函数，从 AgentState 读取输入，更新后返回。
节点之间通过 LangGraph 的 StateGraph 连接。
"""
import time
import re
from typing import Any, Dict, List, Tuple

import tiktoken

from config import (
    LLM_PROVIDER,
    MAX_STEPS,
    TEMPERATURE,
    MAX_CONTEXT_TOKENS,
)
from src.agent.llm_client import get_llm_client
from src.agent.state import AgentState
from src.agent.tools import get_tool_definitions
from src.mcp.client_manager import get_mcp_manager
from src.utils.logging import get_logger, get_correlation_id


# ── 懒初始化 ───────────────────────────────────────────────

_tokenizer = None


def _get_llm():
    return get_llm_client()


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = tiktoken.get_encoding("cl100k_base")
    return _tokenizer


def _estimate_tokens(text: str) -> int:
    """估算文本 token 数"""
    return len(_get_tokenizer().encode(text))


def _format_context_docs(context_docs: List[dict]) -> str:
    """将检索到的文档列表格式化为上下文字符串"""
    if not context_docs:
        return "（无相关文档）"

    parts = []
    for i, doc in enumerate(context_docs, 1):
        title = doc.get("title", "未知来源")
        source = doc.get("source", "")
        content = doc.get("content", "")
        is_web = source.startswith("http://") or source.startswith("https://")
        source_type = "🌐 网页" if is_web else "📄 文档"
        date_str = f" | 日期: {doc.get('date', '')}" if doc.get("date") else ""
        website = doc.get("website", "")
        if is_web and website:
            source_label = f"{website} ({source})"
        else:
            source_label = source
        parts.append(f"[来源 {i}] {source_type}: {title} ({source_label}){date_str}\n{content}")
    return "\n\n---\n\n".join(parts)


def _get_retrieval_hint(query_type: str) -> str:
    """根据查询类型返回检索策略提示"""
    if query_type == "factual":
        return (
            "## 检索策略提示（事实查询）\n"
            "- 优先使用 search_documents(query, method='bm25') 做精确关键词匹配\n"
            "- 如果 BM25 结果不足，再尝试 method='hybrid'\n"
        )
    elif query_type == "conceptual":
        return (
            "## 检索策略提示（概念查询）\n"
            "- 优先使用 search_documents(query, method='dense') 做语义理解\n"
            "- 如果 Dense 结果不足，再尝试 method='hybrid'\n"
        )
    elif query_type == "multi_hop":
        return (
            "## 检索策略提示（多步推理）\n"
            "- 先拆解问题为子问题，逐步检索\n"
            "- 可能需要链式调用多个工具组合结果\n"
            "- 可以使用 execute_query 查询结构化数据\n"
        )
    return ""


def _format_history(history: List[dict]) -> str:
    """格式化对话历史为字符串"""
    if not history:
        return "（无历史对话）"
    lines = []
    for h in history[-6:]:  # 最近 3 轮（6 条消息）
        role = "用户" if h.get("role") == "user" else "助手"
        content = h.get("content", "")[:200]
        lines.append(f"- {role}: {content}")
    return "\n".join(lines)


def _build_system_prompt(
    context_docs: List[dict], step_count: int, max_steps: int,
    query_type: str = "", history: List[dict] = None,
    doc_ids: List[str] = None,
    web_search: bool = False,
) -> str:
    """构建 ReAct 推理阶段的系统提示"""
    hint = _get_retrieval_hint(query_type)
    history_str = _format_history(history or [])

    # 文档过滤提示
    filter_note = ""
    if doc_ids:
        filter_note = f"\n## 文档范围过滤\n当前对话限定了搜索范围（{len(doc_ids)} 个文档 ID），请只在这些文档中检索。"

    # 联网搜索提示（仅当用户启用时显示）
    web_search_note = ""
    if web_search:
        web_search_note = (
            "\n## 🔌 联网搜索 (web_search 工具已启用)\n"
            "你有 web_search 工具可以搜索互联网。重要：\n"
            "- 用户问题含「最新」「今天」「当前」「实时」「新闻」「天气」「现在」「联网」→ 直接用 web_search\n"
            "- 本地检索无结果或不相关 → 用 web_search 补充\n"
            "- 使用后标注来源 URL\n"
            "- **严禁说你无法联网、无法访问互联网、或无法获取实时信息——你拥有 web_search 工具，直接调用即可！**\n"
        )

    return f"""# 角色
你是一个 RAG（检索增强生成）智能问答系统的推理 Agent。你的核心能力是利用工具检索本地知识库和互联网，综合分析多源信息后回答用户问题。你不是一个仅凭自身知识回答的对话模型——你的价值在于**找到正确的信息，而非记住所有信息**。

# 背景
{history_str}

当前系统状态：
- 已执行 {step_count}/{max_steps} 步（最多 {max_steps} 步）
- 已检索到 {len(context_docs)} 篇相关文档作为上下文
{filter_note}
{web_search_note}
{hint}

# 任务
你的工作是**推理并决策下一步行动**——而非直接回答用户的问题。请按以下优先级决策：

1. **联网搜索判断（最高优先级）**：用户问题是否涉及实时信息？判断标准：
   - 含时间敏感词：「最新」「今天」「当前」「实时」「新闻」「天气」「现在」「刚刚」
   - 涉及时效性事实：股价、赛事结果、新闻事件、版本发布、政策变动
   - 涉及本地知识库不可能覆盖的信息：天气、航班、具体人物近况、即时数据
   → 如果是，**第一步就调用 web_search**，不要先查本地知识库。

2. **本地检索**：普通知识问答、概念理解、技术文档查询 → 调用 search_documents
   - 事实查询优先用 method='bm25'（精确关键词匹配）
   - 概念理解优先用 method='dense'（语义理解）
   - 不确定时用 method='hybrid'（默认）

3. **结果评估**：检索结果是否充分回答了用户问题？
   - 充分 → 结束检索，准备回答
   - 不充分 → 调整策略（换检索方法、改写查询词、或补充联网搜索）重新检索

4. **达到最大步数**：如果在 {max_steps} 步内反复检索仍无结果，直接基于已有信息诚实作答。

# 约束
- **信息驱动**：所有结论必须来自检索到的文档，不可凭模型自身知识凭空编造。
- **诚实为本**：检索结果不足时不强行编造答案，必须明确指出信息缺失的具体内容。
- **联网能力认知**：你拥有 web_search 工具，具备实时联网搜索能力。严禁声称"我无法联网"、"我无法访问互联网"、"我的知识截止于某日期"——这些说法是错误的，直接调用 web_search 即可。
- **追问理解**：如果用户问题是对上一轮的追问（如"继续"、"详细说说"、"那第二个呢"），必须结合历史对话理解指代关系。
- **来源可溯**：每个关键结论都要标注引用来源。
- **语言**：始终用中文思考和输出。

# 输出格式
你需要输出 tool_calls（工具调用列表），每个工具调用包含：
- name: 工具名称（search_documents / web_search / execute_query）
- input: 工具参数字典
   - search_documents: {{"query": "检索词", "method": "hybrid|bm25|dense"}}
   - web_search: {{"query": "搜索词", "max_results": 5}}
   - execute_query: {{"sql": "SQL语句"}}

如果信息已充分，tool_calls 输出空数组，系统将进入回答阶段。

## 当前已检索到的信息来源
{_format_context_docs(context_docs)}
"""


def _build_answer_prompt(context_docs: List[dict]) -> str:
    """构建答案生成阶段的系统提示"""
    # 识别是否有网页搜索结果的提示
    has_web_results = any(
        (doc.get("source", "").startswith("http://") or doc.get("source", "").startswith("https://"))
        for doc in context_docs
    )
    web_note = ""
    if has_web_results:
        web_note = (
            "\n**注意：以下来源列表中包含 🌐 网页搜索结果。请用 [来源N] (N=数字编号) 格式引用。"
            "引用时使用下方标注的编号（如 [来源1]、[来源2]），而非网页标题。**\n"
        )

    return f"""# 角色
你是一个 RAG 智能问答系统的答案生成器。你的职责是基于系统检索到的多源信息（本地知识库文档 + 联网搜索结果），生成准确、完整、可溯源的回答。

# 背景
系统已为你检索到以下 {len(context_docs)} 条信息来源，这是生成答案的全部信息基础。每条来源都标注了编号和类型（📄 文档 / 🌐 网页）。
{web_note}
# 任务
根据用户问题，综合这些信息来源生成回答：
- 提取所有与问题直接相关的信息
- 整合多个来源中的相关片段，形成连贯回答
- **每条关键信息必须标注来源编号**，格式: [来源N]（N 为下方来源的编号，如 [来源1]、[来源2]）

# 约束
- **信息驱动**：回答必须来源于下方给出的信息。不编造不存在的内容。
- **积极利用**：即使信息只有部分相关，也要提取有用部分作答，而非直接说"找不到"。
- **诚实补充**：信息确实不完整时，先给出已有的信息，再说明"关于XX部分，检索结果中未包含详细内容"。
- **完全无相关信息**：仅当所有来源确实与问题无关时，才说明无法回答，并建议换个问法或尝试联网搜索。
- **语言**：用中文输出，自然流畅，避免机械罗列。

# 输出格式
采用"总—分"结构：
1. **概述**（1-2 句总体结论）
2. **详细回答**（分点展开，每句引用都要标注 [来源N]）
3. **来源列表**（列出所有引用的来源编号、标题和链接）

来源引用示例：
- "AI Agent 是一种能自主执行任务的系统[来源1]。"
- "百度搜索 API 免费额度为每日 100 次[来源2]。"
- 分点时可标在句尾：如"RRF 融合排序算法通过公式 XXX 计算[来源3]。"
- **每条回答要点至少引用一个来源，禁止整段回答不标注任何来源！**

{_format_context_docs(context_docs)}"""


def _truncate_context(docs: List[dict], max_tokens: int = MAX_CONTEXT_TOKENS) -> List[dict]:
    """动态截断低相关文档，确保总 token 数不超限"""
    if not docs:
        return docs

    # 按 RRF 分数排序（高相关优先）
    sorted_docs = sorted(
        docs,
        key=lambda d: d.get("rrf_score", d.get("dense_score", d.get("bm25_score", 0))),
        reverse=True,
    )

    selected = []
    total_tokens = 0
    #选择
    for doc in sorted_docs:
        doc_tokens = _estimate_tokens(doc.get("content", ""))
        if total_tokens + doc_tokens <= max_tokens:
            selected.append(doc)
            total_tokens += doc_tokens
        else:
            break

    return selected


def _split_sentences(text: str) -> list[str]:
    """将文本按句子边界拆分，用于流式输出"""
    if not text:
        return []
    # 按中文标点、换行、Markdown 段落边界拆分，保留分隔符
    parts = re.split(r'(?<=[。！？\n])\s*', text)
    # 过滤空串，合并过短的片段
    result = []
    buf = ""
    for p in parts:
        buf += p
        if len(buf) >= 20 or p.endswith("\n"):
            result.append(buf)
            buf = ""
    if buf:
        result.append(buf)
    return result


def _tool_name(tool_def: dict) -> str:
    """从 OpenAI 或 Anthropic 格式的工具定义中提取工具名"""
    # OpenAI format: {"type": "function", "function": {"name": "...", ...}}
    if "function" in tool_def:
        return tool_def["function"].get("name", "")
    # Anthropic format: {"name": "...", ...}
    return tool_def.get("name", "")


def _describe_tool_call(tool_name: str, tool_input: dict) -> str:
    """生成人类可读的工具调用描述"""
    if tool_name == "search_documents":
        query = tool_input.get("query", "")
        method = tool_input.get("method", "hybrid")
        method_label = {"bm25": "关键词", "dense": "语义", "hybrid": "混合"}.get(method, method)
        return f"检索知识库 ({method_label}): \"{query[:80]}\""
    elif tool_name == "execute_query":
        sql = tool_input.get("sql", tool_input.get("query", ""))
        return f"执行 SQL 查询: \"{sql[:80]}\""
    elif tool_name == "web_search":
        query = tool_input.get("query", "")
        return f"联网搜索: \"{query[:80]}\""
    elif tool_name == "list_documents":
        return "列出可用文档"
    else:
        return f"调用 {tool_name}: {str(tool_input)[:80]}"


# ── 工具执行器 ────────────────────────────────────────────

async def _execute_tool(tool_name: str, tool_input: dict) -> Tuple[str, list]:
    """
    执行单个工具调用（通过 MCP 协议 call_tool）

    Args:
        tool_name: 工具名称
        tool_input: 工具参数字典

    Returns:
        (result_text, structured_data):
          - result_text: LLM 可读的结果文本
          - structured_data: 原始文档列表（用于 context_docs 管道）
    """
    manager = get_mcp_manager()
    return await manager.execute_tool(tool_name, tool_input)


# ── ReAct 节点 ────────────────────────────────────────────

def reason_node(state: AgentState) -> Dict[str, Any]:
    """
    Reason 节点 — LLM 分析问题，决定下一步行动

    调用 LLM API，判断是需要检索更多信息还是可以直接回答。
    如果需要检索，输出工具调用计划。
    根据 query_type 注入检索策略提示。
    """
    logger = get_logger()
    cid = get_correlation_id()
    t0 = time.time()

    context_docs = state.get("context_docs", [])
    step_count = state.get("step_count", 0)
    max_steps = state.get("max_steps", MAX_STEPS)
    query_type = state.get("query_type", "")
    history = state.get("conversation_history", [])
    doc_ids = state.get("doc_ids", [])

    system_prompt = _build_system_prompt(
        context_docs, step_count, max_steps, query_type, history,
        doc_ids=doc_ids if doc_ids else None,
        web_search=state.get("web_search", False),
    )

    # 构建消息：将完整对话历史传为 messages，保障多轮对话上下文理解
    messages = []
    for h in history[-20:]:  # 最近 10 轮 (20 条消息)
        content = h.get("content", "")[:4000]
        messages.append({"role": h["role"], "content": content})
    messages.append({"role": "user", "content": state["query"]})

    # 获取工具列表，当 web_search 关闭时过滤掉 web_search 工具
    tools = get_tool_definitions(LLM_PROVIDER)
    if not state.get("web_search", False):
        tools = [t for t in tools if _tool_name(t) != "web_search"]

    try:
        result = _get_llm().create_message(
            system=system_prompt,
            messages=messages,
            tools=tools,
            max_tokens=1024,
            temperature=TEMPERATURE,
        )
    except Exception as e:
        logger.error(f"[{cid}] Reason LLM 调用失败: {e}")
        return {
            "status": "answer",
            "answer": f"API 调用出错: {str(e)}",
        }

    tool_calls = result.get("tool_calls", [])
    elapsed = round((time.time() - t0) * 1000)

    if tool_calls:
        tool_names = [t['name'] for t in tool_calls]
        logger.info(
            f"[{cid}] Reason({step_count+1}/{max_steps}) → 调用工具: "
            f"{tool_names} | {elapsed}ms | type={query_type}"
        )
        return {
            "tool_calls": tool_calls,
            "status": "continue",
            "stream_buffer": [f"💭 分析问题 → 需要调用 {', '.join(tool_names)} 检索信息\n"],
        }
    else:
        logger.info(f"[{cid}] Reason({step_count+1}/{max_steps}) → 直接回答 | {elapsed}ms")
        return {
            "tool_calls": [],
            "status": "answer",
            "stream_buffer": ["💭 分析问题 → 信息充分，直接回答\n"],
        }


async def act_node(state: AgentState) -> Dict[str, Any]:
    """
    Act 节点 — 执行工具调用（通过 MCP 协议 call_tool）

    执行 LLM 要求的工具调用 (检索文档 / 查询数据库)。
    将结果存入 tool_results。
    """
    logger = get_logger()
    cid = get_correlation_id()
    tool_calls = state.get("tool_calls", [])
    tool_results = list(state.get("tool_results", []))
    doc_ids = state.get("doc_ids", [])

    stream_buffer = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_input = dict(tool_call.get("input", {}))
        # 自动注入 doc_ids 过滤（当 state 中有限定的文档范围时）
        if tool_name == "search_documents" and doc_ids:
            tool_input["doc_ids"] = doc_ids
        t0 = time.time()

        # 生成人类可读的工具执行描述
        desc = _describe_tool_call(tool_name, tool_input)
        stream_buffer.append(f"🔧 {desc}\n")

        result_text, structured_data = await _execute_tool(tool_name, tool_input)

        elapsed = round((time.time() - t0) * 1000)
        doc_count = len(structured_data) if isinstance(structured_data, list) else 0
        logger.info(f"[{cid}] Act → {tool_name} | {elapsed}ms | 返回 {doc_count} 条")

        tool_results.append({
            "tool_call_id": tool_call.get("id", ""),
            "tool_name": tool_name,
            "tool_input": tool_input,
            "result": result_text,
            "retrieved_docs": structured_data if isinstance(structured_data, list) else [],
        })

    return {
        "tool_results": tool_results,
        "tool_calls": [],
        "stream_buffer": stream_buffer,
    }


def observe_node(state: AgentState) -> Dict[str, Any]:
    """
    Observe 节点 — 处理工具返回结果

    将检索到的新文档合并到 context_docs，去重。
    用 tiktoken 预估 token 量，动态截断低相关文档。
    """
    logger = get_logger()
    cid = get_correlation_id()
    tool_results = state.get("tool_results", [])
    context_docs = list(state.get("context_docs", []))

    seen_ids = {d.get("id", "") for d in context_docs}
    new_docs = []

    for tr in tool_results:
        for doc in tr.get("retrieved_docs", []):
            doc_id = doc.get("id", "")
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                new_docs.append(doc)

    context_docs.extend(new_docs)
    context_docs = _truncate_context(context_docs)

    if new_docs:
        titles = [d.get('title', '未知') for d in new_docs[:3]]
        logger.info(
            f"[{cid}] Observe → +{len(new_docs)} 篇, "
            f"共 {len(context_docs)} 篇 | {', '.join(titles)}"
        )
    else:
        logger.info(f"[{cid}] Observe → 无新增文档, 共 {len(context_docs)} 篇")

    if new_docs:
        titles = [d.get('title', '未知') for d in new_docs[:3]]
        more = f" 等 {len(new_docs)} 篇" if len(new_docs) > 3 else ""
        stream_buffer = [f"📋 找到 {len(new_docs)} 篇相关文档 → {', '.join(titles)}{more}"]
    else:
        stream_buffer = ["📋 未找到新的相关文档"]

    return {
        "context_docs": context_docs,
        "stream_buffer": stream_buffer,
    }


def reflect_node(state: AgentState) -> Dict[str, Any]:
    """
    Reflect 节点 — 评估信息是否足够回答问题
    """
    logger = get_logger()
    cid = get_correlation_id()
    step_count = state.get("step_count", 0)
    max_steps = state.get("max_steps", MAX_STEPS)
    context_docs = state.get("context_docs", [])
    status = state.get("status", "continue")

    if status == "answer":
        logger.info(f"[{cid}] Reflect → answer (reason 已判断)")
        return {
            "step_count": step_count + 1,
            "status": "answer",
            "stream_buffer": ["✅ 信息充足，准备生成回答\n"],
        }

    if step_count >= max_steps:
        logger.info(f"[{cid}] Reflect → max_steps ({max_steps}) 强制回答")
        return {
            "step_count": step_count + 1,
            "status": "max_steps",
            "stream_buffer": [f"⚠️ 已达最大检索次数 ({max_steps})，基于已有信息回答\n"],
        }

    if not context_docs:
        logger.info(f"[{cid}] Reflect → continue (无检索结果)")
        return {
            "step_count": step_count + 1,
            "status": "continue",
            "stream_buffer": ["🔄 未检索到结果，调整策略重新搜索\n"],
        }

    eval_prompt = f"""评估以下检索到的文档是否足以回答用户的问题。

用户问题: {state["query"]}

检索到的文档数: {len(context_docs)}

请只回复一个词: "sufficient" (足够) 或 "insufficient" (不足)"""

    try:
        result = _get_llm().create_message(
            system="",
            messages=[{"role": "user", "content": eval_prompt}],
            max_tokens=10,
            temperature=0,
        )
        text = result.get("text", "").strip().lower()

        if "sufficient" in text:
            logger.info(f"[{cid}] Reflect → answer (信息充足) | {len(context_docs)} 篇文档")
            return {
                "step_count": step_count + 1,
                "status": "answer",
                "stream_buffer": ["✅ 检索信息已足够，准备生成回答\n"],
            }
        else:
            logger.info(f"[{cid}] Reflect → continue (信息不足) → 第 {step_count+2} 轮")
            return {
                "step_count": step_count + 1,
                "status": "continue",
                "stream_buffer": [f"🔄 信息不足，开始第 {step_count + 2} 轮检索\n"],
            }
    except Exception:
        logger.warning(f"[{cid}] Reflect 评估失败，默认 answer")
        return {
            "step_count": step_count + 1,
            "status": "answer",
            "stream_buffer": ["✅ 准备生成回答\n"],
        }


def answer_node(state: AgentState) -> Dict[str, Any]:
    """
    Answer 节点 — 基于检索到的上下文生成最终回答
    """
    logger = get_logger()
    cid = get_correlation_id()
    t0 = time.time()
    query = state["query"]
    context_docs = state.get("context_docs", [])
    status = state.get("status", "answer")

    # 截断上下文
    context_docs = _truncate_context(context_docs)

    system_prompt = _build_answer_prompt(context_docs)

    if status == "max_steps":
        note = "\n\n注意: 已达到最大检索步数，以下回答基于目前已检索到的信息。"
    else:
        note = ""

    try:
        # 构建消息：包含完整对话历史以保持上下文连贯
        history = state.get("conversation_history", [])
        messages = []
        for h in history[-20:]:  # 最近 10 轮
            content = h.get("content", "")[:4000]
            messages.append({"role": h["role"], "content": content})
        messages.append({"role": "user", "content": query + note})

        result = _get_llm().create_message(
            system=system_prompt,
            messages=messages,
            max_tokens=2048,
            temperature=TEMPERATURE,
        )
        answer = result.get("text", "")
    except Exception as e:
        logger.error(f"[{cid}] Answer 生成失败: {e}")
        answer = f"生成回答时出错: {str(e)}"

    elapsed = round((time.time() - t0) * 1000)
    logger.info(f"[{cid}] Answer → {len(answer)} 字符 | {len(context_docs)} 篇来源 | {elapsed}ms")

    # 将答案按句子拆分，用于前端逐句流式展示
    stream_tokens = _split_sentences(answer)

    # 构建引用列表
    sources = []
    seen = set()
    for doc in context_docs:
        title = doc.get("title", "未知")
        if title not in seen:
            seen.add(title)
            sources.append({
                "title": title,
                "source": doc.get("source", ""),
                "score": doc.get("rrf_score", doc.get("dense_score", doc.get("bm25_score", 0))),
            })

    return {
        "answer": answer,
        "context_docs": context_docs,
        "stream_buffer": ["✍️ 基于检索结果生成回答\n"],
        "stream_tokens": stream_tokens,
        "status": "done",
    }
