# internship-monitor v2.0 优化说明

## 当前链路

```text
岗位采集
  -> MySQL
  -> FastAPI
  -> React

简历
  -> ResumeProfile
  -> 规则粗筛
  -> Embedding 语义召回（有索引时启用）
  -> Qwen 精排
  -> Top 10 推荐

岗位
  -> 收藏
  -> 监控规则
  -> monitor-worker 定时检查新增/更新岗位
```

## 本次新增

### 1. 收藏
- `favorites` 表
- `POST /favorites/{job_id}`
- `DELETE /favorites/{job_id}`
- `GET /favorites`
- 岗位列表和详情直接返回 `is_favorite`

当前没有接入完整账号体系，前端使用浏览器生成的本地 `X-User-Id` 标识。后续接入 JWT 登录时可以直接替换这一层。

### 2. AI 匹配升级
规则评分由“简单关键词命中”升级为四部分：
- 核心技能匹配
- 岗位方向匹配
- 项目/经历相关性
- 学历/经验门槛

Qwen 精排结果与规则分数再融合，最终返回：
`match_score / rule_score / llm_score / semantic_score`。

即使 Qwen 精排或 Embedding 暂时不可用，也会自动回退到规则匹配，不会让整次请求直接失败。

### 3. Embedding
使用可配置的百炼 OpenAI-compatible `/embeddings` 接口生成岗位向量，并把向量存到 `job_embeddings`。
默认模型：`text-embedding-v4`，默认 1024 维。

首次使用：打开“AI 智能推荐” -> “更新 Embedding 索引”。

### 4. Redis
Redis 用于：
- 相同简历匹配结果缓存 30 分钟
- 简历接口限流：单用户 60 秒最多 5 次
- 公司/城市/岗位类型元数据缓存 5 分钟

Redis 不可用时应用会降级到 MySQL 和正常计算，不影响基础岗位查询。

### 5. 岗位监控
新增：
- `monitor_configs`
- `monitor_hits`
- 手动“立即检查”
- 后台 `monitor-worker` 定时检查

监控条件复用岗位查询的公司、城市、关键词、岗位类型过滤逻辑，并检测岗位的 `created_at / updated_at` 变化。

### 6. 前端重构
原来的超大 `App.jsx` 已拆分为：
- `SearchPanel`
- `JobList`
- `JobDetailModal`
- `ResumeMatcher`
- `FavoritesPanel`
- `MonitorPanel`
- `useJobs`
- 独立 API 模块

`App.jsx` 现在只负责页面编排和跨页面状态，后续继续新增功能不会再把所有代码堆到一个文件里。

## Docker

`docker-compose.yml` 现在包含：
- MySQL 8
- Redis 7
- FastAPI backend
- monitor-worker
- React + Nginx frontend

MySQL 初始化脚本已经挂载到 `/docker-entrypoint-initdb.d/init.sql`，同时 backend 启动时也会执行 `ensure_schema()`，因此已有数据库卷新增功能表时也可以自动补齐。

LLM/Embedding 配置通过 Compose 环境变量传入容器，不依赖把 `.env` 打包进 Docker 镜像。

## 启动

```bash
cp .env.example .env
# 填写 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL

docker compose up -d --build
```

前端：`http://localhost:3000`
后端：`http://localhost:8000/docs`

本次提供的代码包不包含本地 `.env`、Python `.venv`、前端 `node_modules` 以及个人简历文件；重新部署时根据 `.env.example` 配置即可。
