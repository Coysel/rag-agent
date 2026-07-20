"""
聊天相关 Schema
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求"""
    query: str = Field(..., description="用户问题", min_length=1, max_length=4000)
    max_steps: int = Field(default=5, description="ReAct 最大循环轮数", ge=1, le=10)
    stream: bool = Field(default=True, description="是否启用 SSE 流式输出")
    session_id: str = Field(default="", description="多轮对话会话 ID（空则自动创建）")
    categories: list[str] = Field(default_factory=list, description="限定检索的类别 ID 列表")
    web_search: bool = Field(default=False, description="是否允许联网搜索（默认关闭）")


class Source(BaseModel):
    """引用来源文档"""
    title: str = Field(..., description="文档标题")
    source: str = Field(default="", description="文档来源路径")
    score: float = Field(default=0.0, description="检索相关度分数")
    content: str = Field(default="", description="文档内容摘要")


class ChatResponse(BaseModel):
    """对话响应 (非流式)"""
    query: str = Field(..., description="原始问题")
    answer: str = Field(..., description="最终回答")
    sources: List[Source] = Field(default_factory=list, description="引用来源列表")
    steps: int = Field(default=0, description="执行步数")
    query_type: str = Field(default="", description="查询类型")


class StepEvent(BaseModel):
    """ReAct 步骤事件 (SSE 推送)"""
    type: str = Field(..., description="事件类型: reason | act | observe | reflect | answer | done | error")
    content: str = Field(default="", description="事件内容")
    step: int = Field(default=0, description="当前步数")
    data: Optional[dict] = Field(default=None, description="附加数据")
