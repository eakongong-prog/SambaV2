"""
Samba 日志解析 — 读取 /var/log/samba/ 日志文件
"""
from typing import List, Optional
from ..services.ssh_manager import ssh_manager


async def get_logs(
    server_id: int,
    server,
    level: str = "all",
    search: str = "",
    lines: int = 100,
    log_file: str = "",
) -> dict:
    """读取 Samba 日志"""
    # 确定日志文件
    if not log_file:
        # 先尝试 log.smbd，再尝试 log.nmbd
        log_file = "log.smbd"

    # 构建过滤命令
    grep_cmd = ""
    if search:
        grep_cmd = f"| grep -i '{search}'"

    level_grep = ""
    if level and level != "all":
        level_map = {
            "error": "error|ERROR|failed|FAILED|fatal|FATAL|panic|PANIC",
            "warning": "warn|WARN|warning|WARNING",
            "info": "info|INFO|notice|NOTICE",
            "debug": "debug|DEBUG",
        }
        pattern = level_map.get(level, "")
        if pattern:
            level_grep = f"| grep -iE '{pattern}'"

    # 获取日志文件列表
    exit_code, list_out, _ = await ssh_manager.exec_command(
        server_id, server,
        "ls -la /var/log/samba/ 2>/dev/null | awk '{print $5, $9}' | tail -20 || true"
    )
    log_files = []
    for line in list_out.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and parts[1].startswith("log."):
            log_files.append({"name": parts[1], "size": parts[0]})

    # 读取日志内容
    cmd = f"tail -n {lines * 3} /var/log/samba/{log_file} 2>/dev/null {level_grep} {grep_cmd} | tail -n {lines} || true"

    exit_code, stdout, stderr = await ssh_manager.exec_command(
        server_id, server, cmd
    )

    # 解析日志行
    entries = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        entry = parse_log_line(line)
        entries.append(entry)

    return {
        "entries": entries,
        "count": len(entries),
        "log_file": log_file,
        "log_files": log_files,
    }


def parse_log_line(line: str) -> dict:
    """解析单行日志"""
    entry = {"raw": line, "level": "info", "timestamp": "", "source": "", "message": line}

    # 尝试匹配常见 Samba 日志格式
    # 格式1: [2024/01/15 10:30:45.123, 1] ../source3/...: message
    import re
    m = re.match(r'\[(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}[.\d]*)\s*,\s*(\d+)\]\s*(\S+):\s*(.*)', line)
    if m:
        entry["timestamp"] = m.group(1)
        entry["level_num"] = int(m.group(2))
        entry["source"] = m.group(3)
        entry["message"] = m.group(4)
        # 映射级别
        level_map = {0: "error", 1: "warning", 2: "info", 3: "debug", 4: "debug", 5: "debug", 10: "debug"}
        entry["level"] = level_map.get(entry["level_num"], "info")
        return entry

    # 格式2: smbd[12345]: message
    m = re.match(r'(\w+)\[(\d+)\]:\s*(.*)', line)
    if m:
        entry["source"] = f"{m.group(1)}[{m.group(2)}]"
        entry["message"] = m.group(3)
        entry["level"] = detect_level(m.group(3))
        return entry

    # 通用格式
    entry["level"] = detect_level(line)
    return entry


def detect_level(text: str) -> str:
    """根据关键词推断日志级别"""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["error", "failed", "fatal", "panic", "denied"]):
        return "error"
    if any(kw in text_lower for kw in ["warn", "warning"]):
        return "warning"
    if any(kw in text_lower for kw in ["debug", "trace"]):
        return "debug"
    return "info"
