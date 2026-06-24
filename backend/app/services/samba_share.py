"""
Samba 共享管理 — 解析与修改 smb.conf 中的 [share] 段落
"""
import re
from typing import List, Optional
from ..services.ssh_manager import ssh_manager


async def list_shares(server_id: int, server) -> List[dict]:
    """列出所有共享（解析 testparm -s 输出）"""
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        "testparm -s 2>/dev/null"
    )
    shares = []
    current_section = None

    for line in stdout.split("\n"):
        raw = line
        line = line.strip()
        # 跳过注释和空行
        if not line or line.startswith("#") or line.startswith(";"):
            if not re.match(r'^\[(.+)\]$', line):
                continue

        # section header
        section_match = re.match(r'^\[(.+)\]$', line)
        if section_match:
            section_name = section_match.group(1)
            if section_name != "global":
                current_section = {
                    "name": section_name,
                    "path": "",
                    "valid_users": "",
                    "admin_users": "",
                    "writable": "no",
                    "read_only": "yes",
                    "browseable": "yes",
                    "create_mask": "0744",
                    "directory_mask": "0755",
                }
                shares.append(current_section)
            else:
                current_section = None
            continue

        # key = value 行（行首有 tab）
        if current_section is not None and "=" in line:
            key_val = line.split("=", 1)
            if len(key_val) == 2:
                key = key_val[0].strip().replace(" ", "_")
                val = key_val[1].strip()
                current_section[key] = val

    # 后处理：read only = No 意味着 writable = yes
    for s in shares:
        if s.get("read_only", "").lower() == "no":
            s["writable"] = "yes"

    return shares


async def get_share(server_id: int, server, name: str) -> Optional[dict]:
    """获取单个共享详情"""
    shares = await list_shares(server_id, server)
    for s in shares:
        if s["name"] == name:
            return s
    return None


async def add_share(server_id: int, server, name: str, config: dict) -> dict:
    """在 smb.conf 末尾追加新的 [share] 段落（同时创建目录 + 设权限）"""
    path = config.get("path", f"/data/samba/{name}")
    comment = config.get("comment", name)
    valid_users = config.get("valid_users", "")
    admin_users = config.get("admin_users", "")
    writable = config.get("writable", "yes")
    create_mask = config.get("create_mask", "0777")
    directory_mask = config.get("directory_mask", "0777")
    browseable = config.get("browseable", "yes")

    share_block = f"""
[{name}]
    comment = {comment}
    path = {path}
    valid users = {valid_users}
    admin users = {admin_users}
    writable = {writable}
    browseable = {browseable}
    create mask = {create_mask}
    directory mask = {directory_mask}
    nt acl support = yes
    map acl inherit = yes
"""

    # 1. 创建目录
    await ssh_manager.exec_command(
        server_id, server,
        f"mkdir -p {path} 2>/dev/null"
    )

    # 2. 追加到 smb.conf
    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"echo '{share_block}' >> /etc/samba/smb.conf && echo 'ADDED' || echo 'FAIL'"
    )

    if "ADDED" in stdout:
        # 3. 验证配置
        exit2, test_out, _ = await ssh_manager.exec_command(
            server_id, server,
            "testparm -s /etc/samba/smb.conf 2>&1 | grep -c 'OK' || true"
        )
        # 4. 重载
        await ssh_manager.exec_command(
            server_id, server,
            "systemctl reload smbd 2>/dev/null || systemctl reload smb 2>/dev/null || true"
        )
        return {"success": True, "name": name}

    return {"success": False, "error": stderr}


async def remove_share(server_id: int, server, name: str) -> dict:
    """从 smb.conf 中删除 [name] 段落"""
    import tempfile
    import json

    # 用 Python 内联脚本解析删除（避免复杂的 sed）
    py_script = f'''
import re
try:
    with open("/etc/samba/smb.conf", "r") as f:
        content = f.read()

    pattern = r"^\\[{name}\\].*?(?=^\\[|\\Z)"
    new_content = re.sub(pattern, "", content, flags=re.DOTALL | re.MULTILINE)

    # 清理多余空行
    import os
    new_content = re.sub(r"\\n\\n\\n+", "\\n\\n", new_content)

    with open("/etc/samba/smb.conf", "w") as f:
        f.write(new_content.strip() + "\\n")
    print("REMOVED")
except Exception as e:
    print(f"ERROR: {{e}}")
'''

    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server,
        f"python3 -c '{py_script}' 2>/dev/null || python -c '{py_script}' 2>/dev/null"
    )

    if "REMOVED" in stdout:
        await ssh_manager.exec_command(
            server_id, server,
            "systemctl reload smbd 2>/dev/null || systemctl reload smb 2>/dev/null || true"
        )
        return {"success": True}
    return {"success": False, "error": stderr or stdout}
