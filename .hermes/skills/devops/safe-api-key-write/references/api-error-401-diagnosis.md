# API 401 错误诊断

## 三种 401 场景区分

| 错误信息 | 含义 | 原因 | 修复 |
|----------|------|------|------|
| `Invalid API Key` | 请求到了服务器，Key 无效 | .env 中 key 被 write_file 搞成 `***`，或 key 本身过期 | 用 `set_env_key.py` 重写真实 key |
| `Missing Authentication header` | 连 Authorization 头都没发 | 网关切换 provider 后状态混乱，env 变量未加载 | `pm2 restart hermes-gateway` |
| `403 Forbidden` | Key 有效但权限不足 | key 被禁用、IP 白名单、或付费计划到期 | 查 provider 后台 |

## 关键判断逻辑

**401 = HTTP 请求已到达远程服务器**，所以一定是 key/auth 相关的问题，不可能是本地 provider 类型配错。

**本地配置错误**（如 `provider: xiaomi-mimo` 而非 `provider: openai`）会导致 Hermes 内部报错（如 "unknown provider"），根本不会发出 HTTP 请求，所以不会出现 401。

## 实际案例

MiMo 配置中 `provider: xiaomi-mimo` 写成了自定义名称而非 `openai`：
- 测试 API 直接调用 → HTTP 200 ✅（绕过了 Hermes）
- 通过 Hermes 调用 → 401 Invalid API Key ❌（因为 .env 中 key 已被损坏为 `***`）

后来发现 401 的根因是 key 被 `write_file` 损坏，不是 provider 类型问题。provider 类型修正是后续优化。

## 排查步骤

1. 直接测试 API（绕过 Hermes）：
   ```bash
   curl -H "Authorization: Bearer $KEY" https://api.example.com/v1/models
   ```
2. 如果直连 OK 但 Hermes 报 401 → 检查 .env 中 key 值
3. 如果直连也 401 → key 本身有问题（过期、禁用等）
4. 如果直连报其他错 → 网络或 endpoint 问题
