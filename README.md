# AI 实习信息平台

一个面向实习岗位的采集、检索和智能匹配平台。项目会把腾讯、字节跳动等招聘网站的岗位统一采集到 MySQL，再通过 FastAPI 提供查询接口，并使用 React 前端展示。

## 功能

- 采集腾讯实习岗位：分页调用招聘接口，并补充岗位详情。
- 采集字节跳动实习岗位：通过 Playwright 打开官方页面并捕获真实搜索接口。
- 岗位数据统一建模、内容哈希、去重和增量同步到 MySQL。
- 按公司、城市、岗位类型和关键词搜索，支持排序、分页和岗位详情。
- 浏览器本地用户标识下的岗位收藏。
- 创建岗位监控，手动或由后台 Worker 检查新增、更新岗位。
- 上传 PDF/DOCX 简历，提取简历画像并进行规则匹配、Embedding 召回和 LLM 精排。
- Redis 缓存岗位筛选项和简历匹配结果，并对简历匹配接口进行限流。

## 技术栈

- 后端：Python、FastAPI、PyMySQL、Playwright
- AI：OpenAI 兼容的 LLM/Embedding 接口
- 数据库：MySQL 8
- 缓存：Redis 7
- 前端：React、Vite、Ant Design
- 部署：Docker Compose、Nginx

## 目录结构

```text
src/
  api/          FastAPI 路由
  ai/           简历解析、岗位匹配、Embedding 和 LLM
  collectors/   腾讯、字节跳动岗位采集器
  db/           MySQL 表结构、查询、收藏和监控
  monitor/      岗位监控 Worker
frontend/
  src/          React 页面、组件和 API 客户端
data/
  *_jobs.json   示例岗位数据
docker/
  mysql/        MySQL 初始化脚本
```

## 配置

复制环境变量模板并填写配置：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

至少需要设置：

```dotenv
MYSQL_ROOT_PASSWORD=请替换为强密码
LLM_BASE_URL=https://你的模型服务地址/compatible-mode/v1
LLM_API_KEY=你的模型服务密钥
LLM_MODEL=你的聊天模型名称
```

Embedding 默认使用 `text-embedding-v4` 和 1024 维，可通过 `EMBEDDING_MODEL`、`EMBEDDING_DIMENSION` 修改。`MONITOR_INTERVAL_SECONDS` 控制监控 Worker 的轮询间隔，最小为 30 秒。

不要把 `.env`、真实 API Key、个人简历或其他隐私文件提交到 GitHub。仓库只应提交 `.env.example`。

## Docker 启动

安装 Docker Desktop 后，在项目根目录执行：

```bash
docker compose up -d --build
```

访问：

- 前端：http://localhost:3000
- 后端接口文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

停止服务：

```bash
docker compose down
```

如需连同 MySQL 和 Redis 数据卷一起删除：

```bash
docker compose down -v
```

首次使用 AI 推荐时，在前端点击“更新 Embedding 索引”。没有配置 LLM/Embedding 服务时，岗位搜索、收藏和监控仍可使用，但简历匹配不可用或会回退到规则匹配。

## 本地开发

后端依赖：

```bash
pip install -r requirements.txt
```

Playwright 浏览器：

```bash
playwright install chromium
```

启动后端：

```bash
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

启动前端：

```bash
cd frontend
npm install
npm run dev
```

本地开发时，Vite 会把 `/api` 请求代理到 `http://127.0.0.1:8000`。

## 岗位采集和同步

默认采集入口为 `src/main.py`，其中可配置公司、关键词、页数和字节跳动的无头浏览器模式：

```bash
python -m src.main
```

采集结果会写入 `data/tencent_jobs.json` 和 `data/bytedance_jobs.json`，随后同步到 MySQL。也可以单独运行采集器或使用 `src.db.sync` 同步已有 JSON。

## API 概览

| 路径 | 作用 |
| --- | --- |
| `GET /jobs` | 岗位筛选、排序和分页 |
| `GET /jobs/{job_id}` | 岗位详情 |
| `GET /companies` | 公司选项 |
| `GET /cities` | 城市选项 |
| `GET /job-types` | 岗位类型选项 |
| `GET/POST/DELETE /favorites` | 收藏管理 |
| `GET/POST/PATCH/DELETE /monitors` | 监控配置管理 |
| `POST /monitors/{id}/run` | 手动运行监控 |
| `GET /monitors/{id}/hits` | 查看监控命中 |
| `POST /resume/match` | 上传简历并返回岗位推荐 |
| `GET/POST /ai/embeddings/status|index` | Embedding 状态和索引 |

当前版本没有完整账号系统，前端使用浏览器生成的 `X-User-Id` 作为临时用户标识。它适合本地演示，不适合直接作为公网生产认证方案。

## 上传 GitHub 前检查

项目已忽略环境变量、前端依赖、构建产物、个人简历、截图和采集缓存。上传前仍请执行：

```bash
git status --short
git check-ignore .env frontend/node_modules frontend/dist
```

确认输出中没有真实密钥、个人文件和依赖目录后再提交。首次上传可以执行：

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<你的仓库名>.git
git push -u origin main
```

## 已知限制

- 当前没有真正的登录、JWT/Session 和后端权限系统；`X-User-Id` 不能用于公网安全认证。
- 招聘网站接口和页面可能变化，采集器需要随官方接口调整。
- PDF/DOCX 文本提取质量取决于文件结构；扫描版 PDF 需要 OCR，当前未集成 OCR。
- AI 推荐依赖外部 LLM/Embedding 服务，接口不可用时会降级或返回错误。

## 许可证

当前仓库未指定开源许可证。如需公开源代码并允许他人使用，请根据你的授权意愿补充 LICENSE 文件。
