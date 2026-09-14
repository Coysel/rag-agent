"""
边界与异常场景测试 — 并发、模型故障、下游不可用、输入边界

覆盖场景：
  - 并发操作同一会话（API 层 + SessionStore 层）
  - 模型超时 / 限流 / 返回非法 JSON
  - 向量库（下游工具）不可用
  - 输入边界：query 长度上下界、max_steps 范围

全部离线运行：LLM、向量库、MCP manager 均为 mock，不产生 API 费用。
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.e2e


# ── SSE 解析工具 ────────────────────────────────────────────


def _parse_sse_events(text):
    """解析 SSE text/event-stream 响应为事件列表"""
    events = []
    lines = text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("event: "):
            event_type = line[7:]
            i += 1
            data = {}
            if i < len(lines) and lines[i].strip().startswith("data: "):
                try:
                    data = json.loads(lines[i].strip()[6:])
                except (json.JSONDecodeError, KeyError):
                    pass
                i += 1
            events.append({"event": event_type, "data": data})
        else:
            i += 1
    return events


# ── 应用与依赖 mock ─────────────────────────────────────────


@pytest.fixture
def app_with_mocks(mocker):
    """创建 mock 全部重型依赖的 FastAPI app"""
    mocker.patch("src.api.app.setup_logging")

    mock_bm25 = mocker.patch("src.indexing.bm25_index.get_bm25_index")
    mock_bm25.return_value.document_count = 0
    mock_bm25.return_value.load = lambda: None

    mock_vs = mocker.patch("src.indexing.vector_store.get_vector_store")
    mock_vs.return_value.count = 0

    mock_llm = mocker.patch("src.agent.llm_client.get_llm_client")
    mock_llm.return_value.get_info.return_value = {
        "provider": "mock", "model": "mock", "base_url": "mock",
    }

    mock_emb = mocker.patch("src.indexing.embeddings.get_embedding_model")
    mock_emb.return_value.provider = "mock"
    mock_emb.return_value.model_name = "mock"

    mock_mcp = mocker.patch("src.mcp.client_manager.get_mcp_manager")
    mock_mcp.return_value.initialize = mocker.AsyncMock()
    mock_mcp.return_value.close = mocker.AsyncMock()
    mock_mcp.return_value._all_tools = []

    mock_ss = mocker.patch("src.storage.session_store.get_session_store")
    mock_ss.return_value.cleanup.return_value = 0

    mocker.patch("src.api.routes.documents._get_document_list",
                 return_value={"total_unique": 0, "documents": []})

    from src.api.app import create_app
    app = create_app()

    from src.api.dependencies import get_query_router, get_session
    from src.retrieval.router import QueryType
    from src.storage.session_store import SessionStore

    class _FixedRouter:
        def classify(self, query):
            return QueryType.FACTUAL

    app.dependency_overrides[get_query_router] = lambda: _FixedRouter()
    app.dependency_overrides[get_session] = lambda: SessionStore()
    return app


@pytest.fixture
def client(app_with_mocks):
    with TestClient(app_with_mocks) as tc:
        yield tc


def _setup(mocker, *, chain=None, side_effect=None, tool_side_effect=None):
    """替换 Agent 内部的 LLM、工具定义与 MCP manager"""
    mock_llm = mocker.patch("src.agent.nodes._get_llm")
    if side_effect is not None:
        mock_llm.return_value.create_message.side_effect = side_effect
    else:
        mock_llm.return_value.create_message.side_effect = chain

    mocker.patch("src.agent.nodes.get_tool_definitions",
                 return_value=[{"function": {"name": "search_documents"}}])

    mock_mgr = mocker.patch("src.agent.nodes.get_mcp_manager")
    if tool_side_effect is not None:
        mock_mgr.return_value.execute_tool = mocker.AsyncMock(
            side_effect=tool_side_effect)
    else:
        async def _execute(tool_name, tool_input):
            return (
                f"Tool '{tool_name}' executed successfully.",
                [{"id": "doc1", "title": "测试文档", "source": "test.txt",
                  "content": "检索到的内容", "rrf_score": 0.9}],
            )
        mock_mgr.return_value.execute_tool = _execute
    return mock_llm


def _setup_direct_answer(mocker, side_effect=None):
    """模型直接回答（无工具调用）；side_effect 用于注入模型故障"""
    if side_effect is not None:
        return _setup(mocker, side_effect=side_effect)
    return _setup(
        mocker,
        side_effect=lambda *args, **kwargs: {"text": "直接回答", "tool_calls": []},
    )


# ── 并发操作同一会话 ────────────────────────────────────────


class TestConcurrentSameSession:

    def test_concurrent_requests_do_not_fail(self, client, mocker):
        """同一 session_id 的并发请求：都应正常完成 SSE 流"""
        _setup_direct_answer(mocker)

        def ask(_):
            return client.post("/chat/session", json={
                "query": "并发问题",
                "session_id": "concurrent-session-001",
                "max_steps": 2,
                "stream": True,
            })

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(ask, range(2)))

        assert all(r.status_code == 200 for r in responses), \
            [r.status_code for r in responses]
        assert all("done" in r.text for r in responses)

    def test_session_store_concurrent_appends_keep_data_valid(self, tmp_path):
        """SessionStore 并发写入：不抛未处理异常，历史结构保持合法"""
        from src.storage.session_store import SessionStore

        store = SessionStore(str(tmp_path / "sessions.db"))

        def append(i):
            store.append("s-concurrent", f"问题{i}", f"回答{i}")

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(append, range(2)))

        history = store.get("s-concurrent")
        assert len(history) >= 2
        assert all(m["role"] in ("user", "assistant") for m in history)
        assert all("content" in m for m in history)


# ── 模型故障 ────────────────────────────────────────────────


class TestModelFailures:

    def test_llm_timeout_degrades_gracefully(self, client, mocker):
        """模型超时：请求不崩溃，返回错误说明"""
        _setup_direct_answer(mocker, side_effect=TimeoutError(
            "LLM request timed out after 60s"))

        r = client.post("/chat", json={
            "query": "测试", "max_steps": 2, "stream": True,
        })

        assert r.status_code == 200
        assert "出错" in r.text or "timed out" in r.text

    def test_llm_rate_limit_degrades_gracefully(self, client, mocker):
        """模型限流（429）：请求不崩溃，返回错误说明"""
        _setup_direct_answer(mocker, side_effect=RuntimeError(
            "429 Too Many Requests: rate limit exceeded"))

        r = client.post("/chat", json={
            "query": "测试", "max_steps": 2, "stream": True,
        })

        assert r.status_code == 200
        assert "429" in r.text or "出错" in r.text

    def test_invalid_json_from_model_degrades_gracefully(self, client, mocker):
        """模型返回非法 JSON：解析异常被兜住，请求不崩溃"""
        _setup_direct_answer(mocker, side_effect=json.JSONDecodeError(
            "Expecting value", "", 0))

        r = client.post("/chat", json={
            "query": "测试", "max_steps": 2, "stream": True,
        })

        assert r.status_code == 200
        assert "出错" in r.text or "Expecting value" in r.text


# ── 下游不可用 ──────────────────────────────────────────────


class TestDownstreamFailure:

    def test_tool_execution_failure_emits_error_event(self, client, mocker):
        """向量库不可用：act 阶段抛错 → SSE 推送 error 事件"""
        chain = [
            {"text": "", "tool_calls": [{"id": "c1", "name": "search_documents",
                                          "input": {"query": "x"}}]},
        ]
        _setup(mocker, chain=chain,
               tool_side_effect=RuntimeError("ChromaDB connection refused"))

        r = client.post("/chat", json={
            "query": "测试", "max_steps": 2, "stream": True,
        })

        assert r.status_code == 200
        events = _parse_sse_events(r.text)
        assert any(e["event"] == "error" for e in events), \
            [e["event"] for e in events]

    def test_tool_failure_non_stream_returns_5xx(self, client, mocker):
        """向量库不可用（非流式）：返回 5xx 而不是挂起"""
        chain = [
            {"text": "", "tool_calls": [{"id": "c1", "name": "search_documents",
                                          "input": {"query": "x"}}]},
        ]
        _setup(mocker, chain=chain,
               tool_side_effect=RuntimeError("ChromaDB connection refused"))

        r = client.post("/chat", json={
            "query": "测试", "max_steps": 2, "stream": False,
        })

        assert 500 <= r.status_code < 600


# ── 输入边界 ────────────────────────────────────────────────


class TestInputBoundaries:

    def test_min_length_query_accepted(self, client, mocker):
        """query 下界：1 个字符可通过校验"""
        _setup_direct_answer(mocker)

        r = client.post("/chat", json={
            "query": "a", "max_steps": 1, "stream": False,
        })

        assert r.status_code == 200

    def test_max_length_query_accepted(self, client, mocker):
        """query 上界：4000 字符可通过校验"""
        _setup_direct_answer(mocker)

        r = client.post("/chat", json={
            "query": "q" * 4000, "max_steps": 1, "stream": False,
        })

        assert r.status_code == 200

    def test_over_max_length_rejected(self, client):
        """query 越界：4001 字符被拒绝"""
        r = client.post("/chat", json={
            "query": "q" * 4001, "stream": False,
        })

        assert r.status_code == 422

    @pytest.mark.parametrize("max_steps", [0, 11])
    def test_max_steps_out_of_range_rejected(self, client, max_steps):
        """max_steps 越界：0 与 11 都被拒绝"""
        r = client.post("/chat", json={
            "query": "测试", "max_steps": max_steps, "stream": False,
        })

        assert r.status_code == 422
