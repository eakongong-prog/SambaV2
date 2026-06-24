"""
Samba 群组管理 — 通过 SSH 远程操作
"""
from typing import List
from ..services.ssh_manager import ssh_manager


async def list_groups(server_id: int, server) -> List[dict]:
    """列出所有 Samba 相关群组，含主群组 + 附加群组成员"""
    # 获取 smb_* 群组列表
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        "getent group | awk -F: '$1 ~ /^smb_/ {print $1}' || true"
    )
    group_names = [n.strip() for n in stdout.strip().split("\n") if n.strip()]

    if not group_names:
        return []

    # 一次命令获取所有 smb_* 群组的完整成员
    # 思路：遍历 getent group，用 awk 扫描 /etc/passwd 找主群组为此组的用户
    script = []
    for name in group_names:
        script.append(
            f"gid=$(getent group {name} 2>/dev/null | cut -d: -f3); "
            f"add=$(getent group {name} 2>/dev/null | cut -d: -f4); "
            f"primary=$(awk -F: '$4==\"'$gid'\" {{printf \"%s \", $1}}' /etc/passwd 2>/dev/null); "
            f"all=$(echo \"$primary $add\" | tr ' ' '\\n' | sort -u | tr '\\n' ',' | sed 's/,$//'); "
            f"echo \"{name}|$gid|$all\""
        )

    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        "; ".join(script)
    )

    groups = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if "|" not in line:
            continue
        parts = line.split("|")
        if len(parts) >= 3:
            name = parts[0]
            gid = parts[1]
            members = [m for m in parts[2].split(",") if m] if parts[2] else []
            groups.append({
                "name": name,
                "gid": gid,
                "members": members,
                "member_count": len(members),
            })

    return groups


async def get_group(server_id: int, server, name: str) -> dict:
    """获取群组详情及成员列表（含主群组用户）"""
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"gid=$(getent group {name} 2>/dev/null | cut -d: -f3); "
        f"add=$(getent group {name} 2>/dev/null | cut -d: -f4); "
        f"primary=$(awk -F: '$4==\"'$gid'\" {{printf \"%s \", $1}}' /etc/passwd 2>/dev/null); "
        f"all=$(echo \"$primary $add\" | tr ' ' '\\n' | sort -u | tr '\\n' ',' | sed 's/,$//'); "
        f"echo \"GID|$gid\"; echo \"MEMBERS|$all\""
    )
    if not stdout.strip() or "GID|" not in stdout:
        return None

    gid = ""
    members = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if line.startswith("GID|"):
            gid = line.split("|", 1)[1]
        elif line.startswith("MEMBERS|"):
            members_str = line.split("|", 1)[1]
            members = [m for m in members_str.split(",") if m] if members_str else []

    # 获取每个成员的详细信息（一次命令）
    member_details = []
    if members:
        exit2, all_info, _ = await ssh_manager.exec_command(
            server_id, server,
            "for u in " + " ".join(members) + "; do "
            "  fn=$(getent passwd \"$u\" 2>/dev/null | cut -d: -f5); "
            "  echo \"$u|$fn\"; "
            "done"
        )
        for line in all_info.strip().split("\n"):
            if "|" in line:
                user, fullname = line.split("|", 1)
                member_details.append({"username": user, "full_name": fullname.strip() or user})

    return {
        "name": name,
        "gid": gid,
        "members": members,
        "member_details": member_details,
    }


async def create_group(server_id: int, server, name: str) -> dict:
    """创建一个新的 Samba 群组"""
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"getent group {name} >/dev/null && echo 'EXISTS' || (groupadd {name} && echo 'CREATED')"
    )
    result = stdout.strip()
    if "EXISTS" in result:
        return {"success": False, "error": f"群组 {name} 已存在"}
    if "CREATED" in result:
        return {"success": True, "name": name}
    return {"success": False, "error": stderr}


async def delete_group(server_id: int, server, name: str) -> dict:
    """删除群组"""
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"groupdel {name} 2>/dev/null && echo 'DELETED' || echo 'FAILED'"
    )
    if "DELETED" in stdout:
        return {"success": True}
    return {"success": False, "error": stderr}


async def update_members(server_id: int, server, name: str, members: List[str]) -> dict:
    """替换群组的附加成员（不影响主群组用户）"""
    exit_code, current, _ = await ssh_manager.exec_command(
        server_id, server,
        f"getent group {name} | cut -d: -f4 || true"
    )
    if not current.strip():
        return {"success": False, "error": f"群组 {name} 不存在或无法获取"}

    current_members = [m for m in current.strip().split(",") if m]

    # 移除不在新列表中的附加成员
    for m in current_members:
        if m not in members:
            await ssh_manager.exec_command(
                server_id, server,
                f"gpasswd -d {m} {name} 2>/dev/null"
            )

    # 添加新成员到附加群组
    for m in members:
        if m not in current_members:
            await ssh_manager.exec_command(
                server_id, server,
                f"usermod -aG {name} {m} 2>/dev/null"
            )

    return {"success": True, "members": members}
