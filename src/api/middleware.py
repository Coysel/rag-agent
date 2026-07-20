"""
中间件 — 请求日志、计时、Correlation ID、CORS、速率限制、安全头

功能:
  - 每个请求自动注入 correlation_id
  - 自动记录请求方法、路径、耗时、状态码
  - 基于滑动窗口的速率限制（按路由类别分档）
  - CORS 配置（从 config 读取允许的来源）
  - 安全响应头（CSP, X-Frame-Options, X-Content-Type-Options, HSTS）
"""
import time
from collections import defaultdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from config import CORS_ORIGINS, RATE_LIMIT_CHAT_PER_MINUTE, RATE_LIMIT_EVAL_PER_MINUTE
from src.utils.logging import set_correlation_id, get_logger


# ── 速率限制器 ────────────────────────────────────────────────


class RateLimiter:
    """基于滑动窗口的内存速率限制器"""

    def __init__(self):
        # { "category": { "client_ip": [timestamp, ...] } }
        self._buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_category(self, request: Request) -> str:
        """根据路由确定速率限制类别"""
        path = request.url.path
        if path.startswith("/chat") or path == "/chat/session":
            return "chat"
        if path.startswith("/eval"):
            return "eval"
        return "default"

    def is_allowed(self, request: Request) -> tuple[bool, int]:
        """
        检查请求是否在速率限制内

        Returns:
            (allowed, retry_after_seconds)
        """
        category = self._get_category(request)
        ip = self._get_client_ip(request)

        # 各类别限制 (per minute)
        limits = {
            "chat": RATE_LIMIT_CHAT_PER_MINUTE,
            "eval": RATE_LIMIT_EVAL_PER_MINUTE,
            "default": 60,
        }
        limit = limits.get(category, 60)

        now = time.monotonic()
        window = 60.0  # 1 minute

        # 清理过期记录 + 检查
        timestamps = self._buckets[category][ip]
        timestamps[:] = [t for t in timestamps if now - t < window]

        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1, int(window - (now - oldest)))
            return False, retry_after

        timestamps.append(now)
        return True, 0

    def cleanup(self):
        """清理所有过期的记录（可定期调用，避免内存泄漏）"""
        now = time.monotonic()
        window = 120.0
        for cat in self._buckets:
            for ip in list(self._buckets[cat].keys()):
                self._buckets[cat][ip][:] = [t for t in self._buckets[cat][ip] if now - t < window]
                if not self._buckets[cat][ip]:
                    del self._buckets[cat][ip]


# 全局单例
_rate_limiter = RateLimiter()


# ── 安全响应头 ────────────────────────────────────────────────


def _add_security_headers(response: Response):
    """在生产环境中添加安全加固头"""
    # CSP: 默认仅允许同源，script/style 允许内联（无构建工具的 SPA 需要）
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self' data:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"


# ── 请求日志中间件 ────────────────────────────────────────────


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """为每个请求注入 correlation_id、检查速率限制、记录访问日志"""

    ignored_paths = {"/health", "/docs", "/redoc", "/openapi.json", "/static"}

    async def dispatch(self, request: Request, call_next):
        cid = set_correlation_id()
        logger = get_logger()
        t0 = time.time()

        # 速率限制（跳过静态文件和文档）
        if request.url.path not in self.ignored_paths and not request.url.path.startswith("/static"):
            allowed, retry_after = _rate_limiter.is_allowed(request)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "请求过于频繁，请稍后重试",
                            "detail": f"请在 {retry_after} 秒后重试",
                        }
                    },
                    headers={"Retry-After": str(retry_after)},
                )

        response: Response = await call_next(request)

        elapsed_ms = round((time.time() - t0) * 1000)
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} | {elapsed_ms}ms"
        )

        response.headers["X-Correlation-Id"] = cid
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        _add_security_headers(response)
        return response


# ── 中间件注册 ─────────────────────────────────────────────────


def setup_middleware(app: FastAPI):
    """注册所有中间件（顺序由下到上执行）"""

    # CORS — 从配置读取允许来源，开发环境默认 localhost
    origins = CORS_ORIGINS.split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins if o.strip()],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Admin-Key", "X-Correlation-Id"],
        expose_headers=["X-Correlation-Id", "X-Response-Time-Ms", "Retry-After"],
    )

    # 请求日志 + 速率限制 + 安全头
    app.add_middleware(RequestLoggingMiddleware)
