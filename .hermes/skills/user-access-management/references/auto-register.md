# 新用户自动注册系统

## 脚本：`~/.hermes/scripts/auto_register_users.py`

周期性扫描 Hermes DB 中的新用户，自动加入 access.yaml。

### 工作原理

```
1. sqlite3 state.db 
     SELECT DISTINCT user_id, source 
     FROM sessions 
     WHERE (source='weixin' OR source='wecom') 
       AND user_id IS NOT NULL
   2. 读取 access.yaml 获取已注册 user_id 列表
3. 差集 → 未注册的用户
4. 每个新用户 → 添加为 {id, platform, role: restricted, name}
5. 写回 access.yaml（保持现有结构）
6. stdout 输出 → 由 cron 系统投递到 Lulu 微信
```

### 平台推断逻辑

```python
def guess_platform(uid, source):
    if source in ("weixin", "wecom"):
        return source
    if "@im.wechat" in uid:
        return "weixin"
    if len(uid) < 30:
        return "wecom"  # 企微 ID 通常较短
    return "wecom"
```

### Cron 配置

- **schedule:** `every 10m`
- **mode:** `no_agent`（脚本执行，不消耗 LLM tokens）
- **script:** `auto_register_users.py`
- **deliver:** `local`（静默模式，结果仅写入 cron 输出文件，不发送消息到聊天）
- **注意：** 不要用 `deliver: origin`，否则每次运行（包括无新用户时的空跑）都会发一条消息给用户。

### 去重逻辑

脚本内部自动去重：
1. session DB 中的 user_id 已在 access.yaml 中 → 跳过
2. 短 ID 去重：`xxx@...` 和 `xxx` 视为同一用户
3. 大小写不敏感

### 测试命令

```bash
cd ~/.hermes/scripts && python3 auto_register_users.py
```

正常输出：
```
[06-04 11:54:00] 数据库中发现 1 个用户 ID
[06-04 11:54:00] 没有发现新用户，全部已注册
```

发现新用户时：
```
[06-04 12:00:00] 数据库中发现 2 个用户 ID
[06-04 12:00:00] 发现 1 个未注册用户:
  · NewUser123 (来自 wecom)
  → 已添加: NewUser123 (role=restricted, platform=wecom)
✅ access.yaml 已更新，共 5 个用户

👤 新用户已自动注册
━━━━━━━━━━━━━━
ID: NewUser123
平台: wecom
角色: restricted（仅可对话）
```

（上述通知由 cron 系统投递到 Lulu 微信）

### 与 admin 面板的集成

注册后用户自动出现在 `admin.lulugame.fun` 首页，因为 `get_library_users()` 合并读取 `users-data/` 和 `access.yaml`。无需手动建目录或重启。

### 新用户接入完整流程

```
用户发消息 → 自动注册 restricted → 面板可见
  ↓
Lulu 收到通知 → 回复「升级 xxx trusted」
  ↓
我执行 patch access.yaml → 用户角色变更
  ↓
可选：发送欢迎消息 + 天气链接
```
