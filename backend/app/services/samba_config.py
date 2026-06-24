"""
Samba 配置管理 — smb.conf 读写、testparm 校验、备份与恢复
"""
import datetime
from ..services.ssh_manager import ssh_manager


SMB_CONF_PATH = "/etc/samba/smb.conf"
BACKUP_DIR = "/etc/samba/backups"


async def get_config(server_id: int, server) -> dict:
    """读取 smb.conf 内容"""
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"cat {SMB_CONF_PATH} 2>/dev/null || echo 'NOT_FOUND'"
    )
    if "NOT_FOUND" in stdout:
        return {"content": "", "path": SMB_CONF_PATH, "exists": False}

    # 获取文件最后修改时间
    exit2, mtime, _ = await ssh_manager.exec_command(
        server_id, server,
        f"stat -c '%Y' {SMB_CONF_PATH} 2>/dev/null || date -r {SMB_CONF_PATH} '+%s' 2>/dev/null || echo '0'"
    )

    return {
        "content": stdout,
        "path": SMB_CONF_PATH,
        "exists": True,
        "last_modified": int(mtime.strip()) if mtime.strip().isdigit() else 0,
        "size": len(stdout),
    }


async def update_config(server_id: int, server, content: str) -> dict:
    """保存 smb.conf — 流程: 备份 → 写文件 → testparm → 通过则生效 → 失败则回滚"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. 确保备份目录存在
    await ssh_manager.exec_command(server_id, server, f"mkdir -p {BACKUP_DIR}")

    # 2. 备份当前文件
    backup_name = f"smb.conf.{timestamp}.bak"
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"cp {SMB_CONF_PATH} {BACKUP_DIR}/{backup_name} 2>/dev/null && echo 'BACKUP_OK' || echo 'BACKUP_FAIL'"
    )
    if "BACKUP_FAIL" in stdout:
        # 当前可能没有文件，不是致命错误
        pass

    # 3. 将新内容写入临时文件
    # 用 base64 编码避免 shell 转义问题
    import base64
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"echo '{encoded}' | base64 -d > {SMB_CONF_PATH}.tmp && echo 'WRITTEN' || echo 'WRITE_FAIL'"
    )

    if "WRITE_FAIL" in stdout:
        return {"success": False, "error": "无法写入临时文件"}

    # 4. testparm 校验
    exit_code, test_output, test_err = await ssh_manager.exec_command(
        server_id, server,
        f"testparm -s {SMB_CONF_PATH}.tmp 2>&1 || true"
    )

    if "Loaded services file OK" not in test_output:
        return {
            "success": False,
            "error": "配置校验失败",
            "testparm_output": test_output,
        }

    # 5. 校验通过：覆盖正式文件
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"mv {SMB_CONF_PATH}.tmp {SMB_CONF_PATH} && echo 'SAVED' || echo 'SAVE_FAIL'"
    )

    if "SAVED" in stdout:
        return {"success": True, "message": "配置已保存", "backup": backup_name}

    return {"success": False, "error": "无法覆盖配置文件"}


async def validate_config(server_id: int, server, content: str) -> dict:
    """离线校验配置内容（不保存到文件）"""
    import base64
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

    exit_code, test_output, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"echo '{encoded}' | base64 -d > /tmp/test_smb.conf && "
        f"testparm -s /tmp/test_smb.conf 2>&1 || true; "
        f"rm -f /tmp/test_smb.conf"
    )

    if "Loaded services file OK" in test_output:
        return {"valid": True, "message": "配置语法正确"}
    return {"valid": False, "message": test_output}


async def list_backups(server_id: int, server) -> list:
    """列出所有备份"""
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"ls -lt {BACKUP_DIR}/smb.conf.*.bak 2>/dev/null | awk '{{print $5,$6,$7,$8,$9}}' || true"
    )

    backups = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 5:
            backups.append({
                "filename": parts[4].split("/")[-1],
                "path": parts[4],
                "size": parts[0],
                "date": f"{parts[1]} {parts[2]} {parts[3]}",
            })

    return backups


async def create_backup(server_id: int, server) -> dict:
    """手动创建备份"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"smb.conf.{timestamp}.bak"

    await ssh_manager.exec_command(server_id, server, f"mkdir -p {BACKUP_DIR}")
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"cp {SMB_CONF_PATH} {BACKUP_DIR}/{backup_name} && echo 'CREATED' || echo 'FAIL'"
    )

    if "CREATED" in stdout:
        return {"success": True, "filename": backup_name}
    return {"success": False, "error": "备份失败 — 配置文件可能不存在"}


async def restore_backup(server_id: int, server, filename: str) -> dict:
    """从备份恢复配置"""
    # 防路径穿越
    safe_name = filename.split("/")[-1]
    if not safe_name.startswith("smb.conf.") or not safe_name.endswith(".bak"):
        return {"success": False, "error": "无效的备份文件名"}

    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"cp {BACKUP_DIR}/{safe_name} {SMB_CONF_PATH} && "
        f"testparm -s {SMB_CONF_PATH} 2>&1 | grep -c 'OK' && "
        f"systemctl reload smbd 2>/dev/null || systemctl reload smb 2>/dev/null || true && "
        f"echo 'RESTORED' || echo 'RESTORE_FAIL'"
    )

    if "RESTORED" in stdout:
        return {"success": True, "filename": safe_name}
    return {"success": False, "error": stdout}
