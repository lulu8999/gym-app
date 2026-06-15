---
name: custom-model-provider-config
description: "配置 Hermes 的自定义模型提供商（Custom Provider），解决认证、端点、环境变量等配置问题"
version: 1.0.0
author: Hermes Agent
tags: [config, provider, model, api, troubleshooting]
related_skills: [hermes-agent]
---

# 自定义模型提供商配置指南

配置非内置提供商（如千帆、DeepSeek 自建等）时的标准流程和排错方法。

## ⚠️ 红线规则：先确认，再配置

**所有 API 配置必须走以下流程，不得擅自执行：**

```
1. 列出完整参数 → provider、model、api_key、base_url、特殊注意点
2. 发给用户确认 → 等用户说"加"或"搞"才动手
3. 再执行配置 → 更新 .env + config.yaml
```

**❌ 禁止：** 直接开始配置、自己决定参数、想当然配了再说
**✅ 必须：** 把所有参数列清楚，等用户点头再动手

这个规则适用于任何提供商（千帆、DeepSeek、Kimi、小米、自建等），无论是新建还是修改现有配置。

## 配置步骤

### 1. 确定配置方式

Hermes 支持两种配置自定义提供商：

**方式A：通用 custom provider（推荐）**
- 适用：所有 OpenAI 兼容 API
- 配置：`model` 段落的 `provider: custom`
- 优点：简单直接

**方式B：命名 provider（高级）**
- 适用：需要多个同类提供商或特殊配置
- 配置：`providers` 段落定义
- 优点：可配置多个实例

### 2. 通用配置流程（方式A）

```bash
# 步骤1：写入 API Key 到 .env
echo "QIANFAN_API_KEY=your-key-here" >> ~/.hermes/.env

# 步骤2：配置模型
hermes config set model.provider "custom"
hermes config set model.base_url "https://qianfan.baidubce.com/v2/coding"
hermes config set model.default "qianfan-code-latest"
hermes config set model.api_key "your-key-here"

# 步骤3：测试
hermes chat -q "你好"
```

## 典型错误与排查

### 错误1：`api_key` vs `api_key_env` 混淆

**症状：** HTTP 401，Authorization 头显示 `Bearer no-key-required`

**原因：** 配置了 `api_key_env: QIANFAN_API_KEY`，但 `model` 段落不支持 `api_key_env`

**解决：** 使用 `api_key` 直接写入值，或迁移到 `providers` 段落定义命名 provider

```yaml
# ❌ 不支持（model 段落）
model:
  api_key_env: QIANFAN_API_KEY   # 无效！

# ✅ 支持方式（直接写值）
model:
  api_key: "actual-key-value"

# ✅ 或者用 providers 段落
providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY   # 这里支持
    provider: custom                # ← ⚠️ 必须加这个！缺了就 401
```

### ⚠️ 致命陷阱：命名 provider 缺 `provider: custom`

定义 `providers.xxx` 命名 provider 时，**必须加 `provider: custom`**，否则 Hermes 不会按 OpenAI 兼容协议调用：

```yaml
# ❌ 错误 — 缺了 provider: custom → 请求格式不对 → HTTP 401 invalid_iam_token
providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY
    base_url: https://qianfan.baidubce.com/v2/coding
    default_model: qianfan-code-latest
    models: '["qianfan-code-latest"]'

# ✅ 正确
providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY
    base_url: https://qianfan.baidubce.com/v2/coding
    default_model: qianfan-code-latest
    models: '["qianfan-code-latest"]'
    provider: custom   # ← 必须有！
```

**修改方法：** 用 `hermes config set` CLI，不要用 `patch` 工具（Hermes config.yaml 有安全保护，patch 工具会被拦截报 `Refusing to write to Hermes config file`）：

```bash
# ✅ 正确方式
hermes config set providers.qianfan.provider custom

# ❌ 错误方式 — 会被安全拦截
patch tool → /root/.hermes/config.yaml → providers.qianfan.provider
```

**症状：** HTTP 401 `invalid_iam_token` 或 `coding_plan_api_key_not_allowed`

**原因：** 端点路径不对，或模型不兼容该端点

**千帆正确配置：**
```yaml
# ❌ 错误
base_url: https://qianfan.baidubce.com/v2        # 不是 coding 专属端点
base_url: https://qianfan.baidubce.com/v2/coding/chat/completions  # 不需要带后缀

# ✅ 正确
base_url: https://qianfan.baidubce.com/v2/coding  # Coding 专属端点
```

⚠️ 重要：`/v2/coding` 是 Coding Plan 专属端点，**只支持 coding 类模型**：
- ✅ 支持的：`deepseek-v3`, `deepseek-r1`, `deepseek-v4-flash`, `deepseek-v4-pro`, `qianfan-code-latest`, `ernie-code`
- ❌ 不支持的：`glm-5.1`（智谱通用模型）、`qwen-turbo`（通义千问通用模型）

**排查方法：** 同一个 provider 下换一个 coding 模型试 → 换了就通说明是模型/端点不兼容，不是 Key 失效。
**口诀：** "glm 不走 coding 门，deepseek 才配 coding 端"

### 错误3：Key 格式不对

**症状：** HTTP 401 `invalid_iam_token`

**原因：** 使用了错误的 Key 格式

**千帆 Key 格式：**
```
bce-v3/ALTAKSP-xxx/xxx...
```

**检查方法：**
```bash
# 查 .env 中的 Key
python3 -c "
with open('/root/.hermes/.env') as f:
    for line in f:
        if line.startswith('QIANFAN_API_KEY='***            print(f'Key length: {len(line.split(\"=\", 1)[1].strip())}')
            print(f'Starts with: {line.split(\"=\", 1)[1].strip()[:20]}')
"
```

## 配置完整示例

### 千帆大模型平台

```yaml
# ~/.hermes/config.yaml
model:
  provider: custom
  base_url: https://qianfan.baidubce.com/v2/coding
  default: qianfan-code-latest
  api_key: bce-v3/ALTAKSP-xxx/xxx...  # 从 .env 读取后填入

# ~/.hermes/.env
QIANFAN_API_KEY=bce-v3/ALTAKSP-xxx/xxx...
```

**注意：**
- 千帆提供多种认证方式，上述是 **IAM Key** 方式
- 使用 `/v2/coding` 端点需要 **Coding Plan**
- 如果是普通 API Key，端点可能不同

## 验证测试

```bash
# 基础测试
hermes chat -q "你好"

# 查看请求转储（如果失败）
cat ~/.hermes/sessions/request_dump_*.json | grep -A5 '"url"\|"Authorization"'

# 检查配置
hermes config get model
```

## 常见提供商配置对照

| 提供商 | Base URL | Key 位置 | 特殊注意 |
|--------|----------|----------|----------|
| 千帆 Coding | `https://qianfan.baidubce.com/v2/coding` | .env QIANFAN_API_KEY | 需 Coding Plan |
| 千帆普通 | `https://qianfan.baidubce.com/v2` | .env QIANFAN_API_KEY | 用普通 API Key |
| DeepSeek | `https://api.deepseek.com/v1` | .env DEEPSEEK_API_KEY | 无特殊要求 |
| Kimi | `https://api.moonshot.cn/v1` | .env KIMI_API_KEY | 无特殊要求 |
| 自建 vLLM | `http://localhost:8000/v1` | 直接写入或 env | 需确保端口可访问 |

## 安全提示

- API Key 应保存在 `.env` 中，不要硬编码在 `config.yaml`
- 使用 `safe-api-key-write` 技能写入 Key
- 测试失败时查看 `request_dump_*.json` 确认请求内容
