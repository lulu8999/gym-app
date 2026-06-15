---
name: user-access-management
description: Manage user access permissions (access.yaml) on command. Supports listing, adding, removing, and changing user roles.
---

# 用户权限管理

你（Lulu）可以通过以下指令管理用户权限。我来操作 `~/.hermes/access.yaml`。

## 支持的命令格式

| 你说 | 我做 |
|------|------|
| `查权限` 或 `权限列表` | 读取 access.yaml，列出所有用户及其角色 |
| `加权限 <id/名字> <角色>` | 添加新用户并指定角色 |
| `改权限 <id/名字> <新角色>` | 修改已有用户的角色 |
| `删权限 <id/名字>` | 从 access.yaml 移除用户 |

## 角色说明

| 角色 | 等级 | 权限 |
|------|------|------|
| **admin** | 最高 | 全部权限，包括终端执行、写文件、改 skill、管理 cron |
| **trusted** | 中等 | 读文件、查信息、用已有功能；不能改配置和执行命令 |
| **restricted** | 最低 | 仅对话，不能调任何工具（未来公开使用） |

## 工具权限矩阵

| 工具分类 | admin | trusted | restricted |
|---------|-------|---------|------------|
| 普通对话/查信息 | ✅ | ✅ | ✅ |
| 读文件 | ✅ | ✅ | ❌ |
| 写文件/改配置/终端 | ✅ | ❌ | ❌ |
| skill 管理 | ✅ | ❌ | ❌ |
| cron 管理 | ✅ | ❌ | ❌ |
| 子任务（delegate_task） | ✅ | ❌ | ❌ |

## 用户 ID 获取

- **微信（weixin）**：用户 ID 格式如 `o9cq80-xxxxx@im.wechat`，我可以在对话中看到
- **企微（wecom）**：用户 ID 是企业微信的 UserID，你可以从企微管理后台查到

## 实际例子

```
你：加权限 FengZaiQiShi trusted
我：已将 FengZaiQiShi（风再起时）设为 trusted

你：改权限 师父 admin  
我：已将师父的角色改为 admin

你：查权限
我：当前用户列表：
    Lulu (o9cq80-xxx... ) → admin
    师父 (FengZaiQiShi)    → trusted
    老爹 (LuWeiFeng)       → trusted
```

## 新用户接入流程

### 第一步：自动注册（无需手动操作）

系统每 10 分钟自动扫描 Hermes DB 中是否有新用户 ID（weixin/wecom 平台）：

```
新用户发消息到企微 Bot
  ↓（10分钟内）
auto_register_users.py 检测到新 user_id
  ↓ 访问 access.yaml
新用户不在列表中？→ 自动添加为 restricted
  ↓
access.yaml 更新 → admin.lulugame.fun 自动显示
  ↓
微信通知 Lulu："👤 新用户 xxx 已自动注册"
```

**自动注册脚本：** `~/.hermes/scripts/auto_register_users.py`
- 每 10 分钟通过 cron 运行
- 查找 DB 中所有 `source = weixin/wecom` 且不在 access.yaml 里的 user_id
- ⚠️ **不检测 `source = wecom_callback`** — 通过企微回调模式（corpId+agentId）发消息的用户不会被自动扫描到。需要手动加：直接编辑 access.yaml 或通过「加权限」命令
- 自动添加为 `role: restricted`
- stdout 输出由 cron 系统直接投递到 Lulu 微信
- 无需人工干预

**新用户注册后：**
- admin.lulugame.fun 上自动出现（无需手动建目录）
- 角色为 restricted（仅可对话，不能调任何工具）
- 你可以回复「升级 xxx trusted」来提升权限

### 第二步：权限提升

用户自动注册为 restricted 后，你可以通过以下方式提升：

| 你说 | 我做 |
|------|------|
| `升级 xxx trusted` | 将用户 xxx 改为 trusted 角色 |
| `升级 xxx admin` | 将用户 xxx 改为 admin 角色（谨慎） |
| `改名 xxx 显示名` | 修改用户显示名称 |

### 第三步（可选）：发送欢迎消息

**重要原则：发消息给第三方前，先给用户（Lulu）看内容，他确认了再发。** 不要直接发送。

新用户加入后，发欢迎词介绍自己。欢迎词要：
- **称呼**：自称「小小团」或「小小陆」（不要叫小脑、助理等怪异名字）
- **语气**：礼貌、幽默风趣
- **自我介绍**：是陆海天的 AI 助手
- **功能引导**：根据对方身份介绍可提供的帮助（如织毛衣教程、报表整理等）
- **天气推送**：引导用户点击定位链接：`https://loc.lulugame.fun/?user=用户名`
- **权限下放**：不发送股票报告，不涉及系统操作
- **夸人原则**：夸对方聪明漂亮要自然，不要用"古灵精怪"等评价性词语
- **发前确认**：写好内容后先给 Lulu 审稿，他点头再通过 `send_wecom.py` 发送
- **发送路径**：`send_wecom.py` 位于 `/root/stock_analyzer/send_wecom.py`（不是 `~/.hermes/scripts/`）
  用法：`python3 /root/stock_analyzer/send_wecom.py <user_id> "消息内容"`
- **定位链接**：发欢迎词时同步发送定位链接 `https://loc.lulugame.fun/?user=显示名`

欢迎词模板参考 `references/welcome-mom.md` 和 `references/welcome-wife.md`。

### 第四步（可选）：开启多模态能力
如果需要看图、分析图片，可以给用户配置 Kimi 视觉模型：
- Kimi API 已配置在 providers.kimi，使用 kimi-coding 后端
- 视觉模型：`moonshot-v1-8k-vision-preview` / `32k` / `128k`
- 日常对话和编程继续走 DeepSeek
- 需要看图时通过 delegate_task 派子 agent 用 Kimi 处理

### 第五步（可选）：开启每日天气
如果用户点了定位链接，创建早 8 点的 cron 天气播报：
- 需要先获取用户位置（通过定位服务）
- 再创建 cron 任务，每天 8:00 查询天气并推送
- 报告格式：地点 + 今天气温 + 天气状况 + 温馨提醒

## 限制与注意

- 仅企微（weixin/wecom）平台受权限控制，CLI 和 cron 完全放行
- 受限用户越权时自动拦截并回复「你没有权限，已转发给管理员」
- 建议转发目前由 agent 对话层面处理，非自动
