"""
仪表盘路由 — 聚合展示 + 告警 + 在线历史 + 热门共享 + 磁盘 IO
"""
import asyncio
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..database import get_db
from ..models.server import Server
from ..models.admin import AdminUser
from ..models.audit import AuditLog
from ..models.snapshot import SessionSnapshot
from ..routers.auth import get_current_admin_required
from ..routers.servers import get_server_or_404
from ..services.ssh_manager import ssh_manager

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("/overview")
async def get_overview(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)

    data = {
        "smbd_running": False,
        "nmbd_running": False,
        "active_sessions": 0,
        "share_count": 0,
        "disks": [],
        "disk_io": [],
        "alerts": [],
    }

    # 构建组合命令：系统状态 + 磁盘使用 + 磁盘 IO（并行采样）
    cmd = (
        # 系统服务状态 & 在线信息
        'echo "SMBD=$(systemctl is-active smbd 2>/dev/null || systemctl is-active smb 2>/dev/null || echo unknown)"; '
        'echo "NMBD=$(systemctl is-active nmbd 2>/dev/null || systemctl is-active nmb 2>/dev/null || echo unknown)"; '
        'echo "SESSIONS=$(smbstatus -b 2>/dev/null | tail -n +5 | wc -l)"; '
        'echo "SHARES=$(testparm -s 2>/dev/null | grep -c \'^\[\' || echo 0)"; '
        # 多挂载点磁盘使用
        'echo "DISK_BEGIN"; '
        'for d in /data/samba/ /home/ /srv/samba/; do '
        '  [ -d "$d" ] && df -h "$d" 2>/dev/null | tail -1 | awk -v name="$d" \'{print name"|"$2"|"$3"|"$5"|"$4}\'; '
        'done; '
        'echo "DISK_END"'
    )

    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server, cmd, timeout=30
    )

    in_disk = False
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if line.startswith("SMBD="):
            data["smbd_running"] = "active" in line
            if not data["smbd_running"]:
                data["alerts"].append({"type": "error", "message": "SMB 服务 (smbd) 已停止，文件共享不可用"})
        elif line.startswith("NMBD="):
            data["nmbd_running"] = "active" in line
        elif line.startswith("SESSIONS="):
            try:
                data["active_sessions"] = max(0, int(line.split("=", 1)[1].strip()))
            except ValueError:
                pass
        elif line.startswith("SHARES="):
            try:
                data["share_count"] = max(0, int(line.split("=", 1)[1].strip()) - 1)
            except ValueError:
                pass
        elif line == "DISK_BEGIN":
            in_disk = True
            continue
        elif line == "DISK_END":
            in_disk = False
            continue

        if in_disk and "|" in line:
            parts = line.split("|")
            if len(parts) >= 4:
                share_name = parts[0].rstrip("/")
                share = {
                    "share": share_name,
                    "total": parts[1],
                    "used": parts[2],
                    "percent": int(parts[3].replace("%", "")),
                }
                if len(parts) >= 5:
                    share["avail"] = parts[4]
                data["disks"].append(share)

    # 磁盘 IO — 两次独立 exec_command 采样，服务端计算差值
    try:
        _, io1, _ = await ssh_manager.exec_command(
            server_id, server, "awk '{print $3,$4,$6,$8,$10,$13}' /proc/diskstats", timeout=10
        )
        await asyncio.sleep(1)
        _, io2, _ = await ssh_manager.exec_command(
            server_id, server, "awk '{print $3,$4,$6,$8,$10,$13}' /proc/diskstats", timeout=10
        )

        def _parse(text):
            d = {}
            for line in text.strip().split("\n"):
                p = line.split()
                if len(p) >= 6:
                    try:
                        d[p[0]] = [int(v) for v in p[1:]]
                    except ValueError:
                        pass
            return d

        import re
        # 只保留物理磁盘（sdX/vdX/nvme0nX 等，不含数字后缀）
        _disk_pat = re.compile(r'^(sd[a-z]+|vd[a-z]+|nvme\d+n\d+)$')
        d1, d2 = _parse(io1), _parse(io2)
        for dev in d1:
            if not _disk_pat.match(dev) or dev not in d2:
                continue
            a, b = d1[dev], d2[dev]
            rds = max(0, b[1] - a[1]); wrs = max(0, b[3] - a[3])
            rdo = max(0, b[0] - a[0]); wro = max(0, b[2] - a[2])
            iot = max(0, b[4] - a[4]); top = rdo + wro
            data["disk_io"].append({
                "name": dev,
                "read_mb_s": round(rds * 512.0 / 1048576.0, 1),
                "write_mb_s": round(wrs * 512.0 / 1048576.0, 1),
                "iops": top,
                "avg_latency_ms": round(iot / max(top, 1), 1),
            })
    except Exception:
        pass

    # 磁盘容量告警
    for d in data["disks"]:
        if d["percent"] > 90:
            data["alerts"].append({"type": "warning", "message": f"磁盘 {d['share']} 使用率已达 {d['percent']}%，请及时清理"})
        elif d["percent"] > 80:
            data["alerts"].append({"type": "info", "message": f"磁盘 {d['share']} 使用率 {d['percent']}%，接近预警线"})

    return data


