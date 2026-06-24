"""
服务控制路由 — smbd/nmbd 管理 + 实时会话 + 审计日志
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.admin import AdminUser
from ..routers.auth import get_current_admin_required
from ..routers.servers import get_server_or_404
from ..services import samba_service
from ..utils.audit import record_audit

router = APIRouter(prefix="/api/services", tags=["服务控制"])


@router.get("/status")
async def get_status(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    return await samba_service.get_service_status(server_id, server)


@router.post("/{name}/{action}")
async def control_service(
    name: str,
    action: str,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_service.control_service(server_id, server, name, action)
    await record_audit(db, admin.username, f"service.{action}", name, server_id, server.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "操作失败"))
    return result


@router.post("/reload-config")
async def reload_config(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_service.reload_config(server_id, server)
    await record_audit(db, admin.username, "service.reload-config", "", server_id, server.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "重载失败"))
    return result


@router.get("/sessions")
async def list_sessions(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    sessions = await samba_service.list_sessions(server_id, server)
    return {"sessions": sessions, "count": len(sessions)}


@router.post("/sessions/{pid}/disconnect")
async def disconnect_session(
    pid: str,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_service.disconnect_session(server_id, server, pid)
    await record_audit(db, admin.username, "session.disconnect", f"PID={pid}", server_id, server.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "断开失败"))
    return result
