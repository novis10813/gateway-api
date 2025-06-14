"""
Main application entry point for gateway authentication service.

This is the refactored main.py with clean separation of concerns.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from api.v1.router import api_router

# 創建 FastAPI 應用程式
app = FastAPI(
    title="Gateway Authentication Service",
    description="API Key 和 JWT 驗證服務",
    version="1.0.0"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含 API v1 路由
app.include_router(api_router, prefix="/api/v1")

# 為了向後兼容，也在根路徑包含路由
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, debug=settings.debug) 