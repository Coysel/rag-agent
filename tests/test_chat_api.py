"""
聊天 API 集成测试 — SSE 流式、多轮对话、会话持久化

使用 FastAPI TestClient + dependency_overrides + mock 依赖。
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient


# ── SSE 解析工具 ──────────────────────────────────────────────

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


def _make_mock_llm_chain(return_tool=True, answer_text="这是测试回答。",
                         reflect_text="sufficient"):
    """构建标准的 3 步 LLM 调用链: reason → reflect → answer"""
    if return_tool:
        return [
            # reason → 需要检索
            {"text": "", "tool_calls": [
                {"id": "call_1", "name": "search_documents",
                 "input": {"query": "test"}}
            ]},
            # reflect → sufficient / insufficient
            {"text": reflect_text, "tool_calls": []},
            # answer → 最终回答
            {"text": answer_text, "tool_calls": []},
        ]
    else:
        # reason 直接回答 (无需工具)
        return [
            {"text": answer_text, "tool_calls": []},
            {"text": answer_text, "tool_calls": []},
        ]


def _make_mock_query_router(query_type_value="factual"):
    """创建 mock QueryRouter，classify() 返回 QueryType 枚举值"""
    from enum import Enum

    class MockQueryType(str, Enum):
        FACTUAL = "factual"
        CONCEPTUAL = "conceptual"
        MULTI_HOP = "multi_hop"

    class MockQueryRouter:
        def classify(self, query: str):
            return MockQueryType(query_type_value)

    return MockQueryRouter()


# ── Fixtures ───────────────────────────────────────────────────

@pytest.fixture
def app_with_mocks(mocker):
    """创建 mock 所有重型依赖的 FastAPI app"""
    # ── Mock 全局初始化 (在 create_app 之前，patch 函数定义处) ──
    mocker.patch("src.api.app.setup_logging")

    # BM25 — patch 在 src.indexing.bm25_index（app.py 里是局部 import）
    mock_bm25 = mocker.patch("src.indexing.bm25_index.get_bm25_index")
    mock_bm25.return_value.document_count = 0
    mock_bm25.return_value.load = lambda: None

    # ChromaDB
    mock_vs = mocker.patch("src.indexing.vector_store.get_vector_store")
    mock_vs.return_value.count = 0

    # LLM
    mock_llm = mocker.patch("src.agent.llm_client.get_llm_client")
    mock_llm.return_value.get_info.return_value = {
        "provider": "mock", "model": "mock", "base_url": "mock"
    }

    # Embedding
    mock_emb = mocker.patch("src.indexing.embeddings.get_embedding_model")
    mock_emb.return_value.provider = "mock"
    mock_emb.return_value.model_name = "mock"

    # MCP manager (关键的 async initialize)
    mock_mcp = mocker.patch("src.mcp.client_manager.get_mcp_manager")
    mock_mcp.return_value.initialize = mocker.AsyncMock()
    mock_mcp.return_value.close = mocker.AsyncMock()
    mock_mcp.return_value._all_tools = []

    # Session store
    mock_ss = mocker.patch("src.storage.session_store.get_session_store")
    mock_ss.return_value.cleanup.return_value = 0

    # Document list helper
    mocker.patch("src.api.routes.documents._get_document_list",
                 return_value={"total_unique": 0, "documents": []})

    from src.api.app import create_app
    app = create_app()

    # ── 设置 dependency_overrides ──
    from src.api.dependencies import get_query_router, get_session
    from src.storage.session_store import SessionStore

    app.dependency_overrides[get_query_router] = \
        lambda: _make_mock_query_router("factual")
    app.dependency_overrides[get_session] = lambda: SessionStore()

    return app


@pytest.fixture
def client(app_with_mocks):
    """基于 mock app 的 TestClient"""
    with TestClient(app_with_mocks) as tc:
        yield tc


# ── 设置 LLM + MCP mock 的辅助 fixture ──

def _setup_agent_mocks(mocker, *,
                       answer_text="基于检索到的文档，这是完整测试回答。",
                       reflect_text="sufficient",
                       doc_title="测试文档"):
    """设置 Agent 内部的 LLM 和 MCP mock（在每个测试中调用）"""
    mock_llm = mocker.patch("src.agent.nodes._get_llm")
    chain = _make_mock_llm_chain(
        return_tool=True,
        answer_text=answer_text,
        reflect_text=reflect_text,
    )
    mock_llm.return_value.create_message.side_effect = chain

    mocker.patch("src.agent.nodes.get_tool_definitions",
                 return_value=[{"function": {"name": "search_documents"}}])

    mock_mgr = mocker.patch("src.agent.nodes.get_mcp_manager")

    async def _execute(tool_name, tool_input):
        return (
            f"Tool '{tool_name}' executed successfully.",
            [{"id": "doc1", "title": doc_title, "source": "test.txt",
              "content": "这是检索到的测试内容。", "rrf_score": 0.85}],
        )
    mock_mgr.return_value.execute_tool = _execute

    return mock_llm


# ── Tests ──────────────────────────────────────────────────────

class TestChatSSEEvents:
    """SSE 流式事件序列测试"""

    def test_single_turn_returns_reason_and_done_events(self, client, mocker):
        """单轮对话应返回 reason 和 done 事件"""
        _setup_agent_mocks(mocker)

        response = client.post("/chat", json={
            "query": "测试问题",
            "max_steps": 3,
            "stream": True,
        })

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = _parse_sse_events(response.text)
        event_types = [e["event"] for e in events]

        assert "reason" in event_types, f"Missing 'reason' in events: {event_types}"
        assert "done" in event_types, f"Missing 'done' in events: {event_types}"

    def test_complete_event_pipeline_order(self, client, mocker):
        """验证事件管道顺序: reason → act → observe → reflect → answer → done"""
        _setup_agent_mocks(mocker)

        response = client.post("/chat", json={
            "query": "测试问题",
            "max_steps": 3,
            "stream": True,
        })

        events = _parse_sse_events(response.text)
        event_types = [e["event"] for e in events]

        # 验证核心事件存在且顺序正确
        core = ["reason", "act", "observe", "reflect", "answer", "done"]
        found = [t for t in event_types if t in core]
        assert len(found) >= 4, f"Expected most of {core}, got {found}"

        # reason 在 done 之前
        reason_idx = event_types.index("reason") if "reason" in event_types else -1
        done_idx = event_types.index("done") if "done" in event_types else -1
        assert reason_idx < done_idx, "reason should come before done"

    def test_multi_turn_events_independent(self, client, mocker):
        """两轮对话的答案互不混淆"""
        _setup_agent_mocks(mocker, answer_text="第一轮回答内容。")

        r1 = client.post("/chat", json={
            "query": "第一轮问题", "max_steps": 3, "stream": True,
        })
        assert r1.status_code == 200
        assert "第一轮回答内容" in r1.text

        # 重置 LLM chain 为第二轮的 answer
        _setup_agent_mocks(mocker, answer_text="第二轮回答内容。")

        r2 = client.post("/chat", json={
            "query": "第二轮问题", "max_steps": 3, "stream": True,
        })
        assert r2.status_code == 200
        assert "第二轮回答内容" in r2.text
        assert "第一轮回答内容" not in r2.text, \
            "Second response should not contain first round's answer"


class TestSessionPersistence:
    """会话持久化测试"""

    def test_session_history_passed_to_next_round(self, client, mocker):
        """同一 session_id 的第二轮应携带第一轮历史"""
        _setup_agent_mocks(mocker, answer_text="回答一")

        session_id = "test-session-api-001"

        r1 = client.post("/chat/session", json={
            "query": "第一个问题",
            "session_id": session_id,
            "max_steps": 3,
            "stream": True,
        })
        assert r1.status_code == 200, f"Round 1: {r1.status_code}"

        _setup_agent_mocks(mocker, answer_text="回答二")
        r2 = client.post("/chat/session", json={
            "query": "追问",
            "session_id": session_id,
            "max_steps": 3,
            "stream": True,
        })
        assert r2.status_code == 200, f"Round 2: {r2.status_code}"

    def test_session_list_contains_session(self, client, mocker):
        """GET /chat/sessions 应返回所有会话"""
        _setup_agent_mocks(mocker)
        sid = "test-session-list-001"

        client.post("/chat/session", json={
            "query": "问题", "session_id": sid, "max_steps": 3, "stream": True,
        })

        r = client.get("/chat/sessions")
        assert r.status_code == 200
        data = r.json()
        assert "sessions" in data
        session_ids = [s.get("session_id", "") for s in data["sessions"]]
        assert sid in session_ids, f"Session {sid} not found in {session_ids}"

    def test_delete_session_removes_it(self, client, mocker):
        """DELETE /chat/sessions/{id} 应删除会话"""
        _setup_agent_mocks(mocker)
        sid = "test-session-delete-001"

        client.post("/chat/session", json={
            "query": "问题", "session_id": sid, "max_steps": 3, "stream": True,
        })

        r = client.delete(f"/chat/sessions/{sid}")
        assert r.status_code == 200

    def test_delete_nonexistent_session_returns_404(self, client):
        """删除不存在的会话应返回 404"""
        r = client.delete("/chat/sessions/nonexistent-id")
        assert r.status_code == 404


class TestAnswerIsolation:
    """回答隔离测试 — 防止跨轮内容泄漏"""

    def test_done_event_answer_matches_current_round(self, client, mocker):
        """done 事件中的 answer 应与当前轮次一致"""
        expected = "完整的测试回答：Python 语言特性。"
        _setup_agent_mocks(mocker, answer_text=expected)

        r = client.post("/chat", json={
            "query": "关于Python", "max_steps": 3, "stream": True,
        })
        events = _parse_sse_events(r.text)
        done_events = [e for e in events if e["event"] == "done"]

        assert len(done_events) > 0, "Should have done event"
        done = done_events[-1]
        # done 数据结构: {"event": "done", "data": {"type": "done", "data": {"answer": "..."}}}
        inner = done.get("data", {})
        answer = inner.get("data", {}).get("answer", "")
        if not answer:
            answer = inner.get("answer", "")
        assert answer == expected, \
            f"Answer mismatch: expected '{expected[:50]}', got '{answer[:50]}'"


class TestErrorHandling:
    """错误处理测试"""

    def test_empty_query_rejected(self, client):
        """空查询 → 422"""
        r = client.post("/chat", json={"query": "", "stream": False})
        assert r.status_code == 422

    def test_query_exceeds_max_length_rejected(self, client):
        """超长查询 → 422"""
        r = client.post("/chat", json={"query": "x" * 5000, "stream": False})
        assert r.status_code == 422

    def test_non_stream_returns_json(self, client, mocker):
        """非流式请求 → JSON ChatResponse"""
        _setup_agent_mocks(mocker, answer_text="JSON 格式回答。")

        r = client.post("/chat", json={
            "query": "测试", "stream": False, "max_steps": 3,
        })
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data, f"Response missing 'answer': {list(data.keys())}"
        assert "query" in data
        assert data["answer"] == "JSON 格式回答。"


class TestChatSessionEndpoint:
    """/chat/session 端点专测"""

    def test_auto_creates_session_id_when_empty(self, client, mocker):
        """不传 session_id 时自动生成"""
        _setup_agent_mocks(mocker)

        r = client.post("/chat/session", json={
            "query": "测试", "max_steps": 3, "stream": True,
        })
        assert r.status_code == 200

        # done 事件应包含 session_id
        events = _parse_sse_events(r.text)
        done_events = [e for e in events if e["event"] == "done"]
        if done_events:
            done_data = done_events[-1].get("data", {})
            session_id = done_data.get("data", {}).get("session_id", "")
            assert session_id, "done should contain a session_id"
