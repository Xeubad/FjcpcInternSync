#!/bin/sh
# FjcpcInternSync 容器启动脚本
# 后端必须在 backend/ 目录启动，否则会出现 No module named 'app'。
set -e

cd /app/backend

# SPA 托管目录：容器内前端产物固定在 /app/frontend/dist。
# main.py 的自动探测路径在容器布局下不成立，必须显式指定。
export SPA_STATIC_DIR="${SPA_STATIC_DIR:-/app/frontend/dist}"

# 运行参数（可被环境变量覆盖）
HOST="${APP_HOST:-0.0.0.0}"
PORT="${APP_PORT:-8000}"
WORKERS="${UVICORN_WORKERS:-1}"

echo "[start] FjcpcInternSync 启动: host=${HOST} port=${PORT} workers=${WORKERS}"
echo "[start] SPA_STATIC_DIR=${SPA_STATIC_DIR}"

# 单进程默认即可；任务在进程内执行，多 worker 会让内存会话/任务状态不共享，
# 如需多 worker 请先接入外部会话与任务存储。
exec uvicorn app.main:app --host "${HOST}" --port "${PORT}" --workers "${WORKERS}"
