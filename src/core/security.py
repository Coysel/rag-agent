"""
安全模块 — API Key 鉴权

提供:
  - verify_admin_key: FastAPI Depends 注入，验证 Admin API Key
  - get_admin_key: 读取配置中的 Admin Key

用法:
    @router.delete("/admin/documents/{id}")
    async def delete(id: str, _=Depends(verify_admin_key)):
        ...
"""
from fastapi import Header

from config import ADMIN_API_KEY
from src.core.exceptions import UnauthorizedError


def get_admin_key() -> str:
    """获取 Admin API Key（从 config settings，可被环境变量覆盖）"""
    return ADMIN_API_KEY


def verify_admin_key(x_admin_key: str = Header(None, alias="X-Admin-Key")) -> str:
    """
    FastAPI 依赖 — 验证 Admin API Key

    Raises:
        UnauthorizedError(401): Key 无效或缺失
    """
    admin_key = get_admin_key()
    if not admin_key or not x_admin_key or x_admin_key != admin_key:
        raise UnauthorizedError("无效的 Admin API Key")
    return x_admin_key
