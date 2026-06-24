"""
SSH 连接池管理器
- 为每台 Samba 服务器缓存一条 SSH 连接
- 通过 server_id 获取连接，自动重连
"""
import asyncio
import time
from typing import Dict, Optional, Tuple

import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException
from paramiko import SSHClient

from ..config import settings
from ..utils.security import decrypt_ssh_password


class SSHConnection:
    """包装一条 SSH 连接及其元数据"""
    def __init__(self, client: SSHClient):
        self.client = client
        self.created_at = time.time()
        self.last_used = time.time()

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_used) > settings.SSH_POOL_TTL

    @property
    def is_active(self) -> bool:
        try:
            transport = self.client.get_transport()
            return transport is not None and transport.is_active()
        except Exception:
            return False


class SSHManager:
    """管理多台服务器的 SSH 连接池"""

    def __init__(self):
        self._pool: Dict[int, SSHConnection] = {}

    async def get_client(self, server_id: int, server_info) -> SSHClient:
        """获取连接；不存在或已断开则新建"""
        conn = self._pool.get(server_id)

        if conn is not None:
            if conn.is_expired:
                await self._close_connection(conn)
                self._pool.pop(server_id, None)
                conn = None
            elif not conn.is_active:
                await self._close_connection(conn)
                self._pool.pop(server_id, None)
                conn = None

        if conn is None:
            client = await self._connect(server_info)
            conn = SSHConnection(client)
            self._pool[server_id] = conn

        conn.last_used = time.time()
        return conn.client

    async def _connect(self, server_info) -> SSHClient:
        """建立一条新 SSH 连接"""
        client = SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        hostname = server_info.host
        port = server_info.port
        username = server_info.username

        if server_info.auth_type == "password":
            if not server_info.encrypted_password:
                raise ValueError("SSH 密码未设置")
            password = decrypt_ssh_password(server_info.encrypted_password)
            key_filename = None
        else:
            password = None
            key_filename = server_info.key_path if server_info.key_path else None

        loop = asyncio.get_event_loop()

        def _do_connect():
            client.connect(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                key_filename=key_filename,
                timeout=settings.SSH_TIMEOUT,
                banner_timeout=settings.SSH_TIMEOUT,
            )

        await loop.run_in_executor(None, _do_connect)
        return client

    async def _close_connection(self, conn: SSHConnection):
        """安全关闭连接"""
        try:
            if conn.is_active:
                conn.client.close()
        except Exception:
            pass

    async def test_connection(self, server_info) -> Tuple[bool, str]:
        """测试连接，成功后立即关闭"""
        client = SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            hostname = server_info.host
            port = server_info.port
            username = server_info.username

            if server_info.auth_type == "password":
                encrypted = getattr(server_info, "encrypted_password", None)
                password = decrypt_ssh_password(encrypted) if encrypted else None
                key_filename = None
            else:
                password = None
                key_filename = getattr(server_info, "key_path", None)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: client.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    password=password,
                    key_filename=key_filename,
                    timeout=settings.SSH_TIMEOUT,
                    banner_timeout=settings.SSH_TIMEOUT,
                ),
            )
            return True, "连接成功"
        except AuthenticationException:
            return False, "认证失败：用户名或密码错误"
        except Exception as e:
            return False, str(e)
        finally:
            try:
                client.close()
            except Exception:
                pass

    async def exec_command(self, server_id: int, server_info, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """在指定服务器上执行命令，返回 (exit_code, stdout, stderr)"""
        client = await self.get_client(server_id, server_info)
        loop = asyncio.get_event_loop()

        def _exec():
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            return (
                stdout.channel.recv_exit_status(),
                stdout.read().decode("utf-8", errors="replace"),
                stderr.read().decode("utf-8", errors="replace"),
            )

        try:
            exit_code, stdout, stderr = await loop.run_in_executor(None, _exec)
            return exit_code, stdout, stderr
        except SSHException:
            # 连接断开，清理并重建
            removed = self._pool.pop(server_id, None)
            if removed:
                await self._close_connection(removed)
            raise

    async def close_all(self):
        """关闭所有连接"""
        for conn in list(self._pool.values()):
            await self._close_connection(conn)
        self._pool.clear()

    async def disconnect(self, server_id: int):
        """主动断开某个服务器的连接"""
        conn = self._pool.pop(server_id, None)
        if conn:
            await self._close_connection(conn)


# 全局单例
ssh_manager = SSHManager()
