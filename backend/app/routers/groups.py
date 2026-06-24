"""
群组管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.admin import AdminUser
from ..routers.auth import get_current_admin_required
from ..routers.servers import get_server_or_404
from ..schemas.group import GroupCreate, UpdateMembersRequest
from ..services import samba_group
from ..utils.audit import record_audit

router = APIRouter(prefix="/api/groups", tags=["群组管理"])


@router.get("")
async def list_groups(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    groups = await samba_group.list_groups(server_id, server)
    return {"groups": groups, "count": len(groups)}


@router.get("/{name}")
async def get_group(
    name: str,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    group = await samba_group.get_group(server_id, server, name)
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    return group


@router.post("", status_code=201)
async def create_group(
    body: GroupCreate,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_group.create_group(server_id, server, body.name)
    await record_audit(db, admin.username, "group.create", body.name, server_id, server.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))
    return result


@router.delete("/{name}")
async def delete_group(
    name: str,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_group.delete_group(server_id, server, name)
    await record_audit(db, admin.username, "group.delete", name, server_id, server.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "删除失败"))
    return result


@router.put("/{name}/members")
async def update_members(
    name: str,
    body: UpdateMembersRequest,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    result = await samba_group.update_members(server_id, server, name, body.members)
    await record_audit(db, admin.username, "group.members", f"{name}: {len(body.members)}人",
                       server_id, server.name, {"members": body.members})
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "更新失败"))
    return result
