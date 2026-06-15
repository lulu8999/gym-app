# 企微消息日志集成（Admin Panel）

在 `hermes-admin-panel` 中显示发送给 企业微信 用户的历史消息（单向推送、互动回复等）。

## Architecture

```
send_message() 调用
      │
      ▼
wecom_log.log(recipient, content)    ← 每次发消息时记录
      │
      ▼
~/.hermes/wecom_message_log.jsonl    ← 追加日志
      │
      ▼
get_sent_messages_for_user(name)     ← Admin 面板读取
      │
      ▼
用户详情页显示「已发消息」列表
```

## 日志模块

`~/.hermes/scripts/wecom_log.py`

```python
def log(recipient, content, msg_type="push", source="system"):
    entry = {
        "ts": time.time(),
        "recipient": recipient,
        "display_name": USER_NAMES.get(recipient, recipient),
        "content": content[:500],
        "msg_type": msg_type,   # push / cron / interactive
        "source": source,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def get_messages(recipient=None, limit=50):
    msgs = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except:
                continue
            if recipient and entry.get("recipient") != recipient:
                continue
            msgs.append(entry)
    msgs.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return msgs[:limit]
```

## Admin 面板集成

### app.py 函数

```python
def get_sent_messages_for_user(user_name):
    """读取发给某个用户的企微消息记录"""
    ids_to_check = []
    # 从 access.yaml 找该用户的所有 ID
    ACCESS_PATH = os.path.expanduser('~/.hermes/access.yaml')
    if os.path.exists(ACCESS_PATH):
        import yaml
        with open(ACCESS_PATH) as f:
            access = yaml.safe_load(f) or {}
        for u in access.get('users', []):
            name = u.get('name', '')
            if name.lower() in user_name.lower() or user_name.lower() in name.lower():
                ids_to_check.append(u['id'])
    # 也尝试 channel_id
    profile = get_user_profile(user_name)
    ids_to_check.append(profile.get('channel_id', ''))
    ids_to_check = [x for x in ids_to_check if x]

    if not os.path.exists(WECOM_LOG_PATH):
        return []

    msgs = []
    with open(WECOM_LOG_PATH, encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except:
                continue
            rid = entry.get('recipient', '')
            if not any(rid == cid for cid in ids_to_check):
                continue
            ts = entry.get('ts')
            if ts:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc) + timedelta(hours=8)
                entry['time_str'] = dt.strftime('%m-%d %H:%M')
            msgs.append(entry)

    msgs.sort(key=lambda x: x.get('ts', 0), reverse=True)
    return msgs

@app.route('/user/<name>')
def user_detail(name):
    sent_messages = get_sent_messages_for_user(name)
    return render_template('user.html', sent_messages=sent_messages)
```

### 首页消息计数

```python
# In index() route
sent_counts = {}
for u in users:
    sent_counts[u['name']] = len(get_sent_messages_for_user(u['name']))
return render_template('index.html', sent_counts=sent_counts)
```

## 历史回填

`backfill_wecom_log.py` 从已有数据中提取已发送消息：

**安全数据来源：**
1. **Cron 输出文件** (`~/.hermes/cron/output/<job_id>/*.md`) — 从任务配置的收信人列表 + 执行时间戳提取
2. **手动补录** — 已知的重要推送（欢迎词、鼓励消息等）用 `known` 列表硬编码

**去重策略：** 按 `(recipient, round(ts/60), content[:50])` 去重。

## 注意事项

### 1. 看门狗类噪声

watchdog cron 每 20 分钟运行一次但没有实际消息内容，需在回填时过滤掉 `source` 含"看门狗"的条目。

### 2. JSONL 是追加写入

不会因为多次运行回填脚本产生重复（靠去重逻辑保证）。

### 2. ⚠️ 回填数据准确性：勿混淆"提及"与"实际发送"

**这是常见的回填陷阱。** 不要写一个函数来扫描 session 数据库中所有 assistant 消息，然后通过关键词（如 `content LIKE '%FengZaiQiShi%'`）判断是否发给了某用户。

原因：agent 在回复中**提到**某个用户（例如「师父和老爹已经收到晨报了」）时，这条消息是发给当前对话人（Lulu）的，不是发给师父/老爹的。

**在之前的 session 中，这个函数被直接删除了** — 它产生了 15 条误填记录（把 agent 回复中提及用户的消息当成了发给该用户的消息）。

**正确做法：**
- **Cron 输出文件** — 从 `~/.hermes/cron/output/<job_id>/*.md` 提取，根据 cron job 配置的收信人列表匹配
- **手动发送** — 记录在 `known` 列表中硬编码。仅当用户明确告知时间后才写入
- **仅记录实际触达的消息** — 不要用 session DB 的 assistant 消息反向推断收信人

