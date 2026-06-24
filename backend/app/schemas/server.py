from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    host: str = Field(..., min_length=1, max_length=255, description="IP 或域名")
    port: int = Field(22, ge=1, le=65535, description="SSH 端口")
    username: str = Field(..., min_length=1, max_length=100, description="SSH 用户名")
    auth_type: str = Field("password", pattern="^(password|key)$", description="认证方式")
    password: Optional[str] = Field(None, description="SSH 密码（auth_type=password）")
    key_path: Optional[str] = Field(None, description="密钥文件路径（auth_type=key）")


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    auth_type: Optional[str] = None
    password: Optional[str] = None
    key_path: Optional[str] = None


class ServerOut(BaseModel):
    id: int
    name: str
    host: str
    port: int
    username: str
    auth_type: str
    encrypted_password: Optional[str] = None
    key_path: Optional[str] = None
    last_connected: Optional[datetime] = None
    is_connected: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
