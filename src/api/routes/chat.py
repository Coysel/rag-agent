"""
对话端点 — POST /chat, POST /chat/session

SSE 事件类型 (对应 ReAct 各节点):
  - reason:  Agent 分析问题，决定工具调用
  - act:     执行工具调用
  - observe: 处理工具结果
  - reflect: 评估信息充分性
  - answer:  最终回答
  - done:    完成信号
  - error:   错误信息
"""
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends

from src.core.exceptions import NotFoundError, ServiceUnavailableError
from sse_starlette.sse import EventSourceResponse

from src.utils.logging import get_logger
from src.api.dependencies import get_graph, get_query_router, get_session
from src.api.schemas.chat import ChatRequest, ChatResponse, StepEvent, Source
from src.storage.session_store import SessionStore

router = APIRouter(tags=["chat"])


# ── 辅助函数 ────────────────────────────────────────────────


def _extract_sources(state: dict) -> list[Source]:
    """从 State 中提取引用来源"""
    context_docs = state.get("context_docs", [])
    sources = []
    seen = set()
    for doc in context_docs:
        title = doc.get("title", "未知来源")
        if title not in seen:
            seen.add(title)
            sources.append(Source(
                title=title,
                source=doc.get("source", ""),
                score=doc.get("rrf_score", doc.get("dense_score", doc.get("bm25_score", 0))),
                content=doc.get("content", "")[:800],
            ))
    return sources


def _build_response(query: str, state: dict) -> ChatResponse:
    """从 State 构建非流式 ChatResponse"""
    sources = _extract_sources(state)
    return ChatResponse(
        query=query,
        answer=state.get("answer", ""),
        sources=sources,
        steps=state.get("step_count", 0),
        query_type=state.get("query_type", ""),
    )


async def _run_graph(initial_state: dict, graph) -> dict:
    """运行 LangGraph 直到结束 (非流式)"""
    final_state = dict(initial_state)
    async for event in graph.astream(initial_state):
        for _node_name, state_update in event.items():
            final_state.update(state_update)
    return final_state


# ── SSE 流式生成器 ──────────────────────────────────────────


def _build_step_event(node_name: str, state_update: dict, step: int) -> dict:
    """构建单个 ReAct 步骤的 SSE 事件数据"""
    stream_buffer = state_update.get("stream_buffer", [])
    content = "".join(stream_buffer) if stream_buffer else f"[{node_name}]"

    return StepEvent(
        type=node_name,
        content=content,
        step=step,
        data={
            "query_type": state_update.get("query_type", ""),
            "tool_calls": [
                {"name": tc["name"], "input": tc.get("input", {})}
                for tc in state_update.get("tool_calls", [])
            ],
            "context_count": len(state_update.get("context_docs", [])),
        },
    )


async def _stream_chat(
    initial_state: dict,
    graph,
) -> AsyncGenerator[str, None]:
    """SSE 流式生成器（单轮对话）"""
    step = 0
    try:
        async for event in graph.astream(initial_state):
            for node_name, state_update in event.items():
                step += 1
                event_data = _build_step_event(node_name, state_update, step)
                yield {"event": node_name, "data": event_data.model_dump_json()}

                if node_name == "answer":
                    # 逐句流式输出答案（前端逐句渲染）
                    stream_tokens = state_update.get("stream_tokens", [])
                    for token in stream_tokens:
                        token_event = StepEvent(type="answer", content=token, step=step)
                        yield {"event": "answer", "data": token_event.model_dump_json()}

                    answer_text = state_update.get("answer", "")
                    sources = _extract_sources(state_update)

                    done_data = {
                        "type": "done",
                        "content": "",
                        "step": step,
                        "data": {
                            "answer": answer_text,
                            "sources": [s.model_dump() for s in sources],
                            "steps": step,
                            "query_type": initial_state.get("query_type", ""),
                            "context_count": len(state_update.get("context_docs", [])),
                        },
                    }
                    yield {"event": "done", "data": json.dumps(done_data, ensure_ascii=False)}

    except Exception as e:
        error_event = StepEvent(type="error", content=f"Error: {str(e)}", step=step)
        yield {"event": "error", "data": error_event.model_dump_json()}


