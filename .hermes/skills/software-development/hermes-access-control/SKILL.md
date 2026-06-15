---
name: hermes-access-control
description: 在 Hermes Agent 中实现用户权限分级系统。基于 plugin 的 pre_tool_call hook 拦截工具调用，按角色控制企微用户的操作权限。
version: "1.1"
---

# Hermes 用户权限分级系统

为企微（WeChat Work）用户实现权限控制，阻止越权操作，同时支持将受限用户的建议转发给管理员。

## 触发条件

需要实现或理解 Hermes 用户权限系统时加载本技能。

## 角色设计

| 角色 | 等级 | 权限 | 适用 |
|------|------|------|------|
| `admin` | 3 | 全部权限 | 系统管理员（Lulu） |
| `trusted` | 2 | 日常对话、查信息、用已有功能；不能改配置、skill、执行命令、加 cron | 师父、老爹等可信任用户 |
| `restricted` | 1 | 仅预设问答类功能，不能调工具 | 未来公开用户 |
| `blocked` | 0 | 不响应 | 拉黑用户 |

## 工具权限矩阵

| 工具分类 | tools | admin | trusted | restricted |
|---------|-------|-------|---------|------------|
| 读文件 | read_file, search_files | ✅ | ✅ | ❌ |
| 写文件 | write_file, patch | ✅ | ❌ | ❌ |
| 终端 | terminal | ✅ | ❌ | ❌ |
| skill 管理 | skill_manage | ✅ | ❌ | ❌ |
| cron 管理 | cronjob | ✅ | ❌ | ❌ |
| 子任务 | delegate_task, execute_code | ✅ | ❌ | ❌ |
| 会话 | session_search | ✅ | ❌ | ❌ |
| 系统 | memory, clarify, send_message, todo, process, image_generate, text_to_speech | ✅ | ✅ | ❌* |

*restricted 可选的预设功能按需开放，默认全禁。

## 存储方案

使用 `~/.hermes/access.yaml`，结构：

```yaml
users:
  - user_id: "o9cq80-xxxxx"
    role: admin
    name: Lulu
  - user_id: "shifu-xxx"
    role: trusted
    name: 师父
  - user_id: "laodie-xxx"
    role: trusted
    name: 老爹

# 建议转发设置
suggestion_forward:
  enabled: true
  admin_user_id: "o9cq80-xxxxx"
```

## 实现方式

### 1. Plugin 方案（推荐）

利用 Hermes 现有的 plugin 系统，注册 `pre_tool_call` hook。

**文件结构：**
```
~/.hermes/plugins/access_control/        # 用户插件目录（优先于 agent 自带插件）
├── plugin.yaml     # 声明 pre_tool_call hook
└── __init__.py     # 权限检查逻辑
```

注意插件在 `~/.hermes/plugins/`（用户插件目录），**不是** `hermes-agent/plugins/`。用户插件优先级高于打包插件，且网关重启后自动恢复，无需重新创建。

**plugin.yaml：**
```yaml
name: access-control
version: "0.1.0"
description: "User access control for WeChat Work — block unauthorized tool calls based on user role."
hooks:
  - pre_tool_call
```

**关键逻辑（__init__.py）：**
- `register(ctx)`: 注册 `pre_tool_call` hook
- `_on_pre_tool_call(tool_name, args)`: 拦截入口
  - 获取当前会话的 platform 和 user_id（从 session_context 环境变量）
  - 非企微会话→放行（CLI 不拦）
  - 查 access.yaml 获取用户角色
  - 用户在 blocked 列表→不响应
  - 判断工具是否在禁调列表→block + 转发建议
  - 否则放行

**获取当前用户：**
```python
from gateway.session_context import get_session_env
platform = get_session_env("HERMES_SESSION_PLATFORM")
user_id = get_session_env("HERMES_SESSION_USER_ID")
```

### 2. Sage 建议转发

当 trusted/restricted 用户的对话内容疑似建议时：
1. 回复："你没有权限，已转发给管理员"
2. 通过 `send_message` 或企微 API 转发给 admin：
   - "💡 [用户名] 提了个建议：[原文] 要采纳吗？回 y / n"

