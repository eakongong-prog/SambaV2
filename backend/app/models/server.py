import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from ..database import Base


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)          # 显示名称
    host = Column(String(255), nullable=False)           # IP 或域名
    port = Column(Integer, default=22)                   # SSH 端口
    username = Column(String(100), nullable=False)       # SSH 用户名
    auth_type = Column(String(10), default="password")   # password | key
    encrypted_password = Column(Text, nullable=True)     # AES 加密后的密码
    key_path = Column(Text, nullable=True)               # 密钥文件路径（客户端本机）
    last_connected = Column(DateTime, nullable=True)
    is_connected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
