# SambaV2 启动脚本
# 兼容通过 PyInstaller 打包后的环境

import uvicorn
from app.main import app
from app.config import settings

if __name__ == "__main__":
    print(f"==> SambaV2 v{settings.APP_VERSION} 启动中...")
    print(f"    API 文档: http://127.0.0.1:8800/api/docs")
    print(f"    默认账号: sys_admin / admin123")
    uvicorn.run(app, host="127.0.0.1", port=8800, log_level="info")
