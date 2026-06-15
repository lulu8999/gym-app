---
name: custom-provider-setup
description: "配置 Hermes Agent 中的自定义/第三方 LLM 提供商（如百度千帆、自建代理等），处理非标准提供商的配置陷阱和错误诊断"
version: 1.0.0
author: Lulu's AI assistant
tags: [hermes, config, llm-provider, qianfan, custom-provider]
related_skills: [safe-api-key-write, hermes-agent, vision-integration]
---

# 自定义 LLM 提供商配置指南

## 概述

Hermes Agent 支持通过 `config.yaml` 的 `model` 和 `providers` 部分配置自定义 LLM 提供商。本技能涵盖非标准提供商（如百度千帆 Qianfan、私有部署的 OpenAI 兼容 API 等）的配置流程、常见错误和解决方案。

## 核心工作流程（用户要求）

**所有新增/修改 API 提供商配置前，必须先列清完整参数给用户确认：**

```
需要确认的参数：
├─ provider name: 提供商标识（如 qianfan, xiaomi-mimo）
├─ model name:    模型名（如 glm-5.1, mimo-v2.5）
├─ api_key:       Key 来源（environment variable 或直接写入）
├─ base_url:      完整 endpoint URL
└─ provider type: 是否需要 `provider: custom`（百度千帆必须）
```

**拿到明确肯定答复后才能动手配置。** 这是 Lulu 定的红线，不可绕过。

## 快速配置流程

### 1. 写入 API Key

将 API Key 写入 `~/.hermes/.env`：

```bash
python3 /root/scripts/set_env_key.py PROVIDER_API_KEY sk-your-key-here
```

或直接写入 `config.yaml` 的 `model.api_key`（对于 `custom` 提供商通常更可靠）：

```bash
hermes config set model.api_key sk-your-key-here
```

### 2. 配置 Base URL

```bash
hermes config set model.base_url https://api.example.com/v1
```

### 3. 设置模型和提供商

```bash
hermes config set model.default your-model-name
hermes config set model.provider custom
```

### 4. 测试验证

```bash
hermes chat -q "你好"
```

## 百度千帆 (Qianfan) 特定配置

### 账户类型与端点

千帆平台有多种账户类型，必须使用对应的端点：

| 账户类型 | Base URL | 适用场景 |
|---------|----------|---------|
| 通用推理 | `https://qianfan.baidubce.com/v2` | 标准模型 (ernie-4.5-turbo 等) |
| **Coding Plan** | `https://qianfan.baidubce.com/v2/coding` | 代码生成模型 (qianfan-code-latest) |

**关键警告：** Coding Plan 的 Key 必须使用 `/v2/coding` 端点，否则报错：
```
Error: coding_plan_api_key_not_allowed
```

### ⚠️ 发现：`providers.<name>.provider` 字段可能被忽略

**真实案例（2026-06-09）：** 虽然配了 `provider: custom`，但 Hermes 网关日志显示：

```
WARNING hermes_cli.config: providers.qianfan: unknown config keys ignored: provider
```

并且即使 `api_key_env` 正确指向了 `.env` 中的有效 key，网关实际发出的请求中 Authorization header 为 `Bearer no-key-required` —— 说明 `providers.<name>` 内的 `api_key_env` **没有被网关正确读取**。

配合检查 request dump 的 bash 命令：
```bash
python3 -c "
import json, glob
dumps = sorted(glob.glob('/root/.hermes/sessions/request_dump_*.json'))
with open(dumps[-1]) as f:
    d = json.load(f)
auth = d['request']['headers'].get('Authorization', 'MISSING')
print('URL:', d['request']['url'])
print('Auth:', auth[:60])
print('Model:', d['request']['body'].get('model', 'N/A'))
"
```

### 🚨 可靠方案：key 直接写入 `model.api_key`

既然 `providers` 段的 `api_key_env` 不可靠，最稳妥的方式是**把 key 写进顶层的 `model.api_key`**：

```bash
export KEY=$(grep '^QIANFAN_API_KEY=' ~/.hermes/.env | cut -d'=' -f2-)
hermes config set model.api_key "$KEY"
```

这样无论 `providers` 段怎么配，顶层的 key 都能被网关拿到。

### `providers` 段方案（次选，仅供了解）

```yaml
model:
  provider: qianfan                # ← 引用 providers 段里的名称
  api_key: ''                      # ❌ 空字符串会覆盖 provider 层的 key！
  base_url: ''                     # ❌ 空字符串可能干扰 provider 层的 base_url

providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY
    base_url: https://qianfan.baidubce.com/v2/coding
    default_model: qianfan-code-latest
    models: '["qianfan-code-latest"]'
    provider: custom                # ⚠️ 当前版本会报 warning 可能被忽略
```

**注意陷阱：** `model.api_key: ''` 看起来无害，但会覆盖 provider 层的 key，导致网关发 `Bearer no-key-required`。写空字符串比不写更糟。

