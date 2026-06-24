"""
用户管理路由 — 通过 SSH 操作远程 Samba 服务器
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.admin import AdminUser
from ..routers.auth import get_current_admin_required
from ..routers.servers import get_server_or_404
from ..schemas.user import SambaUserCreate, SambaUserUpdate, ResetPasswordRequest, BatchImportRequest
from ..services import samba_user
from ..utils.audit import record_audit

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("")
async def list_users(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    try:
        users = await samba_user.list_users(server_id, server)
        return {"users": users, "count": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")


@router.get("/{username}")
async def get_user(
    username: str,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    try:
        user = await samba_user.get_user(server_id, server, username)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")


@router.post("", status_code=201)
async def create_user(
    body: SambaUserCreate,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    try:
        result = await samba_user.create_user(
            server_id, server,
            username=body.username,
            password=body.password,
            full_name=body.full_name,
            primary_group=body.primary_group,
            additional_groups=body.additional_groups,
        )
        await record_audit(db, admin.username, "user.create", body.username,
                           server_id, server.name,
                           {"primary_group": body.primary_group, "full_name": body.full_name},
                           "success" if result["success"] else "failed",
                           result.get("error", ""))
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        await record_audit(db, admin.username, "user.create", body.username,
                           server_id, server.name, {}, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")


@router.put("/{username}")
async def update_user(
    username: str,
    body: SambaUserUpdate,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    try:
        result = await samba_user.update_user(
            server_id, server,
            username=username,
            full_name=body.full_name,
            primary_group=body.primary_group,
            additional_groups=body.additional_groups,
        )
        await record_audit(db, admin.username, "user.update", username, server_id, server.name)
        return result
    except Exception as e:
        await record_audit(db, admin.username, "user.update", username, server_id, server.name, {}, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")


@router.delete("/{username}", status_code=200)
async def delete_user(
    username: str,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    try:
        result = await samba_user.delete_user(server_id, server, username)
        await record_audit(db, admin.username, "user.delete", username, server_id, server.name)
        return result
    except Exception as e:
        await record_audit(db, admin.username, "user.delete", username, server_id, server.name, {}, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")


@router.post("/{username}/reset-password")
async def reset_password(
    username: str,
    body: ResetPasswordRequest,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    try:
        result = await samba_user.reset_password(server_id, server, username, body.password)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "重置失败"))
        await record_audit(db, admin.username, "user.reset-password", username, server_id, server.name)
        return result
    except HTTPException:
        raise
    except Exception as e:
        await record_audit(db, admin.username, "user.reset-password", username, server_id, server.name, {}, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")


@router.post("/batch-import")
async def batch_import(
    body: BatchImportRequest,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    try:
        result = await samba_user.batch_import(
            server_id, server,
            [u.model_dump() for u in body.users]
        )
        created = result.get("created", [])
        failed = result.get("failed", [])
        await record_audit(db, admin.username, "user.batch-import",
                           f"成功{len(created)}个/失败{len(failed)}个",
                           server_id, server.name, {"created": created, "failed": failed})
        return result
    except Exception as e:
        await record_audit(db, admin.username, "user.batch-import", "", server_id, server.name, {}, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")
