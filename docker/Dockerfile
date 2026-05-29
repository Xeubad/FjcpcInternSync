# FjcpcInternSync 单容器镜像（多阶段构建）
# 阶段一：Node 构建 React 前端 -> 阶段二：Python 运行 FastAPI 并托管 dist
#
# 构建上下文必须为项目根目录（FjcpcInternSync/），例如：
#   docker build -f docker/Dockerfile -t fjcpc-intern-sync .

# ---------- 阶段一：构建前端 ----------
FROM node:20-alpine AS frontend-builder
WORKDIR /build

# 先拷依赖清单，命中层缓存（依赖未变时不重复 npm ci）
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# 再拷源码并构建，产物在 /build/dist
COPY frontend/ ./
RUN npm run build

# ---------- 阶段二：运行后端 ----------
FROM python:3.12-slim AS runtime

# Python 运行时环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 后端工作目录为 /app/backend（与本地开发一致，避免 No module named 'app'）
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 拷后端源码
COPY backend/ ./backend/

# 从阶段一拷前端构建产物到容器内固定位置
COPY --from=frontend-builder /build/dist ./frontend/dist

# 启动脚本
COPY docker/start.sh ./docker/start.sh
RUN chmod +x ./docker/start.sh

# FastAPI 在 8000 端口同时提供 API 与 SPA
EXPOSE 8000

# 运行时数据目录，建议挂卷持久化（任务、日志、Cookie 等）
VOLUME ["/app/backend/data"]

# 容器健康检查：命中 /health 端点
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200 else 1)"

CMD ["./docker/start.sh"]
