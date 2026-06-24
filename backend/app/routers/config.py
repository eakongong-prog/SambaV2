"""
配置管理路由 — smb.conf 编辑、校验、备份、恢复 + 审计
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..database import get_db
from ..models.admin import AdminUser
from ..routers.auth import get_current_admin_required
from ..routers.servers import get_server_or_404
from ..services import samba_config
from ..utils.audit import record_audit

router = APIRouter(prefix="/api/config", tags=["配置管理"])


class ConfigUpdateRequest(BaseModel):
    content: str


class ConfigValidateRequest(BaseModel):
    content: str


@router.get("")
async def get_config(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    return await samba_config.get_config(server_id, server)


@router.put("")
async def update_config(
    body: ConfigUpdateRequest,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_config.update_config(server_id, server, body.content)
    await record_audit(db, admin.username, "config.update", "smb.conf", server_id, server.name,
                       {"size": len(body.content)},
                       "success" if result["success"] else "failed",
                       result.get("error", ""))
    if not result["success"]:
        detail = result.get("testparm_output", result.get("error", "保存失败"))
        raise HTTPException(status_code=400, detail=detail)
    return result


@router.post("/validate")
async def validate_config(
    body: ConfigValidateRequest,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    return await samba_config.validate_config(server_id, server, body.content)


@router.get("/backups")
async def list_backups(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    backups = await samba_config.list_backups(server_id, server)
    return {"backups": backups}


@router.post("/backups")
async def create_backup(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_config.create_backup(server_id, server)
    await record_audit(db, admin.username, "backup.create",
                       result.get("filename", ""), server_id, server.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "备份失败"))
    return result


@router.post("/backups/{filename}/restore")
async def restore_backup(
    filename: str,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_config.restore_backup(server_id, server, filename)
    await record_audit(db, admin.username, "backup.restore", filename, server_id, server.name,
                       result="success" if result["success"] else "failed",
                       error_message=result.get("error", ""))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "恢复失败"))
    return result
