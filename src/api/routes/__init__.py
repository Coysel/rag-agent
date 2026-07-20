"""
路由聚合 — 所有子路由在此注册到主应用

用法:
    from src.api.routes import register_routes
    register_routes(app)
"""
from fastapi import FastAPI


def register_routes(app: FastAPI):
    """注册所有子路由到 FastAPI 应用"""
    from src.api.routes.health import router as health_router
    from src.api.routes.chat import router as chat_router
    from src.api.routes.eval import router as eval_router
    from src.api.routes.documents import router as documents_router
    from src.api.routes.admin import router as admin_router
    from src.api.routes.categories import router as categories_router
    from src.api.routes.frontend import setup_frontend

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(eval_router)
    app.include_router(documents_router)
    app.include_router(admin_router)
    app.include_router(categories_router)

    # 前端静态文件（挂载在 /）
    setup_frontend(app)
