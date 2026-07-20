"""
Pydantic 数据模型 — API 请求/响应 Schema
"""
from typing import List, Optional
from pydantic import BaseModel, Field


# ── 聊天 ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """对话请求"""
    query: str = Field(..., description="用户问题", min_length=1, max_length=4000)
    max_steps: int = Field(default=5, description="ReAct 最大循环轮数", ge=1, le=10)
    stream: bool = Field(default=True, description="是否启用 SSE 流式输出")


class ChatResponse(BaseModel):
    """对话响应 (非流式)"""
    query: str = Field(..., description="原始问题")
    answer: str = Field(..., description="最终回答")
    sources: List["Source"] = Field(default_factory=list, description="引用来源列表")
    steps: int = Field(default=0, description="执行步数")
    query_type: str = Field(default="", description="查询类型")


class Source(BaseModel):
    """引用来源文档"""
    title: str = Field(..., description="文档标题")
    source: str = Field(default="", description="文档来源路径")
    score: float = Field(default=0.0, description="检索相关度分数")
    content: str = Field(default="", description="文档内容摘要")


class StepEvent(BaseModel):
    """ReAct 步骤事件 (SSE 推送)"""
    type: str = Field(..., description="事件类型: reason | act | observe | reflect | answer | done | error")
    content: str = Field(default="", description="事件内容")
    step: int = Field(default=0, description="当前步数")
    data: Optional[dict] = Field(default=None, description="附加数据")


# ── 健康检查 ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str = "1.0.0"
    index_ready: bool = False
    document_count: int = 0
    chunk_count: int = 0
    llm_provider: str = ""
    llm_model: str = ""
    embedding_provider: str = ""
    embedding_model: str = ""


# ── 评测 ─────────────────────────────────────────────────

class EvalRetrievalRequest(BaseModel):
    """检索对比请求"""
    query: str = Field(..., description="查询文本", min_length=1)


class EvalSingleRequest(BaseModel):
    """单条问答评测请求"""
    query: str = Field(..., description="问题", min_length=1)


class EvalRagasRequest(BaseModel):
    """RAGAS 评测请求 (预设测试集)"""
    count: int = Field(default=5, description="测试问题数量", ge=1, le=20)


class EvalCustomRequest(BaseModel):
    """自定义问题评测请求"""
    questions: List[str] = Field(..., description="用户输入的问题列表", min_length=1, max_length=20)
