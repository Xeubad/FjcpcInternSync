# FjcpcInternSync

面向实习日志场景的**全栈应用**：对接 FJCPC 实习平台接口，提供 **FastAPI** 后端与 **React（Vite + TypeScript + Ant Design）** 管理台；支持 Excel 批量解析与异步上传、文本三行格式批量提交；数据以 **JSON 文件**持久化，可按规划扩展 PostgreSQL。

---

## 功能概览

| 模块 | 说明 |
|------|------|
| 认证 | 管理台账号密码、一次性访问令牌（文件存储）；会话使用 **Bearer Token**；401 自动跳登录 |
| 文本上传 | 日报/周/月文本批量（兼容旧 `/api/upload/day\|week\|month`） |
| Excel 批量上传 | 模板下载、Excel 解析校验、同步/异步批量上传至实习平台 |
| 浏览器 Cookie | aTrust/SSO 场景：用户粘贴浏览器 Cookie，服务端保存后自动注入上游请求 |
| 任务中心 | 异步任务列表、幂等执行守卫（防止重复提交）、重试、错误诊断 |
| 管理员 | 访问令牌签发/列表/禁用 |

---

## 技术栈

- **后端**：Python 3.12+、FastAPI、httpx、slowapi、Pydantic Settings
- **前端**：React 19、TypeScript、Vite、Ant Design、Zustand、Axios、ECharts
- **数据**：`backend/data/` 下 JSON 原子写入（任务、审计日志等）
- **部署**：Docker 多阶段构建（Node 打包前端 + Python 跑后端，单容器 8000 端口提供 API + SPA）

---

## 目录结构

```text
FjcpcInternSync/
├── backend/                 # FastAPI 应用（应用包名为 app）
│   ├── app/                 # 路由、领域、服务、仓储、配置
│   ├── data/                # 运行时数据（勿提交敏感信息与生产密钥）
│   ├── tests/               # pytest
│   ├── requirements.txt
│   └── .env.example         # 环境变量模板 → 复制为 .env
├── frontend/                # React SPA
│   ├── src/
│   └── package.json
├── docker/                  # 容器化部署（单容器，后端托管前端）
│   ├── Dockerfile           # 多阶段构建：Node 构建前端 + Python 跑后端
│   ├── docker-compose.yml   # 单容器编排（挂卷持久化 data/）
│   ├── start.sh             # 容器启动脚本
│   └── .env.docker.example  # 容器环境变量模板 → 复制为 .env.docker
└── README.md                # 本文件
```

---

## 环境准备

1. **Python**：建议 3.12+
2. **Node.js**：建议 LTS（用于前端构建与开发服务器）

---

## 配置

```powershell
cd backend
copy .env.example .env
```

按需修改 `.env`：**生产环境务必修改** `ADMIN_USERNAME` / `ADMIN_PASSWORD`、`ADMIN_KEY`，以及 **FJCPC_\*** 上游地址与 Cookie 模板。联调可使用 **`FJCPC_DRY_RUN=true`** 避免真实请求实习平台。

变量说明以 **`backend/.env.example`** 内注释为准。

---

## 本地开发（推荐）

**后端必须在 `backend` 目录启动**，否则会出现 `No module named 'app'`。

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

另开终端：

```powershell
cd frontend
npm install
npm run dev
```

浏览器访问 **`http://localhost:5173`**（Vite 已将 `/api`、`/health` 代理到 `http://127.0.0.1:8000`，详见 `frontend/vite.config.ts`）。

默认登录账号见 `.env.example`（如 `admin` / `admin123`）。

---

## 生产部署（后端托管前端）

1. 构建前端：

   ```powershell
   cd frontend
   npm ci
   npm run build
   ```

2. 确认存在 **`frontend/dist`**（含 `index.html`）。若构建产物路径不同，在 **`backend/.env`** 中设置 **`SPA_STATIC_DIR`** 指向该目录。

3. 在 **`backend`** 目录启动：

   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. 浏览器访问 **`http://<主机>:8000/login`**，同一端口提供 API 与 SPA。

---

## Docker 部署（单容器）

容器采用**多阶段构建**：Node 阶段打包前端，Python 阶段运行后端并托管 `dist`，最终在 **8000 端口**同时提供 API 与 SPA，与「后端托管前端」模式一致。

> 所有命令在 **项目根目录**（`FjcpcInternSync/`）执行；构建上下文必须是项目根目录。

### 方式一：docker compose（推荐）

```bash
cd docker
cp .env.docker.example .env.docker   # 按需修改账号密码、FJCPC_* 等
docker compose up -d --build
```

### 方式二：docker 命令

```bash
docker build -f docker/Dockerfile -t fjcpc-intern-sync .
docker run -d --name fjcpc-intern-sync \
  -p 8000:8000 \
  --env-file docker/.env.docker \
  -v fjcpc-data:/app/backend/data \
  fjcpc-intern-sync
```

启动后访问 **`http://<主机>:8000/login`**。

### 关键说明

| 项 | 说明 |
|----|------|
| 环境变量 | 复制 `docker/.env.docker.example` 为 `.env.docker`，**生产务必修改** `ADMIN_PASSWORD` / `ADMIN_KEY` 与 `FJCPC_*` |
| 数据持久化 | `backend/data/`（任务、日志、浏览器 Cookie）挂载到命名卷 `fjcpc-data`，容器重建不丢数据 |
| 健康检查 | 容器内置 `HEALTHCHECK`，命中 `GET /health`；`docker ps` 可见 healthy 状态 |
| SPA 目录 | 启动脚本固定 `SPA_STATIC_DIR=/app/frontend/dist`，无需手动配置 |
| 进程数 | 默认 `UVICORN_WORKERS=1`。任务在进程内执行，多 worker 会导致内存会话与任务状态不共享，需先接入外部存储才能 >1 |

### 常用命令

```bash
docker compose logs -f          # 查看日志
docker compose restart          # 重启
docker compose down             # 停止并移除容器（命名卷数据保留）
```

---

## API 与文档

- 健康检查：**`GET /health`**、**`GET /api/health`**（兼容旧版字段形态之一）
- 兼容路由前缀：**`/api`**（如 `/api/upload/day`、`/api/excel/analyze` 等）
- 启动后端后，可打开 **`http://127.0.0.1:8000/docs`** 查看 OpenAPI（Swagger）

---

## 测试

```powershell
cd backend
pytest -q
```

```powershell
cd frontend
npm run build
```

---

## 许可证与免责

本项目为学校实习场景自用工具，使用前请遵守校方与实习平台的服务条款；生产部署请自行加固密钥与 HTTPS。
