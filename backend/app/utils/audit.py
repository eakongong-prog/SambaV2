"""
操作审计工具 — 记录所有写操作
"""
import json
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.audit import AuditLog


async def record_audit(
    db: AsyncSession,
    admin_user: str,
    action: str,
    target: str = "",
    server_id: int = None,
    server_name: str = "",
    detail: dict = None,
    result: str = "success",
    error_message: str = "",
):
    """记录一条审计日志"""
    log = AuditLog(
        admin_user=admin_user,
        action=action,
        target=target,
        server_id=server_id,
        server_name=server_name,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        result=result,
        error_message=error_message or None,
    )
    db.add(log)
    await db.commit()
