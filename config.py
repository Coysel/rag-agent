"""
全局配置 — 集中管理所有可调参数，基于 pydantic-settings 自动验证

特性:
  - 自动从 .env 文件加载
  - 类型校验（端口必为 int，目录必为 Path）
  - 模块级导出向后兼容（from config import API_PORT 仍可用）
"""
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 先将 .env 全部注入 os.environ（供 sentence-transformers/huggingface_hub 等三方库使用）
load_dotenv()


class Settings(BaseSettings):
    """所有配置项集中于此，pydantic 自动校验类型"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略 .env 中的未知项
    )

    # ── 项目路径 ───────────────────────────────────────────
    BASE_DIR: Path = Field(default=Path(__file__).parent)
    DATA_DIR: Path = Field(default=Path(__file__).parent / "data")
    DOCUMENTS_DIR: Path = Field(default=Path(__file__).parent / "data" / "documents")
    CHROMA_DIR: Path = Field(default=Path(__file__).parent / "data" / "chroma_db")
    BM25_INDEX_PATH: Path = Field(default=Path(__file__).parent / "data" / "bm25_index.pkl")
    SQLITE_DB_PATH: Path = Field(default=Path(__file__).parent / "data" / "knowledge.db")

    # ── API Keys ────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    VOYAGE_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""

    # ── Admin Key ───────────────────────────────────────────
    ADMIN_API_KEY: str = "admin-secret-change-me"

    # ── LLM 提供商 ──────────────────────────────────────────
    LLM_PROVIDER: str = "deepseek"  # "deepseek" | "anthropic"

    # ── Embedding 配置 ──────────────────────────────────────
    EMBEDDING_PROVIDER: str = "local"  # "local" | "openai" | "voyage"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    HF_ENDPOINT: str = "https://huggingface.co"  # 国内用户设 https://hf-mirror.com

    # ── Claude 模型 ─────────────────────────────────────────
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # ── DeepSeek 模型 ───────────────────────────────────────
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # ── 文档分块参数 ────────────────────────────────────────
    CHILD_CHUNK_SIZE: int = 256
    PARENT_CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 50

    # ── 检索参数 ────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = 10
    HYBRID_TOP_K: int = 8
    RRF_K: int = 60
    DENSE_WEIGHT: float = 1.0
    SPARSE_WEIGHT: float = 1.0

    # ── Agent 参数 ──────────────────────────────────────────
    MAX_STEPS: int = 5
    TEMPERATURE: float = 0.3

    # ── 文档分类参数 ────────────────────────────────────────
    CATEGORY_SUMMARY_MODEL: str = "deepseek-chat"
    AUTO_CATEGORIZE_ON_UPLOAD: bool = True  # 上传文档后自动摘要+分类

    # ── 联网搜索参数 ────────────────────────────────────────
    WEB_SEARCH_ENABLED: bool = True          # 是否启用联网搜索
    WEB_SEARCH_MAX_RESULTS: int = 5          # 每次搜索返回条数 (1-10)
    WEB_SEARCH_TIMEOUT: int = 10             # 搜索超时秒数

    # ── Token 截断参数 ──────────────────────────────────────
    MAX_CONTEXT_TOKENS: int = 80000

    # ── 服务器参数 ──────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001

    # ── CORS 配置 ───────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:8001,http://127.0.0.1:8001"

    # ── 速率限制 ────────────────────────────────────────────
    RATE_LIMIT_CHAT_PER_MINUTE: int = 30
    RATE_LIMIT_EVAL_PER_MINUTE: int = 10


# ── 单例实例 ────────────────────────────────────────────────
_settings = Settings()


# ── 模块级导出（向后兼容 from config import XXX）────────────
BASE_DIR = _settings.BASE_DIR
DATA_DIR = _settings.DATA_DIR
DOCUMENTS_DIR = _settings.DOCUMENTS_DIR
CHROMA_DIR = _settings.CHROMA_DIR
BM25_INDEX_PATH = _settings.BM25_INDEX_PATH
SQLITE_DB_PATH = _settings.SQLITE_DB_PATH

ANTHROPIC_API_KEY = _settings.ANTHROPIC_API_KEY
OPENAI_API_KEY = _settings.OPENAI_API_KEY
VOYAGE_API_KEY = _settings.VOYAGE_API_KEY
DEEPSEEK_API_KEY = _settings.DEEPSEEK_API_KEY
ADMIN_API_KEY = _settings.ADMIN_API_KEY

LLM_PROVIDER = _settings.LLM_PROVIDER

EMBEDDING_PROVIDER = _settings.EMBEDDING_PROVIDER
EMBEDDING_MODEL = _settings.EMBEDDING_MODEL
LOCAL_EMBEDDING_MODEL = _settings.LOCAL_EMBEDDING_MODEL
HF_ENDPOINT = _settings.HF_ENDPOINT

CLAUDE_MODEL = _settings.CLAUDE_MODEL

DEEPSEEK_MODEL = _settings.DEEPSEEK_MODEL
DEEPSEEK_BASE_URL = _settings.DEEPSEEK_BASE_URL

CHILD_CHUNK_SIZE = _settings.CHILD_CHUNK_SIZE
PARENT_CHUNK_SIZE = _settings.PARENT_CHUNK_SIZE
CHUNK_OVERLAP = _settings.CHUNK_OVERLAP

RETRIEVAL_TOP_K = _settings.RETRIEVAL_TOP_K
HYBRID_TOP_K = _settings.HYBRID_TOP_K
RRF_K = _settings.RRF_K
DENSE_WEIGHT = _settings.DENSE_WEIGHT
SPARSE_WEIGHT = _settings.SPARSE_WEIGHT

MAX_STEPS = _settings.MAX_STEPS
TEMPERATURE = _settings.TEMPERATURE

CATEGORY_SUMMARY_MODEL = _settings.CATEGORY_SUMMARY_MODEL
AUTO_CATEGORIZE_ON_UPLOAD = _settings.AUTO_CATEGORIZE_ON_UPLOAD

WEB_SEARCH_ENABLED = _settings.WEB_SEARCH_ENABLED
WEB_SEARCH_MAX_RESULTS = _settings.WEB_SEARCH_MAX_RESULTS
WEB_SEARCH_TIMEOUT = _settings.WEB_SEARCH_TIMEOUT

MAX_CONTEXT_TOKENS = _settings.MAX_CONTEXT_TOKENS

API_HOST = _settings.API_HOST
API_PORT = _settings.API_PORT

CORS_ORIGINS = _settings.CORS_ORIGINS

RATE_LIMIT_CHAT_PER_MINUTE = _settings.RATE_LIMIT_CHAT_PER_MINUTE
RATE_LIMIT_EVAL_PER_MINUTE = _settings.RATE_LIMIT_EVAL_PER_MINUTE


def get_settings() -> Settings:
    """获取验证后的配置单例（新代码推荐使用此接口）"""
    return _settings
