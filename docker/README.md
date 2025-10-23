# 使用说明

1. 进入docker目录
2. 将需要的docker-compose模版文件复制为docker-compose.yaml
3. 将.env.example复制为.env
4. 检查并修改docker-compose.yaml和.env中需要修改的变量
5. 运行`docker compose up -d`


# FAQ

Q: 如果镜像拉不下来/拉取很慢怎么办？
A: 寻找对应的代理镜像，比如[DaoCloud](https://docs.daocloud.io/community/mirror/index.html)，将代理镜像拉取下来之后手动将其tag为原镜像名