**更新流程（Lulu 场景）：**
1. 用户给新 Key → 更新 `.env` + 重新运行 `hermes config set model.api_key "$KEY"`
2. 重启网关生效

### 错误诊断对照表

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `invalid_iam_token` | Key 格式错误或过期 | 检查 Key 是否完整（应以 `bce-v3/` 开头），确认未过期 |
| `coding_plan_api_key_not_allowed` | 使用了错误的端点 | 将 base_url 改为 `https://qianfan.baidubce.com/v2/coding` |
| `coding_plan_model_not_supported` | 账户不支持该模型 | 确认是 Coding Plan 账户，或切换到通用推理端点 |
| `401 AuthenticationError` | Key 未写入或格式错误 | 检查 `model.api_key` 是否有值，不是 `api_key_env` |
| `Bearer no-key-required`（request dump 中可见） | `model.api_key: ''` 空字符串阻塞了 provider 级 `api_key_env` | 删除或填充 `model.api_key`，见上方陷阱 3 |

### ⚠️ 发现：`providers.<name>.provider` 字段可能被忽略

**真实案例（2026-06-09）：** 虽然配了 `provider: custom`，但 Hermes 网关日志显示：

```
WARNING hermes_cli.config: providers.qianfan: unknown config keys ignored: provider
```

并且即使 `api_key_env` 正确指向了 `.env` 中的有效 key，网关实际发出的请求中 Authorization header 为 `Bearer no-key-required` —— 说明 `providers.<name>` 内的 `api_key_env` **没有被网关正确读取**。

**根因：** `model` 段的 `api_key: ''`（空字符串）会被 Hermes 认为"已设置"，**优先于** `providers.<name>.api_key_env` 生效。结果网关发了一个空 key 出去。

**诊断技巧：** 检查 request dump 确认实际发送的 key：
```bash
python3 -c "
import json, glob
dumps = sorted(glob.glob('/root/.hermes/sessions/request_dump_*.json'))
with open(dumps[-1]) as f:
    d = json.load(f)
auth = d['request']['headers'].get('Authorization', 'MISSING')
print('URL:', d['request']['url'])
print('Auth:', auth[:60])
"
```
如果 Auth 显示 `Bearer no-key-required`，说明 key 没被正确读取。

### 🚨 可靠方案：key 直接写入 `model.api_key`

既然 `providers` 段的 `api_key_env` 可能被 `model.api_key: ''` 阻塞，最稳妥的方式是**把 key 写进顶层的 `model.api_key`**：

```bash
export KEY=$(grep '^QIANFAN_API_KEY=' ~/.hermes/.env | cut -d'=' -f2-)
hermes config set model.api_key "$KEY"
hermes config set model.provider custom
hermes config set model.base_url "https://qianfan.baidubce.com/v2/coding"
```

这样无论 `providers` 段怎么配，顶层的 key 都能被网关拿到。

### IAM Token 过期处理 ⚠️

**关键警告：** 百度千帆的 `bce-v3/...` 格式 Key 是 **IAM 临时令牌**，有有效期（通常几天到几周不等），**到期后必须重新生成**，不能续期。

**症状：**
- 之前能用的 Key 突然报 `invalid_iam_token`
- 没有改动过配置，curl 直测也 401

**解决流程：**
1. 去百度智能云控制台 → 千帆大模型平台 → API Key 管理，重新生成 IAM Token
2. 更新 `.env`：
   ```bash
   sed -i 's|^QIANFAN_API_KEY=.*|QIANFAN_API_KEY=<新Key>|' ~/.hermes/.env
   ```
3. 用 curl 测试：
   ```bash
   source ~/.hermes/.env
   curl -s https://qianfan.baidubce.com/v2/coding/chat/completions \
     -H "Authorization: Bearer $QIANFAN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"glm-5.1","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'
   ```
4. 如果配置用的是 `providers.<name>` 段引用了 `api_key_env`，**不需要改 config.yaml**，更新 `.env` 后重启网关即可生效
5. 如果配置用的是 `model.api_key` 直接写的字面值，需要重新写入：
   ```bash
   python3 -c "
   import os
   key = os.environ.get('QIANFAN_API_KEY', '')
   from subprocess import run
   run(['hermes', 'config', 'set', 'model.api_key', key], check=True)
   print('Key updated')
   "
   ```

**排查口诀：** 同一 provider 换 coding 模型（如 `deepseek-v4-flash`）测 → 通了说明不是 Key 问题，而是模型不兼容。还是 401 → Key 过期。

### 实战案例：从错误到成功

**情境：** 用户提供了 Qianfan Coding Plan 的 Key 和 URL `https://qianfan.baidubce.com/v2/coding`，配置后报 401。

**诊断过程：**

1. 检查请求转储，发现请求发到了 `https://qianfan.baidubce.com/v2/chat/completions`（缺少 `/coding`）
2. 检查配置，发现 `model.api_key_env` 被当成字面量处理
3. 修改 base_url 为完整的 `https://qianfan.baidubce.com/v2/coding`
4. 将 Key 直接写入 `model.api_key` 而不是 `model.api_key_env`

