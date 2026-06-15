---
name: model-watchdog
description: "模型看门狗系统 — 自动检测 LLM API 不可用，通过企微通知用户选择切换模型"
version: 2.0.0
author: Lulu
tags: [watchdog, model-switch, wecom, monitoring]
---

# 模型看门狗系统

## ⚠️ 已废弃（2026-06-05）

用户决定废弃模型看门狗脚本，改为在终端手动切换模型。脚本和 crontab 已删除：
- `rm /root/scripts/model_watchdog.py`
- crontab 中的 `*/1 * * * *` 条目已移除

如需恢复，参考下方的文件位置和逻辑重写。

## 文件位置（已删除）

- ~~`/root/scripts/model_watchdog.py`~~ — 已删除
- ~~`/tmp/model_watchdog/`~~ — 运行时状态目录（残留文件可清理）
  - `status.json` — 当前告警状态
  - `alert_sent` — 上次告警时间戳（防刷屏）
  - `apply_choice.sh` — 动态生成的模型切换脚本
  - `switch_history.log` — 切换历史

## 定时任务（已删除）

~~每 1 分钟由 cron 触发~~ — crontab 条目已移除。

## 工作流程

1. 用 Python urllib 检测当前模型 API（`{base_url}/models`），不自建 SDK 依赖
2. 正常 → 清除告警状态，退出
3. 失败 → 动态扫描 `.env` 找出哪些 API Key 已配置，自动生成可用模型列表
4. 发送企微通知给 KuHai/LuHaiTian，附带可选项（编号 1~N）
5. 用户返回 Hermes 对话回复数字
6. 用 `hermes config set model.default/provider/base_url` 切换（Hermes 内置命令，不用 sed）
7. 切换后通知用户，清除告警状态

**被动设计原则**：看门狗只负责检测 + 告警，切换动作由用户在 Hermes 对话中发起。这是有意的 — 切换脚本（apply_choice.sh）是静态的，对话中的我才做实际决策。

## 分支逻辑

| 可用备选数 | 行为 |
|-----------|------|
| 0 | 企微通知：无备用 Key，请用户提供新 API Key + URL |
| 1 | 自动切换，企微通知"已自动切换" |
| ≥2 | 企微发选项列表，用户回复数字选择 |

## 动态模型检测

`PROVIDER_MODELS` 字典定义支持的 provider 和 Key 环境变量名。脚本扫 `.env` 中有哪些 Key 存在，自动加入可用列表。

**新增 Key 流程**：用户在微信给 Key + URL → 写入 `.env` → 添加到 `PROVIDER_MODELS` → 下次 cron 自动出现。

当前支持（仅有实际配置的 Key 才显示）：
- DeepSeek（DEEPSEEK_API_KEY）：flash, pro
- 小米 MiMo（XIAOMI_API_KEY）：mimo-v2-flash, mimo-v2-pro, mimo-v2.5, mimo-v2.5-pro
- Kimi（KIMI_API_KEY）：moonshot-v1-8k-vision-preview 等

## 关键设计决策

1. **`hermes config set` 优先于 sed** — 用 Hermes 内置命令改配置，不改 .yaml 格式细节
2. **Python 优先于 Bash** — 纯 Python 脚本避免 bash 多行 curl 的引号问题
3. **动态生成 apply_choice.sh** — 每次检测失败时根据当前可用模型重新生成，不会过时
4. **编号选择（数字）** — 企微消息中用户回复数字，简单直接
5. **30 分钟防刷屏** — 告警写入时间戳文件，不重复打扰
6. **零 AI 依赖** — 不用 LLM 检测 LLM，避免循环依赖

## 关键特性

- 零 AI 依赖：纯 Python + urllib 检测 API
- **动态检测模型**：扫 `.env` 的 API Key，不硬编码
- 30 分钟防刷屏
- 自动恢复清除
- 切换日志记录
- 无备选时通知用户提供新 Key

## 陷阱清单（从实际开发中总结）

### 1. Bash 多行 curl 引号

`"Authorization: Bearer $api_key \` 中 `\"` 不会关闭字符串！  
`\` 行连续符 + `\"` 转义引号的组合效果是：字符串持续到 EOF。  
→ **改用 Python urllib** 即可彻底避免。（见 `references/bash-multiline-quoting.md`）

### 2. `__import__('urllib.request')` 返回顶层模块

`__import__('urllib.request')` 返回的是 `urllib`（顶层包），不是 `urllib.request`（子模块）。  
→ 必须 `import urllib.request` 显式导入。（见 `references/python-import-trap.md`）

