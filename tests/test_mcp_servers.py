"""
MCP 工具 Server 测试 — 文档检索 / SQLite 查询 / 联网搜索

覆盖三个 Server 的 impl 纯函数层：
  - search_documents_impl / get_document_impl
  - execute_query_impl 的只读白名单与危险关键字拦截
  - _search_sync 的 Key 缺失、业务错误码、HTTP 错误与超时

不启动 MCP 进程，不访问真实网络与向量库。
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import pytest

from src.mcp import doc_server, sqlite_server, web_server


# ── doc_server ──────────────────────────────────────────────


class TestDocServer:

    def test_search_returns_ranked_results(self, mocker):
        """检索命中：按 rank 返回，score 取 rrf_score"""
        docs = [
            {"id": "d1", "title": "文档一", "source": "a.txt",
             "content": "内容一", "rrf_score": 0.9},
            {"id": "d2", "title": "文档二", "source": "b.txt",
             "content": "内容二", "rrf_score": 0.5},
        ]
        mocker.patch("src.retrieval.pipeline.retrieve", return_value=docs)

        payload = json.loads(doc_server.search_documents_impl("查询"))

        assert payload["total"] == 2
        assert [r["rank"] for r in payload["results"]] == [1, 2]
        assert payload["results"][0]["id"] == "d1"
        assert payload["results"][0]["score"] == 0.9

    def test_search_empty_returns_message(self, mocker):
        """无命中：返回空列表与提示文案"""
        mocker.patch("src.retrieval.pipeline.retrieve", return_value=[])

        payload = json.loads(doc_server.search_documents_impl("无命中查询"))

        assert payload["results"] == []
        assert "未找到" in payload["message"]

    def test_search_retrieval_failure_returns_error_json(self, mocker):
        """向量库不可用：工具返回结构化错误，不向上抛异常"""
        mocker.patch("src.retrieval.pipeline.retrieve",
                     side_effect=RuntimeError("ChromaDB connection refused"))

        payload = json.loads(doc_server.search_documents_impl("查询"))

        assert "ChromaDB connection refused" in payload["error"]

    def test_get_document_returns_full_content(self, mocker):
        """按 ID 获取完整父文档"""
        mock_pr = mocker.patch("src.retrieval.parent_retriever.get_parent_retriever")
        mock_pr.return_value.get_parent_doc.return_value = {
            "id": "p1", "title": "父文档", "source": "x.txt", "content": "完整内容",
        }

        payload = json.loads(doc_server.get_document_impl("p1"))

        assert payload["id"] == "p1"
        assert payload["content"] == "完整内容"

    def test_get_document_missing_returns_error(self, mocker):
        """文档不存在：返回明确错误而不是空对象"""
        mock_pr = mocker.patch("src.retrieval.parent_retriever.get_parent_retriever")
        mock_pr.return_value.get_parent_doc.return_value = None

        payload = json.loads(doc_server.get_document_impl("不存在"))

        assert payload["error"] == "文档不存在"

    def test_get_document_internal_failure_returns_error(self, mocker):
        """索引损坏：异常被兜住并转为 JSON 错误"""
        mock_pr = mocker.patch("src.retrieval.parent_retriever.get_parent_retriever")
        mock_pr.return_value.get_parent_doc.side_effect = RuntimeError("index corrupted")

        payload = json.loads(doc_server.get_document_impl("p1"))

        assert "index corrupted" in payload["error"]


# ── sqlite_server ───────────────────────────────────────────


class TestSQLiteServer:

    @pytest.fixture
    def temp_db(self, tmp_path):
        db = tmp_path / "knowledge.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE courses (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO courses (name) VALUES ('线性代数')")
        conn.commit()
        conn.close()
        return str(db)

    def test_select_returns_rows(self, temp_db):
        """合法 SELECT：返回列名、行数据与计数"""
        payload = json.loads(sqlite_server.execute_query_impl(
            "SELECT id, name FROM courses", db_path=temp_db))

        assert payload["columns"] == ["id", "name"]
        assert payload["row_count"] == 1
        assert payload["rows"][0]["name"] == "线性代数"

    @pytest.mark.parametrize("sql", [
        "DELETE FROM courses",
        "UPDATE courses SET name = 'x'",
        "INSERT INTO courses (name) VALUES ('x')",
    ])
    def test_non_select_rejected(self, sql, temp_db):
        """非 SELECT 语句：在读操作入口被拦截"""
        payload = json.loads(sqlite_server.execute_query_impl(sql, db_path=temp_db))

        assert "仅允许 SELECT" in payload["error"]

    @pytest.mark.parametrize("keyword", ["DROP", "ALTER", "CREATE", "ATTACH"])
    def test_dangerous_keyword_after_select_rejected(self, keyword, temp_db):
        """SELECT 后拼接危险语句：按关键字拦截"""
        sql = f"SELECT 1; {keyword} TABLE courses"
        payload = json.loads(sqlite_server.execute_query_impl(sql, db_path=temp_db))

        assert f"不允许包含 {keyword}" in payload["error"]

    def test_unknown_table_returns_error(self, temp_db):
        """查询不存在的表：返回数据库原始错误信息"""
        payload = json.loads(sqlite_server.execute_query_impl(
            "SELECT * FROM missing_table", db_path=temp_db))

        assert "missing_table" in payload["error"]

    def test_list_tables(self, temp_db):
        """列出表名"""
        payload = json.loads(sqlite_server.list_tables_impl(db_path=temp_db))

        assert "courses" in payload["tables"]
        assert payload["count"] >= 1

    def test_truncates_at_100_rows(self, tmp_path):
        """超过 100 行时截断并标记 truncated"""
        db = tmp_path / "big.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.executemany("INSERT INTO t (id) VALUES (?)", [(i,) for i in range(150)])
        conn.commit()
        conn.close()

        payload = json.loads(sqlite_server.execute_query_impl(
            "SELECT * FROM t", db_path=str(db)))

        assert payload["row_count"] == 150
        assert len(payload["rows"]) == 100
        assert payload["truncated"] is True


# ── web_server ──────────────────────────────────────────────


class TestWebServer:

    def test_missing_api_key_returns_hint(self, mocker):
        """未配置 Key：返回配置指引而不是发起请求"""
        mocker.patch.object(web_server, "_get_api_key", return_value="")

        payload = json.loads(web_server._search_sync("查询", 5))

        assert "BAIDU_API_KEY" in payload["error"]

    def test_success_returns_results(self, mocker):
        """正常响应：标题、链接、摘要完整映射"""
        mocker.patch.object(web_server, "_get_api_key", return_value="fake-key")
        resp = mocker.Mock()
        resp.raise_for_status = mocker.Mock()
        resp.json.return_value = {"references": [
            {"title": "结果一", "url": "https://example.com", "content": "摘要内容",
             "snippet": "摘要", "website": "example.com"},
        ]}
        mock_client = mocker.patch("httpx.Client")
        mock_client.return_value.__enter__.return_value.post.return_value = resp

        payload = json.loads(web_server._search_sync("查询", 5))

        assert payload["total"] == 1
        assert payload["results"][0]["title"] == "结果一"
        assert payload["results"][0]["url"] == "https://example.com"
        assert payload["query"] == "查询"

    def test_business_error_code_surfaces(self, mocker):
        """HTTP 200 但业务失败：错误码透出到 error 字段"""
        mocker.patch.object(web_server, "_get_api_key", return_value="fake-key")
        resp = mocker.Mock()
        resp.raise_for_status = mocker.Mock()
        resp.json.return_value = {"code": 16, "message": "quota exceeded"}
        mock_client = mocker.patch("httpx.Client")
        mock_client.return_value.__enter__.return_value.post.return_value = resp

        payload = json.loads(web_server._search_sync("查询", 5))

        assert "code=16" in payload["error"]
        assert "quota exceeded" in payload["error"]

    def test_http_error_reports_status_and_detail(self, mocker):
        """HTTP 503：返回状态码与响应正文摘要"""
        mocker.patch.object(web_server, "_get_api_key", return_value="fake-key")
        req = httpx.Request("POST", web_server._BAIDU_SEARCH_URL)
        err_resp = httpx.Response(503, text="upstream down", request=req)
        resp = mocker.Mock()
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503", request=req, response=err_resp)
        mock_client = mocker.patch("httpx.Client")
        mock_client.return_value.__enter__.return_value.post.return_value = resp

        payload = json.loads(web_server._search_sync("查询", 5))

        assert "HTTP 503" in payload["error"]
        assert "upstream down" in payload["error"]

    def test_timeout_returns_friendly_error(self, mocker):
        """请求超时：返回可读的提示文案"""
        mocker.patch.object(web_server, "_get_api_key", return_value="fake-key")
        resp = mocker.Mock()
        resp.raise_for_status.side_effect = httpx.TimeoutException("timeout")
        mock_client = mocker.patch("httpx.Client")
        mock_client.return_value.__enter__.return_value.post.return_value = resp

        payload = json.loads(web_server._search_sync("查询", 5))

        assert "超时" in payload["error"]

    def test_max_results_clamped_to_20(self, mocker):
        """max_results 上界：超过 20 时收敛为 20 后再发给 API"""
        mocker.patch.object(web_server, "_get_api_key", return_value="fake-key")
        resp = mocker.Mock()
        resp.raise_for_status = mocker.Mock()
        resp.json.return_value = {"references": []}
        mock_client = mocker.patch("httpx.Client")
        post = mock_client.return_value.__enter__.return_value.post
        post.return_value = resp

        web_server._search_sync("查询", 100)

        assert post.call_args.kwargs["json"]["resource_type_filter"][0]["top_k"] == 20
