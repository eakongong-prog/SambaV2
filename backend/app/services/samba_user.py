"""
Samba 用户管理 — 通过 SSH 远程操作
对应命令: pdbedit, usermod, smbpasswd, chpasswd, useradd/userdel
"""
from typing import List, Optional
from ..services.ssh_manager import ssh_manager


async def list_users(server_id: int, server) -> List[dict]:
    """列出所有 Samba 用户（一次 SSH 调用获取全部数据）"""
    # 一条命令获取所有信息，避免 N+1 问题
    cmd = (
        "pdbedit -L -w 2>/dev/null | awk -F: '{print $1}' | while read user; do "
        "  groups=$(id -nG \"$user\" 2>/dev/null | tr ' ' ','); "
        "  flags=$(pdbedit -v \"$user\" 2>/dev/null | grep -i 'account flags' | head -1 || echo ''); "
        "  fullname=$(getent passwd \"$user\" 2>/dev/null | cut -d: -f5); "
        "  uid=$(id -u \"$user\" 2>/dev/null); "
        "  echo \"$user|$uid|$fullname|$groups|$flags\"; "
        "done"
    )

    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server, cmd, timeout=30
    )

    users = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) >= 5:
            users.append({
                "username": parts[0],
                "uid": parts[1],
                "full_name": parts[2],
                "groups": parts[3],
                "disabled": "D" in parts[4] if parts[4] else False,
            })

    return users


async def get_user(server_id: int, server, username: str) -> Optional[dict]:
    """获取单个用户详情"""
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"pdbedit -v {username}"
    )
    if exit_code != 0 or not stdout.strip():
        return None

    info = {"username": username}
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            info[key] = val

    # 获取群组
    exit2, groups, _ = await ssh_manager.exec_command(
        server_id, server,
        f"groups {username} 2>/dev/null | sed 's/.* : //' | tr ' ' ','"
    )
    info["groups"] = groups.strip() if exit2 == 0 else ""
    return info


async def create_user(
    server_id: int,
    server,
    username: str,
    password: str,
    full_name: str = "",
    primary_group: str = "smb_public",
    additional_groups: List[str] = None,
) -> dict:
    """创建系统用户 + Samba 用户"""
    cmds = [
        f"id {username} &>/dev/null && echo 'EXISTS' || "
        f"useradd -m -s /sbin/nologin -g {primary_group} {username}"
    ]

    if additional_groups:
        groups_str = ",".join(additional_groups)
        cmds.append(f"usermod -aG {groups_str} {username}")

    if full_name:
        cmds.append(f"usermod -c '{full_name}' {username}")

    cmds.append(f"(echo '{password}'; echo '{password}') | smbpasswd -s -a {username}")

    for cmd in cmds:
        exit_code, stdout, stderr = await ssh_manager.exec_command(
            server_id, server, cmd
        )
        if "EXISTS" in stdout:
            return {"success": False, "error": f"用户 {username} 已存在"}

    return {"success": True, "username": username}


async def update_user(
    server_id: int,
    server,
    username: str,
    full_name: str = None,
    primary_group: str = None,
    additional_groups: List[str] = None,
) -> dict:
    """更新用户信息"""
    results = []

    if full_name is not None:
        _, stdout, stderr = await ssh_manager.exec_command(
            server_id, server,
            f"usermod -c '{full_name}' {username} && echo 'OK' || echo 'FAIL'"
        )
        results.append("full_name" if "OK" in stdout else "full_name_failed")

    if primary_group is not None:
        _, stdout, stderr = await ssh_manager.exec_command(
            server_id, server,
            f"usermod -g {primary_group} {username} && echo 'OK' || echo 'FAIL'"
        )
        results.append("primary_group" if "OK" in stdout else "primary_group_failed")

    if additional_groups is not None:
        groups_str = ",".join(additional_groups) if additional_groups else ""
        if groups_str:
            _, stdout, stderr = await ssh_manager.exec_command(
                server_id, server,
                f"usermod -G {groups_str} {username} 2>/dev/null && echo 'OK' || echo 'FAIL'"
            )
        results.append("additional_groups_ok")

    return {"success": True, "updated": results}


async def delete_user(server_id: int, server, username: str) -> dict:
    """删除 Samba 用户 + 系统用户"""
    cmds = [
        f"smbpasswd -x {username} 2>/dev/null",
        f"userdel -r {username} 2>/dev/null && echo 'DELETED' || echo 'FAIL'"
    ]
    for cmd in cmds:
        await ssh_manager.exec_command(server_id, server, cmd)

    return {"success": True, "deleted": username}


async def reset_password(server_id: int, server, username: str, password: str) -> dict:
    """重置 Samba 密码"""
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"(echo '{password}'; echo '{password}') | smbpasswd -s {username}"
    )
    if exit_code == 0:
        await ssh_manager.exec_command(
            server_id, server,
            f"echo '{username}:{password}' | chpasswd"
        )
        return {"success": True}
    return {"success": False, "error": stderr}


async def batch_import(server_id: int, server, users: List[dict]) -> dict:
    """批量导入用户"""
    created = []
    failed = []
    for u in users:
        username = u.get("username", "")
        password = u.get("password", "")
        if not username or not password:
            continue
        result = await create_user(
            server_id, server,
            username=username,
            password=password,
            full_name=u.get("full_name", ""),
            primary_group=u.get("primary_group", "smb_public"),
            additional_groups=u.get("additional_groups", []),
        )
        if result["success"]:
            created.append(username)
        else:
            failed.append({"username": username, "error": result.get("error", "")})

    return {"success": True, "created": created, "failed": failed}