### 3. 嵌套 heredoc 不能工作

Bash 中不能在 heredoc 内嵌另一个 heredoc。  
→ 改用 Python 写文件，或 printf/echo 逐行构建。

### 4. .env 的 `source` 加载

`source .env` 在 `set -e` 下可能静默失败（某些 .env 行对 bash 有语法问题）。  
→ Python 逐行解析 `.env` 更可靠：按 `=` 分割、去引号、跳过注释。

### 5. 不要把 DashScope/千问 的无效 Key 列进选项

如果 `.env` 中有旧/无效的 Key，API 检测会返回 401。但看门狗只检查 Key 是否存在（"未空"），不验证有效性。  
→ 愿意的话可以加一次轻量验证，但会增加检测延迟。当前策略是让用户试了再说。

### 6. `hermes_self_heal.py` 备份会覆盖新 Key

`hermes_self_heal.py` 的 `do_backup()` 会把 `.env` 和 `config.yaml` 打包进 `~/.hermes/backups/`。如果之后执行 `do_restore()`，它会**用旧备份中的 `.env` 覆盖当前文件**，导致新更新的 API Key 被旧 Key 替换。

该脚本没有设置 cron 自动运行，但手动执行 `python3 hermes_self_heal.py check` 时会先备份再检查。每次备份之间若更新了 Key，恢复旧备份就会丢失新 Key。

**对策：** 更新 Key 后确认没有旧备份需要保留；或者将 `.env` 从 `BACKUP_PATHS` 中移除（取决于是否接受 Key 不备份的风险）。

### 7. `write_file` 工具会掩码 `sk-xxx` 模式的 Key

Hermes 的 `write_file` 工具会自动将内容中的 `sk-xxx` 格式字符串替换为 `***`，写入 .env 后 Key 被破坏。这是内置保护机制，但会损害 Key 写入的正确性。

**对策：** 写 API Key 到文件时，必须用 `sed` 替换现有行，或 Python 逐行写入文件。不能用 `write_file` 直接写含 Key 的内容。详见 `references/env-key-management.md`。

### 8. HTTP 429 速率限制错误

当 API 返回 `HTTP 429: Too many requests` 时，表示请求频率超限。常见原因：
- 短时间连续调用了太多次 API
- 多个程序同时用同一个 API Key
- 服务器本身有请求频率限制（如 DeepSeek 在整点前后可能有 180 秒流卡顿）

**对策：**
1. **等一会儿再试**（通常几秒到几分钟就恢复）
2. **减少并发请求**，别同时发太多
3. **检查是不是有脚本在疯狂刷接口**
4. **在看门狗中加入重试逻辑** — 遇到 429 时等待一段时间再重试，而不是立即判定为失败

### 9. 禁用/移除模型提供商

当需要完全禁用某个模型提供商（如千帆）时，不能只删除 `.env` 中的 API Key，还需要从 `config.yaml` 的 `providers` 部分移除配置。

**正确步骤：**
1. 编辑 `~/.hermes/config.yaml`，删除 `providers:` 下对应的提供商配置块
2. 如果需要，重启网关使配置生效：`systemctl --user restart hermes-gateway`
3. 检查是否有 cron 任务或其他脚本引用了该提供商

**错误做法：** 只删除 API Key 而保留配置，会导致配置中有无效的提供商定义。

## Bash → Python 迁移决策树

当 I/O 脚本需要以下任何一项时，**直接写 Python**，别从 Bash 开始：

```
需要多行 curl？          → Python urllib.requests
需要嵌套 heredoc？       → Python write()  
需要数组/字典操作？      → Python dict/list
需要条件分支+循环？       → Python if/for
需要处理 API JSON 响应？ → Python json.loads
有环境变量操作？          → Python os.environ
```

Python 版仍然**零 AI 依赖**（只用了 `os/sys/json/time/subprocess/urllib.request/fcntl`，全是标准库），比 Bash 更少坑。

## 参考文件

- `references/python-import-trap.md` — `__import__('urllib.request')` 返回顶层模块而非子模块
- `references/bash-multiline-quoting.md` — Bash 多行 curl 引号陷阱（`\\\"` 不关闭字符串）
- `references/vision-capability.md` — 当前环境 vision 模型排查记录
- `references/env-key-management.md` — .env 文件 Key 写入陷阱：write_file 会掩码 sk-xxx，必须用 sed/Python：各模型是否支持视觉、API Key 在哪、LiteLLM 假阳性陷阱、故障诊断流程
