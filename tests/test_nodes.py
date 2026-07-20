"""
Agent 节点单元测试 — mock LLM 调用
"""
import pytest


class TestReasonNode:
    """Reason 节点测试"""

    def test_direct_answer_when_no_tools(self, mocker):
        """当 LLM 不返回 tool_calls 时，应直接进入 answer"""
        from src.agent.nodes import reason_node

        # mock LLM
        mock_llm = mocker.patch("src.agent.nodes._get_llm")
        mock_llm.return_value.create_message.return_value = {
            "text": "这是一个简单问题",
            "tool_calls": [],
        }

        # mock tools
        mocker.patch(
            "src.agent.nodes.get_tool_definitions",
            return_value=[],
        )

        state = {
            "query": "你好",
            "context_docs": [],
            "step_count": 0,
            "max_steps": 5,
            "query_type": "conceptual",
            "conversation_history": [],
        }

        result = reason_node(state)
        assert result["status"] == "answer"

    def test_tool_call_when_retrieval_needed(self, mocker):
        """当 LLM 返回 tool_calls 时，应继续执行"""
        from src.agent.nodes import reason_node

        mock_llm = mocker.patch("src.agent.nodes._get_llm")
        mock_llm.return_value.create_message.return_value = {
            "text": "",
            "tool_calls": [
                {"id": "call_1", "name": "search_documents", "input": {"query": "test"}}
            ],
        }

        mocker.patch("src.agent.nodes.get_tool_definitions", return_value=[])

        state = {
            "query": "PyTorch 的参数是什么",
            "context_docs": [],
            "step_count": 0,
            "max_steps": 5,
            "query_type": "factual",
            "conversation_history": [],
        }

        result = reason_node(state)
        assert result["status"] == "continue"
        assert len(result["tool_calls"]) == 1

    def test_handles_llm_error(self, mocker):
        """LLM 异常时返回错误状态"""
        from src.agent.nodes import reason_node

        mock_llm = mocker.patch("src.agent.nodes._get_llm")
        mock_llm.return_value.create_message.side_effect = RuntimeError("API 不可用")

        mocker.patch("src.agent.nodes.get_tool_definitions", return_value=[])

        state = {
            "query": "测试", "context_docs": [],
            "step_count": 0, "max_steps": 5,
            "query_type": "", "conversation_history": [],
        }

        result = reason_node(state)
        assert result["status"] == "answer"
        assert "出错" in result.get("answer", "")


class TestObserveNode:
    """Observe 节点测试"""

    def test_dedup_by_id(self):
        from src.agent.nodes import observe_node

        state = {
            "context_docs": [
                {"id": "doc1", "title": "已有", "content": "..."},
            ],
            "tool_results": [
                {
                    "retrieved_docs": [
                        {"id": "doc1", "title": "已有", "content": "..."},  # 重复
                        {"id": "doc2", "title": "新文档", "content": "新内容"},
                    ]
                }
            ],
        }

        result = observe_node(state)
        docs = result["context_docs"]
        # doc1 不重复，doc2 新增 → 共 2 篇
        assert len(docs) == 2
        titles = {d["title"] for d in docs}
        assert titles == {"已有", "新文档"}

    def test_empty_id_skipped(self):
        """id 为空的文档应跳过（之前的关键 bug）"""
        from src.agent.nodes import observe_node

        state = {
            "context_docs": [],
            "tool_results": [
                {
                    "retrieved_docs": [
                        {"id": "", "title": "无ID", "content": "..."},  # id 为空
                        {"id": "valid", "title": "有效", "content": "..."},
                    ]
                }
            ],
        }

        result = observe_node(state)
        docs = result["context_docs"]
        assert len(docs) == 1
        assert docs[0]["title"] == "有效"


class TestReflectNode:
    """Reflect 节点测试"""

    def test_max_steps_forces_answer(self):
        from src.agent.nodes import reflect_node

        state = {
            "step_count": 5, "max_steps": 5,
            "context_docs": [{"id": "1"}],
            "status": "continue",
            "query": "测试",
        }

        result = reflect_node(state)
        assert result["status"] == "max_steps"

    def test_no_docs_continues(self):
        from src.agent.nodes import reflect_node

        state = {
            "step_count": 1, "max_steps": 5,
            "context_docs": [],
            "status": "continue",
            "query": "测试",
        }

        result = reflect_node(state)
        assert result["status"] == "continue"
