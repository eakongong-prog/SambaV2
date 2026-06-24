# SambaV2 — Samba 可视化管理后台

通过 SSH 远程连接 Samba 服务器，用图形界面管理用户、群组、共享目录、权限、服务状态和配置文件。

## 功能特性

- **🌐 多服务器管理** — 保存多台 Samba 服务器的 SSH 连接，一键切换
- **👥 用户管理** — 增删改查 Samba 用户，批量导入，重置密码，部门分配
- **👨‍👩‍👧 群组管理** — 部门群组增删，成员拖拽调整
- **📁 共享管理** — smb.conf 中 [share] 段的可视化增删改
- **🔐 ACL 权限浏览器** — 目录树浏览 + POSIX ACL 可视化编辑 + 一键预设模板
- **⚙️ 服务控制** — smbd/nmbd 启停重启，实时会话查看与强制断开
- **📝 配置编辑器** — Monaco Editor 在线编辑 smb.conf，testparm 校验，自动备份
- **📊 日志查看器** — 搜索/过滤 Samba 日志，级别筛选，自动刷新
- **📋 操作审计** — 所有操作自动记录，可追溯

## 技术栈

| 层 | 选型 |
|----|------|
| 后端 | Python 3.11+ / FastAPI |
| 前端 | Vue 3 + Element Plus + Vite |
| SSH | Paramiko |
| 存储 | SQLite |
| 认证 | JWT |

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8800 --reload
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动前端

```bash
cd frontend
npm run dev
```

浏览器打开 http://localhost:5173

### 5. Docker 部署

```bash
docker compose -f deploy/docker-compose.yml up -d
```

访问 http://localhost:8088

## 默认管理员

- 账号：`sys_admin`
- 密码：`admin123`
- **首次登录后请立即修改密码！**

## 连接到 Samba 服务器

1. 登录后台后，点击「添加服务器」
2. 填写 Samba 服务器的 IP、SSH 用户名（需要 root 或有 sudo 权限）和密码
3. 点击「测试连接」验证
4. 保存后即可通过顶栏下拉切换

## 开发

```bash
# 后端开发
cd backend && uvicorn app.main:app --reload --port 8800

# 前端开发
cd frontend && npm run dev
# Vite 代理会自动将 /api 请求转发到 http://127.0.0.1:8800
```

## 许可证

MIT
