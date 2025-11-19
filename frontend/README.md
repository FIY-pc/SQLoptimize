# SQLoptimize 前端（assistant-ui）

> 基于 [assistant-ui](https://github.com/Yonom/assistant-ui) 的 SQL 优化平台前端。

---

## 快速开始

### 1. 配置环境变量

在前端构建或运行时可提供以下变量（`.env.local` 或 docker 构建参数）：

| 变量 | 说明 |
| ---- | ---- |
| `NEXT_PUBLIC_SQLOPT_SERVICE_URL` | 后端服务基础 URL（默认 `http://127.0.0.1:8000`） |
| `NEXT_PUBLIC_DEFAULT_EMAIL` | 默认账号邮箱（首次访问自动登录/注册） |
| `NEXT_PUBLIC_DEFAULT_PASSWORD` | 默认账号密码 |
| `NEXT_PUBLIC_DEFAULT_NAME` | 默认账号昵称（可选，默认 `Default`） |


自动登录逻辑：仅配置默认账号时生效，若本地已有登录态（用户手动登录过）则不会覆盖。

示例（Docker Compose `frontend` 服务传参）：

```yaml
services:
	frontend:
		build:
			context: ./frontend
			args:
				NEXT_PUBLIC_SQLOPT_SERVICE_URL: "http://backend:8000"
				NEXT_PUBLIC_DEFAULT_EMAIL: "demo@example.com"
				NEXT_PUBLIC_DEFAULT_PASSWORD: "demo123456"
				NEXT_PUBLIC_DEFAULT_NAME: "DemoUser"
		environment:
			- NEXT_PUBLIC_SQLOPT_SERVICE_URL=http://backend:8000
```

### 2. 本地开发启动

```bash
cd frontend
npm install
npm run dev
# 或 yarn dev / pnpm dev / bun dev
```

访问 [http://localhost:3000](http://localhost:3000) 查看效果。

页面入口：`app/page.tsx`，保存后自动热更新。

### 3. Docker 相关用法（推荐）

> 需先安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)

#### 一键启动前后端

在项目根目录执行：

```bash
docker compose up --build
```

这会自动构建并启动：

- 后端（8000端口）：http://localhost:8000
- 前端（3000端口）：http://localhost:3000

#### 只运行前端或后端

只运行前端：

```bash
docker compose up frontend --build
```

查看服务状态

```bash
docker compose ps
```

查看服务日志

```bash
docker compose logs -f frontend   # 查看前端日志
docker compose logs -f backend    # 查看后端日志
```

关闭所有服务

```bash
docker compose down
```

重建镜像（依赖有变动时）

```bash
docker compose build
```

进入容器内部（调试/排查）

```bash
docker compose exec frontend sh   # 进入前端容器
docker compose exec backend sh    # 进入后端容器
```

---

## 目录结构

- `app/`         Next.js 应用主目录
- `components/`  复用 UI 组件
- `lib/`         业务逻辑、API 封装、工具
- `public/`      静态资源
- `README.md`    本说明文档

---

## 常用命令

| 命令                 | 说明               |
| -------------------- | ------------------ |
| npm run dev          | 本地开发（热更新） |
| npm run build        | 生产环境构建       |
| npm run start        | 启动生产环境服务   |
| npm run lint         | 代码风格检查       |
| npm run prettier     | 检查格式           |
| npm run prettier:fix | 自动修复格式       |

---

## 常见问题

1. **端口冲突**：如 3000/8000 被占用，请先释放端口或修改 `docker-compose.yml`。
2. **构建/依赖报错**：请先 `npm install`，如遇 ESLint/TypeScript 报错请根据提示修复。
3. **默认账号未生效**：确认已设置 `NEXT_PUBLIC_DEFAULT_EMAIL` 与 `NEXT_PUBLIC_DEFAULT_PASSWORD`，并且浏览器 `localStorage` 没有残留旧的登录态（可手动清除或使用应用内退出功能）。
4. **希望禁用自动登录**：不设置默认账号即可；或在生产环境只保留用户手动登录入口。

---

## 贡献建议

- 统一使用 TypeScript，保持类型安全。
- 组件/业务逻辑分层，详见 `lib/` 目录结构。
- PR 前请确保通过 lint/type 检查。

---

## 参考链接

- [assistant-ui 官方文档](https://github.com/Yonom/assistant-ui)
- [Next.js 官方文档](https://nextjs.org/docs)
