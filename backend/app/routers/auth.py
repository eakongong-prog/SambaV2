"""
认证路由：登录、获取当前用户、修改密码
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.admin import AdminUser
from ..schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest, AdminInfo
from ..utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/api/auth", tags=["认证"])

security = HTTPBearer()

# ---------- 获取当前用户 ----------

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="无效的认证凭据",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise CREDENTIALS_EXCEPTION
    username = payload.get("sub")
    if username is None:
        raise CREDENTIALS_EXCEPTION

    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise CREDENTIALS_EXCEPTION
    return user


async def get_current_admin_required(
    current_user: AdminUser = Depends(get_current_admin),
) -> AdminUser:
    if current_user.username != "sys_admin":
        raise HTTPException(status_code=403, detail="仅限 sys_admin 访问")
    return current_user


# ---------- 路由 ----------

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == body.username)
    )
    admin = result.scalar_one_or_none()

    if not admin or not verify_password(body.password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    # 更新最后登录时间
    admin.last_login = datetime.utcnow()
    await db.commit()

    # 只有 sys_admin 能登录
    if admin.username != "sys_admin":
        raise HTTPException(status_code=403, detail="仅限 sys_admin 登录")

    token = create_access_token(data={"sub": admin.username})
    return LoginResponse(
        access_token=token,
        must_change_password=admin.must_change_password,
    )


@router.get("/me", response_model=AdminInfo)
async def get_me(current_user: AdminUser = Depends(get_current_admin_required)):
    return AdminInfo(
        username=current_user.username,
        must_change_password=current_user.must_change_password,
    )


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: AdminUser = Depends(get_current_admin_required),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")

    current_user.hashed_password = get_password_hash(body.new_password)
    current_user.must_change_password = False
    await db.commit()

    return {"message": "密码修改成功"}
