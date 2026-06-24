"""
Samba ACL 权限管理 — getfacl/setfacl 解析与操作
"""
from typing import List, Optional
from ..services.ssh_manager import ssh_manager


async def list_directory(server_id: int, server, share_path: str, sub_path: str = "") -> List[dict]:
    """列出指定目录下的子目录和文件"""
    full_path = share_path.rstrip("/")
    if sub_path:
        full_path = f"{full_path}/{sub_path.strip('/')}"

    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"ls -la {full_path} 2>/dev/null | tail -n +2 || true"
    )

    items = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 8)
        if len(parts) < 9:
            continue

        perms = parts[0]
        name = parts[8]
        is_dir = perms.startswith("d")
        size = parts[4]

        # 跳过 . 和 ..
        if name in (".", ".."):
            continue

        item_path = f"{sub_path.rstrip('/')}/{name}" if sub_path else name
        items.append({
            "name": name,
            "path": item_path,
            "is_dir": is_dir,
            "size": size,
            "permissions": perms,
            "owner": parts[2],
            "group": parts[3],
        })

    # 目录排前面
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return items


async def get_acl(server_id: int, server, share_path: str, sub_path: str = "") -> dict:
    """获取指定路径的 ACL 详情"""
    full_path = share_path.rstrip("/")
    if sub_path:
        full_path = f"{full_path}/{sub_path.strip('/')}"

    # 获取 POSIX 基本权限
    exit_code, stat_out, _ = await ssh_manager.exec_command(
        server_id, server,
        f"stat -c '%a %U %G' {full_path} 2>/dev/null || true"
    )

    owner = ""
    group = ""
    octal_mode = ""
    if stat_out.strip():
        parts = stat_out.strip().split()
        if len(parts) >= 3:
            octal_mode = parts[0]
            owner = parts[1]
            group = parts[2]

    # 获取 ACL
    exit_code, acl_out, _ = await ssh_manager.exec_command(
        server_id, server,
        f"getfacl -p {full_path} 2>/dev/null || true"
    )

    entries = []
    default_entries = []
    current_list = entries

    for line in acl_out.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("default:"):
            current_list = default_entries
            line = line[8:]

        # 解析格式: user::rwx, user:name:rwx, group::rwx, group:name:rwx, other::rwx, mask::rwx
        parts = line.split(":", 2)
        if len(parts) >= 2:
            entry_type = parts[0]  # user / group / other / mask
            entry_name = parts[1] if len(parts) > 1 else ""
            perms = parts[2] if len(parts) > 2 else ""

            entry = {
                "type": entry_type,
                "name": entry_name if entry_name else "(默认)",
                "permissions": perms,
                "read": "r" in perms,
                "write": "w" in perms,
                "execute": "x" in perms,
            }
            current_list.append(entry)

    return {
        "path": sub_path or "/",
        "full_path": full_path,
        "owner": owner,
        "group": group,
        "octal_mode": octal_mode,
        "entries": entries,
        "default_entries": default_entries,
    }


async def set_acl(
    server_id: int,
    server,
    share_path: str,
    sub_path: str,
    entries: List[dict],
    recursive: bool = False,
) -> dict:
    """设置 ACL 条目"""
    full_path = share_path.rstrip("/")
    if sub_path:
        full_path = f"{full_path}/{sub_path.strip('/')}"

    rec_flag = "-R" if recursive else ""

    for entry in entries:
        entry_type = entry.get("type", "user")
        name = entry.get("name", "")
        perms = entry.get("permissions", "")

        # 构造 setfacl 命令
        if name and name != "(默认)":
            acl_spec = f"{entry_type}:{name}:{perms}"
        else:
            acl_spec = f"{entry_type}::{perms}"

        # 是否修改 default ACL
        is_default = entry.get("default", False)
        if is_default:
            acl_spec = f"default:{acl_spec}"

        exit_code, stdout, stderr = await ssh_manager.exec_command(
            server_id, server,
            f"setfacl {rec_flag} -m {acl_spec} {full_path} 2>&1 && echo 'OK' || echo 'FAIL'"
        )
        if "FAIL" in stdout:
            return {"success": False, "error": f"setfacl 失败: {stdout}"}

    return {"success": True}


async def remove_acl_entry(
    server_id: int,
    server,
    share_path: str,
    sub_path: str,
    entry_type: str,
    name: str,
    is_default: bool = False,
) -> dict:
    """删除单个 ACL 条目"""
    full_path = share_path.rstrip("/")
    if sub_path:
        full_path = f"{full_path}/{sub_path.strip('/')}"

    prefix = "default:" if is_default else ""
    if name and name != "(默认)":
        acl_spec = f"{prefix}{entry_type}:{name}"
    else:
        acl_spec = f"{prefix}{entry_type}::"

    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"setfacl -x {acl_spec} {full_path} 2>&1 && echo 'OK' || echo 'FAIL'"
    )

    if "OK" in stdout:
        return {"success": True}
    return {"success": False, "error": stdout}


async def apply_template(
    server_id: int,
    server,
    share_path: str,
    template_name: str,
    group_name: str = "",
    recursive: bool = True,
) -> dict:
    """应用预设 ACL 模板"""
    full_path = share_path.rstrip("/")
    rec_flag = "-R" if recursive else ""

    templates = {
        # 私有模式：创建者独占，其他人无权
        "private": [
            f"setfacl {rec_flag} -b {full_path}",
            f"setfacl {rec_flag} -d -m u::rwx,g::---,o::--- {full_path}",
            f"setfacl {rec_flag} -m u::rwx,g::---,o::--- {full_path}",
        ],
        # 协作模式：部门内可读写
        "collaborative": [
            f"setfacl {rec_flag} -b {full_path}",
            f"setfacl {rec_flag} -d -m u::rwx,g::rwx,o::--- {full_path}",
            f"setfacl {rec_flag} -m u::rwx,g::rwx,o::--- {full_path}",
        ] + ([
            f"setfacl {rec_flag} -d -m g:{group_name}:rwx {full_path}",
            f"setfacl {rec_flag} -m g:{group_name}:rwx {full_path}",
        ] if group_name else []),
        # 公开模式：所有人可读
        "public": [
            f"setfacl {rec_flag} -b {full_path}",
            f"setfacl {rec_flag} -d -m u::rwx,g::r-x,o::r-x {full_path}",
            f"setfacl {rec_flag} -m u::rwx,g::r-x,o::r-x {full_path}",
        ],
    }

    if template_name not in templates:
        return {"success": False, "error": f"未知模板: {template_name}"}

    for cmd in templates[template_name]:
        exit_code, stdout, stderr = await ssh_manager.exec_command(
            server_id, server, cmd
        )

    return {"success": True, "template": template_name}
