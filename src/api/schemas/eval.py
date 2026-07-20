"""
评测相关 Schema
"""
from typing import List
from pydantic import BaseModel, Field


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
