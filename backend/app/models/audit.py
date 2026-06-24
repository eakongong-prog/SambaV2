import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from ..database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_user = Column(String(50), nullable=False)       # 操作者
    server_id = Column(Integer, nullable=True)             # 目标服务器
    server_name = Column(String(100), nullable=True)       # 服务器名称快照
    action = Column(String(100), nullable=False)            # 操作类型: user.create, share.delete, service.restart...
    target = Column(String(255), nullable=True)             # 操作目标: 用户名、共享名...
    detail = Column(Text, nullable=True)                    # 操作详情 JSON
    result = Column(String(20), default="success")          # success | failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
