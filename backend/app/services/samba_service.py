"""
Samba 服务控制 — systemctl smbd/nmbd, smbstatus 会话管理
"""
from typing import List, Optional
from ..services.ssh_manager import ssh_manager


async def get_service_status(server_id: int, server) -> dict:
    """获取 smbd 和 nmbd 的详细运行状态"""
    result = {
        "smbd": {"running": False, "pid": "", "memory": "", "cpu": "", "uptime": ""},
        "nmbd": {"running": False, "pid": "", "memory": "", "cpu": "", "uptime": ""},
    }

    for svc in ("smbd", "nmbd"):
        # 备选: smb / nmb (CentOS/RHEL 命名)
        for name in (svc, svc.replace("smbd", "smb").replace("nmbd", "nmb")):
            exit_code, stdout, stderr = await ssh_manager.exec_command(
                server_id, server,
                f"systemctl is-active {name} 2>/dev/null || true"
            )
            running = stdout.strip() == "active"

            if running:
                pid_cmd = f"systemctl show {name} --property=MainPID 2>/dev/null | cut -d= -f2 || true"
                mem_cmd = f"ps -p $(cat /var/run/{name}.pid 2>/dev/null || echo 0) -o rss --no-headers 2>/dev/null | awk '{{printf \"%.1f MB\", $1/1024}}' || echo '-'"
                cpu_cmd = f"ps -p $(cat /var/run/{name}.pid 2>/dev/null || echo 0) -o %cpu --no-headers 2>/dev/null || echo '-'"
                uptime_cmd = f"ps -p $(cat /var/run/{name}.pid 2>/dev/null || echo 0) -o etime --no-headers 2>/dev/null || echo '-'"

                _, pid_out, _ = await ssh_manager.exec_command(server_id, server, pid_cmd)
                _, mem_out, _ = await ssh_manager.exec_command(server_id, server, mem_cmd)
                _, cpu_out, _ = await ssh_manager.exec_command(server_id, server, cpu_cmd)
                _, uptime_out, _ = await ssh_manager.exec_command(server_id, server, uptime_cmd)

                result[svc] = {
                    "running": True,
                    "pid": pid_out.strip(),
                    "memory": mem_out.strip(),
                    "cpu": cpu_out.strip(),
                    "uptime": uptime_out.strip(),
                }
                break  # 找到一个有效名称就退出
            else:
                result[svc] = {"running": False, "pid": "", "memory": "", "cpu": "", "uptime": ""}

    return result


async def control_service(server_id: int, server, name: str, action: str) -> dict:
    """控制服务 — start / stop / restart"""
    # 规范化名称
    valid_actions = ["start", "stop", "restart", "reload"]
    if action not in valid_actions:
        return {"success": False, "error": f"无效操作: {action}"}

    valid_names = ["smbd", "nmbd", "smb", "nmb"]
    if name not in valid_names:
        return {"success": False, "error": f"无效服务名: {name}"}

    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"systemctl {action} {name} 2>&1 && echo 'OK' || echo 'FAIL'"
    )

    if "OK" in stdout:
        return {"success": True, "action": action, "name": name}
    return {"success": False, "error": stderr or stdout}


async def reload_config(server_id: int, server) -> dict:
    """重载 Samba 配置"""
    # 先 testparm
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        "testparm -s /etc/samba/smb.conf 2>&1 | tail -3 || true"
    )

    if "Loaded services file OK" not in stdout:
        return {"success": False, "error": f"配置校验失败: {stdout}"}

    for name in ("smbd", "smb"):
        exit_code, stdout, stderr = await ssh_manager.exec_command(
            server_id, server,
            f"systemctl reload {name} 2>&1 && echo 'OK' || true"
        )
        if "OK" in stdout:
            return {"success": True, "message": "配置已重载"}

    return {"success": False, "error": "重载失败，请检查服务状态"}


async def list_sessions(server_id: int, server) -> List[dict]:
    """列出当前所有 SMB 会话 (smbstatus)"""
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        "smbstatus -b 2>/dev/null || smbstatus 2>/dev/null || true"
    )

    sessions = []
    for line in stdout.split("\n"):
        line = line.strip()
        if not line or line.startswith("----") or line.startswith("Samba") or line.startswith("PID") or line.startswith("Service"):
            continue
        # 尝试解析 smbstatus 行格式
        parts = line.split()
        if len(parts) >= 5:
            sessions.append({
                "pid": parts[0] if len(parts) > 0 else "",
                "user": parts[1] if len(parts) > 1 else "",
                "machine": parts[2] if len(parts) > 2 else "",
                "share": parts[3] if len(parts) > 3 else "",
                "connected_at": " ".join(parts[4:]) if len(parts) > 4 else "",
            })

    return sessions


async def disconnect_session(server_id: int, server, pid: str) -> dict:
    """强制断开指定 PID 的会话"""
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"kill {pid} 2>/dev/null && echo 'KILLED' || echo 'FAIL'"
    )

    if "KILLED" in stdout:
        return {"success": True, "pid": pid}
    return {"success": False, "error": f"无法断开会话 PID={pid}"}