@router.get("/session-history")
async def get_session_history(
    server_id: int = Query(..., description="服务器 ID"),
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    """获取会话历史 — 从 session_snapshots 表读取真实采样数据"""

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # 查询快照数据
    result = await db.execute(
        select(SessionSnapshot)
        .where(
            SessionSnapshot.server_id == server_id,
            SessionSnapshot.created_at >= cutoff,
        )
        .order_by(SessionSnapshot.created_at.asc())
    )
    snapshots = result.scalars().all()

    # 获取当前在线数
    server = await get_server_or_404(server_id, db)
    current_count = 0
    try:
        exit_code, stdout, stderr = await ssh_manager.exec_command(
            server_id, server,
            "smbstatus -b 2>/dev/null | tail -n +5 | wc -l || echo 0",
            timeout=10,
        )
        current_count = max(0, int(stdout.strip()))
    except Exception:
        pass

    # 构建时间序列
    sessions = [
        {
            "time": s.created_at.strftime("%m-%d %H:%M") if s.created_at else "",
            "hour": s.created_at.hour if s.created_at else 0,
            "count": s.count,
        }
        for s in snapshots
    ]

    # 如果没有任何历史采样，回退到只有当前值的一个点
    if not sessions:
        now = datetime.utcnow()
        sessions = [{
            "time": now.strftime("%m-%d %H:%M"),
            "hour": now.hour,
            "count": current_count,
        }]

    return {"sessions": sessions, "current": current_count}


@router.get("/top-shares")
async def get_top_shares(
    server_id: int = Query(..., description="服务器 ID"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    server = await get_server_or_404(server_id, db)

    top = []
    try:
        exit_code, stdout, stderr = await ssh_manager.exec_command(
            server_id, server,
            "smbstatus -b 2>/dev/null | tail -n +5 | awk '{print $4}' | sort | uniq -c | sort -rn || true"
        )

        exit2, size_out, _ = await ssh_manager.exec_command(
            server_id, server,
            "for d in /data/samba/*/; do "
            "  name=$(basename $d); "
            "  size=$(du -sh $d 2>/dev/null | awk '{print $1}'); "
            "  echo \"$name|$size\"; "
            "done"
        )
        size_map = {}
        for line in size_out.strip().split("\n"):
            if "|" in line:
                n, s = line.split("|", 1)
                size_map[n] = s.strip()

        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                count = int(parts[0])
                share = parts[1]
                top.append({"share": share, "connections": count, "size": size_map.get(share, "-")})

        if not top:
            for name, size in sorted(size_map.items(), key=lambda x: x[1], reverse=True)[:8]:
                top.append({"share": name, "connections": 0, "size": size})
    except Exception:
        pass

    return {"top": top[:8]}


@router.get("/audit-logs")
async def get_audit_logs(
    server_id: int = Query(..., description="服务器 ID"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin_required),
):
    """获取审计日志 — 按 server_id 过滤"""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.server_id == server_id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return {
        "logs": [
            {
                "id": l.id,
                "admin_user": l.admin_user,
                "server_id": l.server_id,
                "server_name": l.server_name,
                "action": l.action,
                "target": l.target,
                "detail": l.detail,
                "result": l.result,
                "error_message": l.error_message,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
    }


async def sample_session_snapshot(db: AsyncSession):
    """后台任务：对每台服务器采样当前在线会话数并存入 session_snapshots 表"""
    from ..models.server import Server as ServerModel

    result = await db.execute(select(ServerModel))
    servers = result.scalars().all()

    for srv in servers:
        try:
            exit_code, stdout, stderr = await ssh_manager.exec_command(
                srv.id, srv,
                "smbstatus -b 2>/dev/null | tail -n +5 | wc -l || echo 0",
                timeout=10,
            )
            count = max(0, int(stdout.strip()))
        except Exception:
            count = 0

        snapshot = SessionSnapshot(server_id=srv.id, count=count)
        db.add(snapshot)

        # 清理 7 天前的旧数据
        cutoff = datetime.utcnow() - timedelta(days=7)
        await db.execute(
            delete(SessionSnapshot).where(
                SessionSnapshot.server_id == srv.id,
                SessionSnapshot.created_at < cutoff,
            )
        )

    await db.commit()
