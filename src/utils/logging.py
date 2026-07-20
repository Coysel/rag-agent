"""
结构化日志 — 基于 loguru 的统一日志系统

提供:
  - 请求级 correlation_id 追踪
  - 节点级耗时记录
  - 生产环境 JSON 格式输出

用法:
    from src.utils.logging import get_logger, set_correlation_id

    logger = get_logger()
    logger.info("something happened")

    with correlation_context(cid):
        logger.info("this will carry the correlation_id")
"""
import sys
import uuid
from contextvars import ContextVar

try:
    from loguru import logger
    HAS_LOGURU = True
except ImportError:
    import logging
    logger = logging.getLogger("rag")
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.INFO)
    HAS_LOGURU = False

# 请求级上下文变量（线程安全）
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_logger():
    """获取 logger 实例"""
    return logger


def set_correlation_id(cid: str = "") -> str:
    """设置当前请求的 correlation_id，若未提供则自动生成"""
    if not cid:
        cid = str(uuid.uuid4())[:8]
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    """获取当前请求的 correlation_id"""
    return _correlation_id.get()


def _cid_filter(record: dict) -> bool:
    """loguru filter: 注入 correlation_id"""
    cid = _correlation_id.get()
    record["extra"]["cid"] = cid if cid else "-"
    return True


def setup_logging(level: str = "INFO", json_format: bool = False):
    """
    初始化日志配置（在 main.py lifespan 中调用）

    Args:
        level: 日志级别
        json_format: 生产环境启用 JSON 格式
    """
    if not HAS_LOGURU:
        return

    logger.remove()  # 移除默认 handler

    if json_format:
        # 生产环境: JSON 格式
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | {extra[cid]} | {message}",
            filter=_cid_filter,
            level=level,
            serialize=True,  # JSON 输出
        )
    else:
        # 开发环境: 彩色文本格式
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level: <7}</level> | "
                "<cyan>{extra[cid]: <10}</cyan> | "
                "<level>{message}</level>"
            ),
            filter=_cid_filter,
            level=level,
            colorize=True,
        )