建议检测信号：用户说"能不能""可以加""建议""有没有""如果..."

### 3. 管理命令

通过 agent 对话实现管理：
- "查权限" → 读 access.yaml 列出所有用户
- "加权限 [名字] [角色]" → 写入 access.yaml
- "删权限 [名字]" → 移除用户条目
- "改权限 [名字] [新角色]" → 更新角色
- "查我的 ID" → 读取 session_context 中的 user_id

## 新用户自动注册（auto_register）

新用户向企微 Bot 发消息时，自动发现并注册。脚本位于 `~/.hermes/scripts/auto_register_users.py`。

### 关键原则

- **只记录可验证的数据** — 时间戳必须从 cron 输出文件名或 session DB 解析，不猜测
- **只记录实际发送的消息** — 不将对话中"提到"某用户当作"发给了"该用户
- **自动注册为 restricted** — 新用户默认仅可对话，管理员可手动提权

### 核心逻辑

```python
def scan_and_register():
    # 1. 从 state.db 获取所有 weixin/wecom user_id
    cur = conn.execute("SELECT DISTINCT user_id, source FROM sessions ...")
    # 2. 与 access.yaml 已注册用户比对
    existing_ids = set(u['id'] for u in data.get('users', []))
    # 3. 未注册的 → 自动加入（role=restricted）
    for uid in unregistered:
        data['users'].append({
            'id': uid, 'platform': guess_platform(uid),
            'role': 'restricted', 'name': uid,
        })
    # 4. 写回 access.yaml
    yaml.dump(data, f, allow_unicode=True)
    # 5. 通知管理员（cron no_agent 模式自动投递 stdout）
    print(f"👤 新用户已自动注册: {uid}")
```

### 部署为 cron（no_agent，零 token）

```bash
hermes cron create --schedule "every 10m" \
  --script auto_register_users.py \
  --no-agent --name "🆕 新用户自动检测注册"
```

**⚠️ 先在对话中询问用户意见再部署。** 自动注册 cron 会每 10 分钟静默扫描一次数据库，如果用户不希望收到频繁的"新用户已注册"通知，或希望手动控制新用户准入，就不应该部署这个 cron。

### 状态确认

通过 `hermes cron list` 检查 job 状态。脚本每 10 分钟运行一次，输出通过 cron 系统自动投递到管理员微信。

### 工作流

```
用户发消息到企微 Bot → state.db 记录
  ↓ (10分钟内)
auto_register cron 扫描到新 user_id
  ↓ 比对 access.yaml → 自动添加（restricted）
access.yaml 更新 → admin 面板立即显示
  ↓ cron 投递通知到管理员微信
管理员回复「升级 <ID> trusted」提权
```

### 依赖项

- `~/.hermes/state.db` — Hermes session 数据库
- `~/.hermes/access.yaml` — 用户权限配置
- `~/.hermes/scripts/auto_register_users.py` — 自动注册脚本

## 注意事项

- 插件注册后需要重启网关：`hermes gateway restart`
- **自动注册不影响已有用户** — 只处理 state.db 中有但 access.yaml 没有的 user_id
- **agent 发消息不受限制** — access control 只对 weixin/wecom 平台的外部用户生效，agent 自己的 send_message 和 cron 推送不受影响
- 测试时可以先写 demo 版逐条验证
- 用户 ID 在企微中是稳定不变的
- plugin 的 pre_tool_call block 返回格式：`{"action": "block", "message": "..."}`
- security-guidance 插件是现有参考实现，位于 `plugins/security-guidance/`
- **网关重启后先查文件系统** — `~/.hermes/plugins/access_control/` 和 `~/.hermes/access.yaml` 已在文件系统中存在的话，不要重复创建。先 `ls ~/.hermes/plugins/` 检查已有插件，再从已有配置继续。
- **网关重启恢复** — 插件文件存在文件系统中，网关重启后自动加载，不需要重新创建。下次会话先检查 `~/.hermes/plugins/` 和 `~/.hermes/access.yaml` 是否已存在再开始。
- **文件系统优先** — 当会话被网关中断后恢复时，优先检查文件系统中有无已存在的插件、配置等，避免重复创建。
