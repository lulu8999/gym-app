# WeCom AI Bot 连接故障排查

## 错误：invalid bot_id or secret (errcode=853000)

### 典型原因

1. **Bot ID 不是 AgentId** — 最常见的错误：把应用的 AgentId（如 1000002）当作 AI Bot 的 Bot ID 配置。
   - AgentId：数字格式，来自应用详情页
   - Bot ID：字符串格式（如 `aibyIv3U0ehs...`），来自 AI Bot 设置页

2. **Secret 字段名** — Hermes `wecom.py` 代码读取 `extra.get("secret")`，不是 `bot_secret`。如果手动写了 `bot_secret` 字段，代码会跳过它并回退到环境变量。正确配置：
   ```yaml
   extra:
     bot_id: "your-bot-id"
     secret: "your-bot-secret"   # 字段名必须是 secret，不是 bot_secret
   ```

3. **环境变量干扰** — 配置加载代码（`gateway/config.py` 第 1636-1645 行）会检测 `WECOM_BOT_ID` 和 `WECOM_SECRET` 环境变量并覆盖配置。如果环境变量中有旧值，即使配置文件正确也会被覆盖。

4. **`.env` 未重新加载** — 更新了 `.env` 文件后需要重启网关（`pm2 restart hermes-gateway`）。配置文件和 `.env` 在启动时各加载一次。

### 调试步骤

```bash
# 1. 检查网关进程运行状态
pm2 status | grep hermes-gateway

# 2. 检查配置文件中的凭据
grep -A 8 "  wecom:" ~/.hermes/config.yaml

# 3. 检查 gateway 进程实际的环境变量
pgrep -f "hermes.*gateway" | head -1 | xargs -I{} sh -c 'cat /proc/{}/environ | tr "\0" "\n" | grep WECOM'

# 4. 检查 .env 文件
grep WECOM ~/.hermes/.env

# 5. 检查 shell 环境变量（与进程可能不同）
env | grep WECOM
```

### 配置生效关系

```
~/.hermes/config.yaml  ← 主要配置来源（优先级高）
       ↓
~/.hermes/.env         ← 启动时通过 load_hermes_dotenv() 加载
       ↓
WECOM_BOT_ID env var   ← config.py 第 1636 行检测，如存在则覆盖 config
WECOM_SECRET env var   ← config.py 第 1637 行检测
```

### 已知可用凭据（本服务器）

- 企业 ID (corpId): `ww815119bb08398d37`
- 应用名: 超级大脑
- 应用 AgentId: 1000002
- AI Bot ID: `aibyIv3U0ehs8X8V5XxzLvyYcW0oUdeOj-j`
- AI Bot Secret: 存于 `~/.hermes/.env` 的 `WECOM_SECRET` 字段
