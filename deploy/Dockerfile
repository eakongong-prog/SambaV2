FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 构建前端（需要 Node.js）
COPY frontend/ /tmp/frontend/
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    cd /tmp/frontend && \
    npm install && \
    npm run build && \
    mkdir -p /app/static && \
    cp -r /tmp/frontend/dist/* /app/static/ && \
    apt-get remove -y nodejs npm && \
    rm -rf /tmp/frontend /root/.npm

EXPOSE 8088

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