### 3. ⚠️ 时间戳：只记录可验证的时间

**永远不要猜测消息发送时间。** 这是用户最不能接受的错误——"你猜时间干啥"。

如果数据库或 cron 输出中没有精确的时间戳记录，就不要创建该日志条目。

正确的时间戳来源（优先级从高到低）：
1. **cron 输出文件名** — 格式 `YYYY-MM-DD_HH-MM-SS.md`，解析为精确 Unix 时间戳
2. **Hermes session DB** — `messages.timestamp` 字段（仅当消息是通过 Hermes gateway 发送的）  
3. **企微 API 返回** — 调用 `/cgi-bin/message/send` 时 API 返回的 `msgid` 和 `create_time`

**绝对不要做的：**
- 根据"大概什么时候"估算时间戳
- 用相近的其他活动时间代替
- 用 context compaction 中的文字描述推算时间
- 将 assistant 消息的时间戳当作发送时间（尤其是提到用户但并非发给该用户的消息）
- 用 unix 时间戳的"整数估算"（如 1780490000）硬编码代替真实时间
- 在硬编码 `known` 列表中使用凭感觉估算的时间戳 — 宁缺毋滥

**如果用户纠正了时间：** 立即更新 JSONL 中的 `ts` 字段和 `known` 列表中的硬编码值。如果用户告诉你的时间和你猜的不同，直接承认错误，不要辩解。修正时间戳的流程：
1. 直接编辑 `wecom_message_log.jsonl` 中对应条目的 `ts`
2. 同步更新 `backfill_wecom_log.py` 中的 `known` 列表
3. 验证面板显示正确的时间

**如果无法从以上来源确定精确时间：** 不要猜测，直接跳过该条目。让用户告诉你正确时间，然后按用户说的写入。已写入但时间不对的条目应当被删除重建——错误的时间比没有时间更糟糕。

如果无法从以上来源确定精确时间，跳过该条目而不是猜测。

### 4. ⚠️ Cron 任务管理：区分"不要提醒"和"不要运行"

当用户说「取消提醒/停止提醒」时：

| 用户真实意图 | 正确的操作 |
|-------------|-----------|
| 不要发消息提醒我，但脚本继续跑 | `hermes cron update <ID> --deliver local` |
| 暂时停掉 | `hermes cron pause <ID>` |
| 彻底不跑了 | `hermes cron remove <ID>` |

**常见错误：** 用户说「不要提醒了」时错误地删除整个 cron 任务。用户纠正：\"我只是不要提醒，你别把注册脚本给我删了\"。

默认创建自动注册类 cron 时用 `deliver: local`（静默模式），运行结果只写日志不发消息：

```bash
hermes cron create --schedule "every 10m" \
  --script auto_register_users.py \
  --no-agent --deliver local --name "新用户自动检测注册"
```

### 5. 虚拟用户自动显示

access.yaml 中的用户**不需要**对应的 users-data 目录即可在首页显示。`get_library_users()` 会合并 users-data 目录和 access.yaml，在 access.yaml 中有但没目录的用户自动创建虚拟条目（`from_access=True`）。虚拟用户的详情页通过 `get_user_profile()` 回退到 access.yaml 提取信息。

### 6. 未来消息自动记录

通过 Hermes 企业微信通道发送消息时，自动调用 `wecom_log.log()` 记录：

```python
from wecom_log import log
log(recipient="FengZaiQiShi", content="消息内容", msg_type="push", source="interactive")
```

对于 cron no_agent 脚本，消息日志的回填应从 cron 输出目录提取（有精确的文件修改时间），不需要脚本内部额外调用。

### 7. 新用户自动发现与注册

`~/.hermes/scripts/auto_register_users.py` 自动扫描并注册新企微用户：

```python
def scan_and_register():
    # 1. 从 state.db 获取所有 weixin/wecom user_id
    # 2. 与 access.yaml 已注册用户比对
    # 3. 新用户 → 自动加入（role=restricted）
```

部署为每 10 分钟 cron（no_agent 模式，零 token 消耗，**静默运行**）：

```bash
hermes cron create --schedule "every 10m" \
  --script auto_register_users.py \
  --no-agent --deliver local --name "新用户自动检测注册"
```

`deliver: local` 表示脚本结果只写入 cron 输出文件，不发送任何消息到聊天。这样既保持了自动注册功能，又不会因为每次运行都产生空通知而骚扰用户。

工作流：
```
用户发消息到企微 Bot → state.db 记录
  ↓ (10分钟内)
auto_register 扫描 → access.yaml 新增（restricted）
  ↓
面板自动显示新用户
```

管理员如需提权：通过 `user-access-management` skill 手动升级。无需脚本通知。
