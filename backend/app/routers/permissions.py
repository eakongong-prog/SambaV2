"""
权限管理路由 — ACL 浏览与编辑
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional

from ..database import get_db
from ..models.admin import AdminUser
from ..routers.auth import get_current_admin_required
from ..routers.servers import get_server_or_404
from ..services import samba_acl, samba_share
from ..utils.audit import record_audit

router = APIRouter(prefix="/api/permissions", tags=["权限管理"])


class AclEntryInput(BaseModel):
    type: str  # user / group
    name: str = ""
    permissions: str = ""  # rwx / r-x / ---
    default: bool = False


class SetAclRequest(BaseModel):
    share: str
    path: str = ""
    entries: List[AclEntryInput]
    recursive: bool = False


class RemoveAclRequest(BaseModel):
    share: str
    path: str = ""
    type: str
    name: str = ""
    is_default: bool = False


class ApplyTemplateRequest(BaseModel):
    share: str
    template: str  # private / collaborative / public
    group_name: str = ""
    recursive: bool = True


def _share_path_cache():
    """辅助：获取共享名→路径的映射"""
    return {}


async def _get_share_path(share_name: str, server_id: int, server, db) -> str:
    """根据共享名获取实际路径"""
    shares = await samba_share.list_shares(server_id, server)
    for s in shares:
        if s["name"] == share_name:
            return s.get("path", f"/data/samba/{share_name}")
    raise HTTPException(status_code=404, detail=f"共享 {share_name} 不存在")


@router.get("/tree")
async def get_tree(
    share: str = Query(..., description="共享名"),
    path: str = Query("", description="子路径"),
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    share_path = await _get_share_path(share, server_id, server, db)
    try:
        items = await samba_acl.list_directory(server_id, server, share_path, path)
        return {"items": items, "share": share, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")


@router.get("/acl")
async def get_acl(
    share: str = Query(..., description="共享名"),
    path: str = Query("", description="子路径"),
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    share_path = await _get_share_path(share, server_id, server, db)
    try:
        return await samba_acl.get_acl(server_id, server, share_path, path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")


@router.put("/acl")
async def set_acl(
    body: SetAclRequest,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    share_path = await _get_share_path(body.share, server_id, server, db)
    try:
        result = await samba_acl.set_acl(
            server_id, server,
            share_path, body.path,
            [e.model_dump() for e in body.entries],
            body.recursive,
        )
        entries_desc = "; ".join(f"{e.type}:{e.name}={e.permissions}" for e in body.entries)
        await record_audit(db, admin.username, "acl.set",
                           f"{body.share}/{body.path}", server_id, server.name,
                           {"entries": entries_desc, "recursive": body.recursive})
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "设置失败"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")


@router.post("/apply-template")
async def apply_template(
    body: ApplyTemplateRequest,
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)
    share_path = await _get_share_path(body.share, server_id, server, db)
    try:
        result = await samba_acl.apply_template(
            server_id, server,
            share_path, body.template, body.group_name, body.recursive,
        )
        await record_audit(db, admin.username, "acl.template",
                           f"{body.share} -> {body.template}", server_id, server.name,
                           {"template": body.template, "group_name": body.group_name})
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "应用失败"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH 执行失败: {str(e)}")
