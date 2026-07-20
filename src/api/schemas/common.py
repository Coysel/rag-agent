"""
通用 Schema — 健康检查、管理操作等
"""
from pydantic import BaseModel, Field


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


class AddDocumentRequest(BaseModel):
    """添加文档请求（Admin 端点用）"""
    content: str = Field(..., description="文档正文", min_length=1)
    title: str = Field(..., description="文档标题", min_length=1)
    source: str = Field(default="", description="来源路径（可选）")
