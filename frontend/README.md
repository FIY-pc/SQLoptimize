# SQLoptimize 前端（assistant-ui）

> 基于 [assistant-ui](https://github.com/Yonom/assistant-ui) 的 SQL 优化平台前端。

---

## 快速开始

### 1. 配置环境变量

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

---

## 贡献建议

- 统一使用 TypeScript，保持类型安全。
- 组件/业务逻辑分层，详见 `lib/` 目录结构。
- PR 前请确保通过 lint/type 检查。

---

## 参考链接

- [assistant-ui 官方文档](https://github.com/Yonom/assistant-ui)
- [Next.js 官方文档](https://nextjs.org/docs)
