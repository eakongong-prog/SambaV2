"""
共享管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.admin import AdminUser
from ..routers.auth import get_current_admin_required
from ..routers.servers import get_server_or_404
from ..schemas.share import ShareCreate, ShareUpdate
from ..services import samba_share
from ..utils.audit import record_audit

router = APIRouter(prefix="/api/shares", tags=["共享管理"])


@router.get("")
async def list_shares(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    shares = await samba_share.list_shares(server_id, server)
    return {"shares": shares, "count": len(shares)}


@router.get("/{name}")
async def get_share(
    name: str,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    share = await samba_share.get_share(server_id, server, name)
    if not share:
        raise HTTPException(status_code=404, detail="共享不存在")
    return share


@router.post("", status_code=201)
async def add_share(
    body: ShareCreate,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_share.add_share(server_id, server, body.name, body.model_dump())
    await record_audit(db, admin.username, "share.create", body.name,
                       server_id, server.name, dict(body.model_dump()))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))
    return result


@router.delete("/{name}")
async def remove_share(
    name: str,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_share.remove_share(server_id, server, name)
    await record_audit(db, admin.username, "share.delete", name, server_id, server.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "删除失败"))
    return result