async def _stream_chat_session(
    initial_state: dict,
    query: str,
    session_id: str,
    graph,
    session_store: SessionStore,
) -> AsyncGenerator[str, None]:
    """SSE 流式生成器（多轮对话 — 自动更新会话历史）"""
    final_answer = ""
    step = 0
    try:
        async for event in graph.astream(initial_state):
            for node_name, state_update in event.items():
                step += 1
                if node_name == "answer":
                    final_answer = state_update.get("answer", "")

                event_data = _build_step_event(node_name, state_update, step)
                yield {"event": node_name, "data": event_data.model_dump_json()}

                if node_name == "answer":
                    # 逐句流式输出答案
                    stream_tokens = state_update.get("stream_tokens", [])
                    for token in stream_tokens:
                        token_event = StepEvent(type="answer", content=token, step=step)
                        yield {"event": "answer", "data": token_event.model_dump_json()}

                    sources = _extract_sources(state_update)
                    done_data = {
                        "type": "done",
                        "step": state_update.get("step_count", step),
                        "data": {
                            "answer": final_answer,
                            "sources": [s.model_dump() for s in sources],
                            "session_id": session_id,
                            "query_type": initial_state.get("query_type", ""),
                        },
                    }
                    yield {"event": "done", "data": json.dumps(done_data, ensure_ascii=False)}

        # 异步持久化会话
        if final_answer:
            session_store.append(session_id, query, final_answer)

    except Exception as e:
        error_event = StepEvent(type="error", content=f"Error: {str(e)}", step=step)
        yield {"event": "error", "data": error_event.model_dump_json()}


# ── 端点 ────────────────────────────────────────────────────


def _resolve_doc_ids(categories: list[str]) -> list[str] | None:
    """将类别 ID 列表解析为文档 ID 列表"""
    if not categories:
        return None
    from src.categorization.category_store import get_category_store
    store = get_category_store()
    doc_ids = store.get_doc_ids(categories)
    return doc_ids if doc_ids else None


@router.post("/chat")
async def chat(
    request: ChatRequest,
    graph=Depends(get_graph),
    query_router=Depends(get_query_router),
):
    """单轮对话 — 支持流式 (SSE) 和非流式 (JSON)"""
    logger = get_logger()
    logger.info(f"收到查询: {request.query[:80]}...")

    query_type = query_router.classify(request.query)
    doc_ids = _resolve_doc_ids(request.categories)

    from src.agent.graph import get_initial_state
    initial_state = get_initial_state(
        query=request.query,
        max_steps=request.max_steps,
        doc_ids=doc_ids,
        web_search=request.web_search,
    )
    initial_state["query_type"] = query_type.value if hasattr(query_type, "value") else str(query_type)

    if request.stream:
        return EventSourceResponse(_stream_chat(initial_state, graph))
    else:
        try:
            final_state = await _run_graph(initial_state, graph)
            return _build_response(request.query, final_state)
        except Exception as e:
            raise ServiceUnavailableError("对话处理失败", str(e))


@router.post("/chat/session")
async def chat_session(
    request: ChatRequest,
    graph=Depends(get_graph),
    query_router=Depends(get_query_router),
    session_store=Depends(get_session),
):
    """多轮对话 — 支持 session_id 关联上下文"""
    logger = get_logger()

    session_id = request.session_id
    if not session_id:
        from src.utils.logging import get_correlation_id
        session_id = get_correlation_id()

    history = session_store.get(session_id)
    query_type = query_router.classify(request.query)
    doc_ids = _resolve_doc_ids(request.categories)

    from src.agent.graph import get_initial_state
    initial_state = get_initial_state(
        query=request.query,
        max_steps=request.max_steps,
        conversation_history=history,
        session_id=session_id,
        doc_ids=doc_ids,
        web_search=request.web_search,
    )
    initial_state["query_type"] = query_type.value if hasattr(query_type, "value") else str(query_type)

    logger.info(f"Session({session_id}) ← 第 {len(history)//2 + 1} 轮对话")

    if request.stream:
        return EventSourceResponse(
            _stream_chat_session(initial_state, request.query, session_id, graph, session_store)
        )
    else:
        try:
            final_state = await _run_graph(initial_state, graph)
            answer = final_state.get("answer", "")
            session_store.append(session_id, request.query, answer)
            return _build_response(request.query, final_state)
        except Exception as e:
            raise ServiceUnavailableError("对话处理失败", str(e))


# ── Session 管理端点 ─────────────────────────────────────────


@router.get("/chat/sessions")
async def list_sessions(session_store=Depends(get_session)):
    """列出所有会话"""
    return {"sessions": session_store.get_all_sessions()}


@router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str, session_store=Depends(get_session)):
    """删除一个会话"""
    ok = session_store.delete(session_id)
    if not ok:
        raise NotFoundError("会话")
    return {"status": "ok"}
