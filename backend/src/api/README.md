# api

数据库用的sqlite，db文件路径可以在.env的db_path修改，默认是./data/app.db


## 鉴权

有鉴权的接口（指使用了utils/auth_dependence.py中的get_current_user依赖项的）不能直接访问，需要先拿到令牌（token）

测试方法：

1. 先POST /api/auth/register注册一个用户（这一步拿到的ccess_token和refresh_token也可以直接用）
2. POST /api/auth/login进行登录，拿到access_token和refresh_token
3. 请求有鉴权的接口时，先设置请求头`Authorization`为`Bearer {access_token}`
4. 然后填写参数请求即可

关于access_token和refresh_token的说明：

- `access_token`是`访问令牌`，是实际用来验证访问权限的令牌
- `refresh_token`是`刷新令牌`，用途是刷新`access_token`
- 两者的过期时长可以在`.env`里面设置，为了方便测试不妨可以设置一个很大的数