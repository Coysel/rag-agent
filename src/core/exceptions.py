"""
自定义异常类 + 全局异常处理器

统一错误响应格式:
    {"error": {"code": "...", "message": "...", "detail": "..."}}

用法:
    raise AppException(code="DOCUMENT_NOT_FOUND", message="文档不存在", status_code=404)

在 app 工厂中注册:
    app.add_exception_handler(AppException, app_exception_handler)
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """业务异常基类 — 所有业务层错误都应抛出此类或其子类"""

    def __init__(
        self,
        code: str = "INTERNAL_ERROR",
        message: str = "服务器内部错误",
        detail: str = "",
        status_code: int = 500,
    ):
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)


# ── 常用异常子类 ────────────────────────────────────────────


class NotFoundError(AppException):
    """资源不存在 (404)"""

    def __init__(self, resource: str = "资源", detail: str = ""):
        super().__init__(
            code=f"{resource.upper().replace(' ', '_')}_NOT_FOUND",
            message=f"{resource}不存在",
            detail=detail,
            status_code=404,
        )


class ValidationError(AppException):
    """参数校验失败 (422)"""

    def __init__(self, message: str = "参数无效", detail: str = ""):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            detail=detail,
            status_code=422,
        )


class UnauthorizedError(AppException):
    """未授权 (401)"""

    def __init__(self, message: str = "未授权访问"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
        )


class ServiceUnavailableError(AppException):
    """服务不可用 (503)"""

    def __init__(self, message: str = "服务暂时不可用", detail: str = ""):
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=message,
            detail=detail,
            status_code=503,
        )


# ── 全局异常处理器 ──────────────────────────────────────────


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理 AppException 及其子类"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未预期的异常（兜底）"""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "detail": str(exc) if __debug__ else "",
            }
        },
    )
