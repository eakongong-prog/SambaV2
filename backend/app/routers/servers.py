"""
服务器管理路由 — 本地 CRUD，不通过 SSH
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.server import Server
from ..models.admin import AdminUser
from ..schemas.server import ServerCreate, ServerUpdate, ServerOut
from ..services.ssh_manager import ssh_manager
from ..routers.auth import get_current_admin_required
from ..utils.security import encrypt_ssh_password

router = APIRouter(prefix="/api/servers", tags=["服务器管理"])


async def get_server_or_404(server_id: int, db: AsyncSession) -> Server:
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return server


@router.get("", response_model=list[ServerOut])
async def list_servers(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    result = await db.execute(select(Server).order_by(Server.id))
    return result.scalars().all()


@router.get("/{server_id}", response_model=ServerOut)
async def get_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return server


@router.post("", response_model=ServerOut, status_code=201)
async def create_server(
    body: ServerCreate,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = Server(
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
        auth_type=body.auth_type,
    )
    if body.auth_type == "password" and body.password:
        server.encrypted_password = encrypt_ssh_password(body.password)
    if body.key_path:
        server.key_path = body.key_path

    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


@router.put("/{server_id}", response_model=ServerOut)
async def update_server(
    server_id: int,
    body: ServerUpdate,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    for field in ("name", "host", "port", "username", "auth_type", "key_path"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(server, field, val)

    if body.auth_type == "password" and body.password:
        server.encrypted_password = encrypt_ssh_password(body.password)
    elif body.auth_type == "key":
        server.encrypted_password = None

    await db.commit()
    await db.refresh(server)

    # 更新后断开旧连接
    await ssh_manager.disconnect(server_id)
    return server


@router.delete("/{server_id}", status_code=204)
async def delete_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    await ssh_manager.disconnect(server_id)
    await db.delete(server)
    await db.commit()


@router.post("/{server_id}/test-connection")
async def test_connection(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    ok, message = await ssh_manager.test_connection(server)
    return {"success": ok, "message": message}
