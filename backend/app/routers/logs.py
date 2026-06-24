"""
日志查看路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.admin import AdminUser
from ..routers.auth import get_current_admin_required
from ..routers.servers import get_server_or_404
from ..services import samba_log

router = APIRouter(prefix="/api/logs", tags=["日志查看"])


@router.get("")
async def get_logs(
    level: str = Query("all", description="日志级别: all/error/warning/info/debug"),
    search: str = Query("", description="搜索关键词"),
    lines: int = Query(100, ge=10, le=1000, description="行数"),
    log_file: str = Query("", description="日志文件名"),
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    try:
        return await samba_log.get_logs(server_id, server, level, search, lines, log_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")
