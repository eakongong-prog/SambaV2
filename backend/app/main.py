"""
SambaV2 — Samba 可视化管理后台 API
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db, async_session
from .routers import auth, servers, dashboard, users, groups, shares, services, config, permissions, logs

# 后台采样任务句柄
_background_tasks = set()


async def session_sampling_loop():
    """每 5 分钟对所有服务器采样一次在线会话数"""
    while True:
        await asyncio.sleep(300)  # 5 分钟间隔
        try:
            async with async_session() as db:
                await dashboard.sample_session_snapshot(db)
        except Exception:
            pass  # 采样失败不影响主流程


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # 启动后台会话采样
    task = asyncio.create_task(session_sampling_loop())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    yield
    # 关闭时取消后台任务
    for t in _background_tasks:
        t.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS — 开发时允许前端独立运行
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(shares.router)
app.include_router(services.router)
app.include_router(config.router)
app.include_router(permissions.router)
app.include_router(logs.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