**成功配置：**
```bash
hermes config set model.base_url "https://qianfan.baidubce.com/v2/coding"
hermes config set model.api_key "bce-v3/ALTAKSP-..."
hermes config set model.api_key_env ""  # 清空不可用的 env 引用
```

## 通用配置陷阱

### 1. api_key_env vs api_key — 作用域不同

`api_key_env` 在 `model` 段和 `providers` 段行为不同：

| 位置 | 表现 | 推荐方式 |
|------|------|---------|
| `model` 段 | 部分版本有兼容问题，可能被当字面量处理 | 直接写 `model.api_key` |
| `providers.<name>` 段 | ⚠️ 存在隐患：`model.api_key: ''` 空字符串会覆盖 provider 级 `api_key_env` | 双管齐下（见下方方案） |

**场景判断：**
- 如果只有一个 provider → 用 `model` 段，`api_key` 直接写
- 如果有多个 provider 共存（如 Lulu 的 qianfan + xiaomi-mimo）→ 用 `providers` 段，`api_key_env` 引用 `.env`

### 2. model.provider ≠ providers.<name>.provider

这两个 `provider` 字段含义完全不同：

```yaml
model:
  provider: qianfan         # ← 引用 providers 段里的名称

providers:
  qianfan:
    provider: custom         # ← 声明接口协议类型（缺了就 401！）
```

| 字段 | 位置 | 含义 | 常见值 |
|------|------|------|-------|
| `model.provider` | `model` 段 | 选择用哪个 provider 配置 | `qianfan`, `xiaomi-mimo` |
| `providers.<name>.provider` | `providers` 段内 | 声明 API 格式类型 | `custom`, `openai`, `anthropic` |

**千帆 Coding Plan 必须写 `provider: custom` 在 `providers.<name>` 块内。**

### 3. `model.api_key: ''` 空字符串阻塞 provider 级 api_key_env ⚠️

**症状：** curl 直测 API 正常，但 Hermes 网关报 `invalid_iam_token`。检查 request dump 发现 Authorization header 是 `Bearer no-key-required`。

**根因：** `model` 段的 `api_key: ''`（空字符串）会被 Hermes 认为"已设置"，**优先于** `providers.<name>.api_key_env` 生效。结果网关发了一个空 key 出去。

```yaml
# ❌ 错误 — model.api_key 是空字符串，阻塞了 providers.qianfan.api_key_env
model:
  api_key: ''              # ← 这个空字符串抢了优先级！
  provider: qianfan

providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY   # ← 配了但没用上
```

**修复方式（选一个）：**

**方案 A：** 把 `model.api_key` 设为实际 key 值（最可靠）
```bash
hermes config set model.api_key "$QIANFAN_API_KEY"
```

**方案 B：** 完全删除 `model.api_key` 字段（让 provider 级配置接管）
```yaml
model:
  # api_key: ''   ← 删掉这一行
  provider: qianfan
```

**验证：** 改完后再查 request dump，确认 Auth header 从 `Bearer no-key-required` 变成 `Bearer bce-v3/...`。

### 4. base_url 残留

切换提供商时，旧的 `model.base_url` 可能残留并覆盖新配置：

```bash
# 检查残留
hermes config show | grep base_url

# 清理
hermes config set model.base_url ""
```

### 5. 请求路径自动补全

Hermes 会在 `base_url` 后自动添加 `/chat/completions`：

| 配置的 base_url | 实际请求 URL |
|---------------|-------------|
| `https://api.example.com/v1` | `https://api.example.com/v1/chat/completions` |
| `https://qianfan.baidubce.com/v2/coding` | `https://qianfan.baidubce.com/v2/coding/chat/completions` |

**确保你配置的 base_url 是不含 `/chat/completions` 的前缀路径。**

## 验证技巧

### 用 xxd 验证密钥写入

当 `redact.py` 遮挡显示时，用 `xxd` 查看实际写入的内容：

```bash
xxd /root/.hermes/.env | grep -A2 QIANFAN
# 应看到 62 63 65 2d 76 33 2f... （bce-v3/ 的 hex）
```

### 用 curl 测试原生 API

绕过 Hermes 直接测试提供商：

```bash
source ~/.hermes/.env
curl -s https://qianfan.baidubce.com/v2/coding/chat/completions \
  -H "Authorization: Bearer ${QIANFAN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"qianfan-code-latest","messages":[{"role":"user","content":"hi"}]}'
```

如果 curl 成功但 Hermes 失败 → 配置问题（base_url/api_key 错误）。
如果 curl 失败 → 密钥或网络问题。

## 关联技能

- `safe-api-key-write`: API Key 安全写入和验证
- `hermes-agent`: Hermes 核心配置说明
- `vision-integration`: 视觉模型配置（含 MiMo/Kimi）
