"""
前端页面路由 — GET /

用于挂载 frontend/ 目录为静态文件。

V2 方式:
    FastAPI StaticFiles 挂载整个 frontend/ 目录
    浏览器可正确缓存 .css/.js 文件
    支持正确的 Content-Type (text/css, application/javascript, image/svg+xml)
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse


def setup_frontend(app: FastAPI):
    """
    挂载前端静态文件目录。

    查找顺序:
      1. {PROJECT_ROOT}/frontend/  (V2 模块化前端)
      2. {PROJECT_ROOT}/src/api/frontend.html  (V1 单文件回退)
    """
    project_root = Path(__file__).parent.parent.parent.parent  # src/api/routes/ → project root
    frontend_dir = project_root / "frontend"

    if frontend_dir.is_dir():
        # V2: 多文件前端 — 挂载 StaticFiles + 返回入口 index.html
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="frontend_static")

        @app.get("/")
        async def serve_frontend():
            return FileResponse(
                str(frontend_dir / "index.html"),
                media_type="text/html; charset=utf-8",
            )
    else:
        # V1 兼容: 单文件 HTML 回退
        v1_path = project_root / "src" / "api" / "frontend.html"

        @app.get("/")
        async def serve_frontend_v1():
            if v1_path.is_file():
                return FileResponse(str(v1_path), media_type="text/html; charset=utf-8")
            return HTMLResponse(
                "<html><body><h1>前端页面未找到</h1><p>请创建 frontend/ 目录或运行索引脚本</p></body></html>",
                status_code=503,
            )
