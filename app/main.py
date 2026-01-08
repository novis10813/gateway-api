"""
Main application entry point for gateway authentication service.

This is the refactored main.py with clean separation of concerns.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
import sys

from core.config import settings
from api.v1.router import api_router
from db.database import db_manager

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles database initialization on startup and cleanup on shutdown.
    """
    # Startup
    logger.info("🚀 Starting Gateway Authentication Service...")
    
    try:
        await db_manager.init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Database initialization skipped: {e}")
        logger.info("   Falling back to legacy JSON file mode")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Gateway Authentication Service...")
    await db_manager.close()
    logger.info("✅ Database connections closed")


# 創建 FastAPI 應用程式
app = FastAPI(
    title="Gateway Authentication Service",
    description="API Key 和 JWT 驗證服務 (V2 with PostgreSQL)",
    version="2.0.0",
    lifespan=lifespan
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

# Admin UI 靜態檔案
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    @app.get("/ui")
    async def admin_ui():
        """Serve the Admin UI"""
        return FileResponse(static_dir / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)