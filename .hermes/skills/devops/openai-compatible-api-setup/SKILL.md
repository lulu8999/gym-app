---
name: openai-compatible-api-setup
description: "标准流程：配置 OpenAI 兼容的 LLM API + 微信配置失败诊断。统一用 provider: openai，直接写 api_key，清残留旧 key。"
version: 1.1.0
author: Lulu's AI assistant
tags: [hermes, config, llm-provider, api-setup, openai-compatible, qianfan]
related_skills: [safe-api-key-write, hermes-agent]
---

# OpenAI 兼容 API 配置标准流程

## 📊 配置展示格式（重要！）

用户想看 **按 `/model` 命令能看到的格式** 来展示配置，不是按 `.env` 变量名分类。

### `/model` 能看到什么？

| 命令 | 配置来源 | 状态 |
|------|---------|------|
| `/model qianfan-code-latest` | model 段 | 当前主模型 |
| `/model qianfan` | providers.qianfan | fallback |
| `/model kimi` | providers.kimi | 待确认 |
| `/model xiaomi-mimo` | providers.xiaomi-mimo | 视觉辅助 |
| deepseek-v4-flash | ⚠️ 特殊情况 | 通过 `--global` 切换时临时写入 model 段 |

### ⚠️ DeepSeek 的特殊性

DeepSeek 不是通过 `providers` 段配置的，而是：
- **委派任务用**：`delegation.model: deepseek-v4-pro`（子代理专用）
- **全局切换用**：通过 `--global` 参数把 DeepSeek 写入 `model` 段，临时替换主模型

### 展示模板

```markdown
| 命令 | 位置 | 状态 |
|------|------|------|
| `/model qianfan` | model 段 | ✓ 在用 |
| `/model kimi` | providers | 待确认 |
| `/model xiaomi-mimo` | providers | ✓ 视觉辅助 |
```

---

## 🎯 核心原则（必须遵守）

### 核心原则（2026-06-13 更新）

**所有 OpenAI 兼容 API 统一用 `provider: openai`，禁止用 `provider: custom`。**

| Provider 类型 | 是否可用 | 说明 |
|---|---|---|
| `openai` | ✅ 唯一正确值 | 所有 OpenAI 兼容 API（千帆、DeepSeek、MiMo、中转站等） |
| `custom` | ❌ 已被 Gateway 静默忽略 | 日志显示 `unknown config keys ignored: provider` → 配置失效 |

**配置位置：`providers` 段和 `model` 段都可以。**

> ⚠️ **`provider: custom` 为什么不行？** Hermes Gateway 不认识 `providers.<name>` 段下的 `provider: custom`，会静默忽略 → provider 配置失效 → 回退到 `.env` 旧 Key → 401。把值改成 `openai` 即可。
>
> ⚠️ **`api_key_env` 为什么不行？** Gateway 进程不自动加载 `.env` 到环境变量，即使 `.env` 有正确的 key 也拿不到 → `/model` 显示 `unknown provider`。直接用 `api_key` 字段写入完整 key 值。
>
> ⚠️ **`model` 段 vs `providers` 段**：之前的版本建议全写 `model` 段，实测 `providers` 段 + `provider: openai` 也完全可用（千帆、MiMo、DeepSeek 均测试通过）。选哪个取决于使用场景：
>   - 只有 1 个主模型 → 用 `model` 段简单直接
>   - 多个模型共存、后台切换 → 用 `providers` 段（支持 `/model` 切换）
>
> **关键：确保 api_key 完整写入，且 provider 值不是 `custom`。**

**配置规则速查：**
- ✅ `provider: openai` — 所有 OpenAI 兼容 API 的标准值
- ✅ `api_key: 完整key` — 直接写值，不用 `api_key_env`
- ❌ `provider: custom` — 禁止使用，Gateway 不认识
- ❌ `api_key_env` / `key_env` — 禁止使用，Gateway 不加载 `.env`

1. **配完必须验证** — curl 直测 API

---

## 📋 标准配置步骤

### 第1步：确认参数清单（给用户确认）

```
需要配置的参数：
├─ model:       xxx（如 qianfan-code-latest）
├─ base_url:    https://xxx（完整 endpoint）
├─ provider:    custom（所有 OpenAI 兼容 API 都是这个）
├─ api_key:     sk-... 或 bce-v3/...（实际 key 值，不是 env 变量名）
└─ 重启网关:    需要/不需要
```

**⚠️ 必须拿到用户明确答复后才能执行**

---

### 第2步：备份当前配置

```bash
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.backup.$(date +%Y%m%d_%H%M%S)
```

---

### 第3步：写入配置（Python 方式，不用 sed）

**方式 A：写入 providers 段（多模型共存时推荐）**

```python
import yaml

config_path = '/root/.hermes/config.yaml'

with open(config_path) as f:
    config = yaml.safe_load(f)

# 确保 providers 段存在
if 'providers' not in config:
    config['providers'] = {}

# 添加新 provider（⚠️ provider 值必须用 openai，不是 custom）
config['providers']['my-provider'] = {
    'provider': 'openai',
    'base_url': 'https://完整的endpoint.com/v1',
    'default_model': '模型名',
    'models': '["模型1","模型2"]',
    'api_key': 'sk-你的实际完整key'  # 直接写值，不用 api_key_env
}

with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("✓ 配置写入完成")
```

**方式 B：写入 model 段（单一主模型时快刀斩乱麻）**

```python
import yaml

config_path = '/root/.hermes/config.yaml'

with open(config_path) as f:
    config = yaml.safe_load(f)

config['model']['default'] = '你的模型名'
config['model']['provider'] = 'openai'  # ⚠️ 必须 openai，不是 custom
config['model']['base_url'] = 'https://完整的endpoint.com/v1'
config['model']['api_key'] = 'sk-你的实际完整key'

with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("✓ 配置写入完成")
```

**写入后必须验证 Key 完整性：**

```bash
grep "api_key:" ~/.hermes/config.yaml | grep -v "^#"
# 确认 key 长度合理（不是截断的 ... 值）
python3 -c "
import re
with open('/root/.hermes/config.yaml') as f:
    content = f.read()
for m in re.finditer(r'api_key:\s*(\S+)', content):
    key = m.group(1)
    if '...' in key or len(key) < 20:
        print(f'❌ 截断 key: {key[:15]}... (len={len(key)})')
    else:
        print(f'✅ OK: {key[:15]}... (len={len(key)})')
"
```

---

### 第4步：重启网关

```bash
hermes gateway restart
```

---

### 第5步：验证请求（关键！）

发个测试消息，然后检查请求转储：

```python
import json
import glob

# 找最新的请求转储
dump_files = glob.glob('/root/.hermes/sessions/request_dump_*.json')
latest = max(dump_files, key=lambda x: x.split('_')[-1])

with open(latest) as f:
    d = json.load(f)

print('URL:', d['request']['url'])
print('Auth Header 前缀:', d['request']['headers']['Authorization'][:50])
```

**验证标准：**
- ✅ Auth Header 是 `Bearer sk-...` 或 `Bearer bce-v3/...` — Key 读取成功
- ❌ Auth Header 是 `Bearer no-key-required` — Key 没读到，需要检查

---

## 🔴 常见错误对照表

| 错误现象 | 原因 | 解决方案 |
|---------|------|---------|
| `no-key-required` | `model.api_key` 为空 | 把 key 直接写入 `model.api_key` |
| 404 / 空响应 | `base_url` 错误 | 确认 endpoint 是完整 URL（含 `/v1` 或 `/v2`） |
| `invalid_iam_token` | Coding Plan Key 用错了 endpoint | 确认 base_url 是 `.../v2/coding` |
| `coding_plan_api_key_not_allowed` | Key 类型不匹配 | 千帆 Coding Plan Key 只能用于 `/v2/coding` 端点 |
| 网关没生效 | 没重启 | 每次改 config 必须 `hermes gateway restart` |
| GPT 报 401 | 大概率 `model.api_key` 没写对 | 按标准流程，全部写死到 model 段 |
| `unknown config keys ignored: provider` | `provider` 字段（任何值）写在 providers 段 | **删除 providers 段的 `provider` 字段**，只在 `model` 段使用 |
| 401 `invalid_iam_token`（重启后） | Gateway 忽略 providers 段配置，回退到 `.env` 旧 Key | 确认 config.yaml 中无 `provider: custom` 在 providers 段 |
| `api_key` 写入后仍 401 | 写入了截断值（字面 `...` 在 key 中间） | 用 Python 逐字符提取完整 key 并验证长度后重新写入 |
| `/model` 显示 `unknown provider` | `api_key_env` 未被 Gateway 加载 | 改用直接 `api_key`（删除 `api_key_env` 和 `key_env`） |
| `unknown config keys ignored: provider` | `provider: custom` 在 providers 段 | 改为 `provider: openai` |
| 国内 API（MiMo/DeepSeek）超时/异常 | 环境代理 `HTTPS_PROXY` 设置了 mihomo/clash | 为 Provider 配置 `noxxx` 或请求时加 `--noproxy "*"` |

### 🔴 Key 截断陷阱（2026-06-13 新增，极其重要）

**现象**：config.yaml 中的 api_key 显示为 `sk-cpy...lfby`（13位）或 `sk-ffe...05ad`（13位），看起来像正常的 key，但实际是被截断的值。

**根因**：之前的会话中，终端 `grep` 或 `echo` 显示 key 时被 Hermes 工具掩码截断为 `sk-xxx...yyy` 格式，然后这个截断值被直接写入了 config.yaml。字面的 `...` 是三个点号字符，不是省略号。

**危害**：
- API 返回 401（Invalid API Key）
- 但肉眼看配置文件时，key 看起来"正常"（有前缀有后缀），很难发现问题

**诊断**：
```python
# 逐字符检查 key 是否包含字面 ...
import re
with open('/root/.hermes/config.yaml') as f:
    content = f.read()
for m in re.finditer(r'api_key:\s*(\S+)', content):
    key = m.group(1)
    if '...' in key or len(key) < 20:
        print(f'❌ Truncated key: {key} (len={len(key)})')
    else:
        print(f'✅ OK: {key[:15]}... (len={len(key)})')
```

**修复**：用 Python 从 `.env` 提取完整 key（逐字符，不用 grep）：
```python
with open('/root/.hermes/.env') as f:
    for line in f:
        line = line.strip()
        if 'API_KEY' in line and not line.startswith('#'):
            key = line.split('=', 1)[1]
            print(f'Full key: {key[:15]}... (len={len(key)})')
            break
```

---

## 📦 常用 API 参数速查

### 百度千帆 Coding Plan
```yaml
model: qianfan-code-latest
provider: openai
base_url: https://qianfan.baidubce.com/v2/coding
api_key: bce-v3/ALTAKSP-...
```

### 任意 OpenAI 兼容 API（中转站等）
```yaml
model: gpt-4o
provider: openai
base_url: https://中转站地址.com/v1
api_key: sk-...
```

---

## ⚠️ Proxy 干扰排查（国内 API 配置必读）

当 VPS 上配置了全局代理（mihomo/clash 等），**国内 API 会被迫走代理**，导致超时或异常。

### 现象

- MiMo API 请求超时（>30s）或返回 502 Bad Gateway
- DeepSeek（国内节点）响应异常
- API 直连正常但走代理就出问题

### 诊断

```bash
# 查看当前代理环境变量
env | grep -i proxy

# 常见输出：
# HTTPS_PROXY=http://127.0.0.1:7890
# HTTP_PROXY=http://127.0.0.1:7890
```

### 绕过的两种方式

**方式 A：curl 直测时绕过**
```bash
curl -s --noproxy "*" https://api.xiaomimimo.com/v1/models \
  -H "Authorization: Bearer $(grep XIAOMI_API_KEY ~/.hermes/.env | cut -d= -f2)"
```

**方式 B：在 .bashrc 设置 no_proxy（推荐）**
```bash
export no_proxy="localhost,127.0.0.1,api.xiaomimimo.com,api.deepseek.com"
export NO_PROXY="$no_proxy"
```

### 关键原则

- **国内 API 直连最佳**：MiMo、DeepSeek 不需要翻墙
- **mihomo 只要用于外网访问**：Jina Reader、GitHub API 等
- **不要全局无差别代理**：`HTTPS_PROXY` 会覆盖所有出站流量

### 配置后验证

```bash
# 不走代理测试国内 API
curl -s --noproxy "*" --connect-timeout 5 --max-time 10 \
  -H "Authorization: Bearer <您的key>" \
  https://api.xiaomimimo.com/v1/models

# 走代理测试外网 API
curl -s --connect-timeout 5 \
  https://api.github.com/zen
```

- ❌ **不要在 `model` 段或 `providers` 段用 `api_key_env` 或 `key_env`** — Gateway 不加载 `.env` 到进程环境，间接引用无效
- ❌ **不要在 `providers.<name>` 段写 `provider: custom`** — Gateway 不认识此值，会静默忽略（日志 `unknown config keys ignored: provider`），导致配置失效 → 回退到 `.env` 旧 Key → 401
- ❌ **不要用 sed 编辑 YAML** — 会搞乱缩进格式
- ❌ **不要直接复制终端显示的 key** — 终端输出可能被截断为 `sk-xxx...yyy`（字面 `...`），写进去就废了
- ❌ **不要假设 `.env` 的 Key 自动生效** — Gateway 进程不会自动读取 `.env`，必须写入 config.yaml

---

## ✅ 历史教训总结

**千帆 401 原因：**
- `model.api_key = ''` 为空，但 `providers.qianfan.api_key_env` 没被网关正确读取
- 结果实际请求发的是 `Bearer no-key-required` → 401

**MiMo provider unknown 原因（2026-06-13）：**
- `providers.xiaomi-mimo` 用了 `api_key_env: XIAOMI_API_KEY` + `key_env: XIAOMI_API_KEY`
- Gateway 不加载 `.env` 到进程环境 → provider 初始化失败 → unknown provider
- 修复：删除 `api_key_env`/`key_env`，直接写 `api_key` 值到 config.yaml

**DeepSeek 429 / 401 根因（2026-06-13）：**
- `providers.deepseek` 的 api_key 是字面 `sk-ffe...05ad`（13位截断值）
- 和 MiMo 一模一样的 bug：终端 grep 显示被截断，然后截断值被写入 config.yaml
- 同时 `provider: custom` 被 Gateway 忽略 → provider 配置完全失效
- 修复：改为 `provider: openai` + 从 .env 提取完整 key（35位）写入

**Key 截断显示陷阱（2026-06-13）：**
- 终端 `grep` 或 `echo` 显示 key 可能截断为 `sk-cpy...lfby`（字面 `...`），实际值 51 位
- 用 `write_file` 写入时会把截断值写进去 → API 返回 401
- 必须用 Python 逐字符提取完整 key 并验证长度后再写入

**解决方案：**
- 弃用 `providers` 段间接配置
- 全部参数写死到 `model` 段：key、url、provider 一个不落
- 配完看请求转储验证

---

## 🧹 清理无效 API 的标准流程

当需要清理不再使用的 API 时：

### 第1步：检查当前配置

```bash
# 查看 providers 段
grep -A 10 "^providers:" ~/.hermes/config.yaml

# 查看 fallback_providers
grep "fallback_providers" ~/.hermes/config.yaml
```

### 第2步：删除 providers 中的无效配置

```python
import yaml
with open('/root/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)

# 删除无效的 provider（如 kimi）
if 'kimi' in cfg.get('providers', {}):
    del cfg['providers']['kimi']

with open('/root/.hermes/config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
```

### 第3步：同步清理 fallback_providers

如果 `fallback_providers` 里引用了已删除的 provider，需要同步更新：

```python
import yaml
import json

with open('/root/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)

# 解析并清理 fallback_providers
fallback = json.loads(cfg.get('fallback_providers', '[]'))
fallback = [x for x in fallback if 'kimi' not in x.lower()]  # 删除含 kimi 的项
cfg['fallback_providers'] = json.dumps(fallback)

with open('/root/.hermes/config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
```

### 第4步：清理 .env 中的无效 Key

```bash
# 先确认哪些 Key 还在用
grep -E "^[A-Z_]+=" ~/.hermes/.env | grep -v "^#"

# 删除无效 Key（如 KIMI_API_KEY、CODEX_API_KEY 等）
sed -i '/^KIMI_API_KEY/d; /^KIMI_BASE_URL/d; /^CODEX_API_KEY/d; /^DEEPSEEK_API_KEY/d' ~/.hermes/.env
```

### 第5步：重启网关

```bash
hermes gateway restart
```

---

## 📕 参考文件

- 📕 `references/wechat-api-failure-diagnosis.md` — 微信配置 API 失败诊断指南（三个根因 + 排查流程）

--- 

**总结：清理 API 需要同步做三件事**
1. 删除 `providers.xxx` 配置
2. 清理 `fallback_providers` 里的引用
3. 删除 `.env` 里对应的 Key

**以后所有 API 配置，一律按此标准流程执行。**

---

## 🔴 铁律 v3：API 配置逐步验证流程（Lulu 强制要求）

用户要求配置 API 时，必须按以下步骤逐步执行，禁止跳步：

```
① 搜 config.yaml 全文件确认无残留旧 key / 重复配置
   （model: 段 + providers: 段可能有同名配置）
② 列完整参数（provider / model / api_key / base_url）→ Lulu 确认
③ 直接写入 config.yaml，不用 api_key_env 间接引用
④ 写入后 grep 确认仅一处配置 + 无残留旧 key → curl 测试 API
⑤ 都通过后再问 Lulu 是否重启
```

**关键补充（2026-06-13 新增）：**
- **Key 截断陷阱**：终端输出显示的 key 可能被截断为 `sk-cpy...lfby`（字面 `...` 三个点号），写入 config 后 API 返回 401。必须用 Python 逐字符提取完整 key 并验证长度。
- `provider: custom` 已确认不可用 → 统一用 `provider: openai`
- `api_key_env` / `key_env` 全部不可靠 → 统一用直接 `api_key` 值
- 可以在 `providers` 段配置，不强制写入 `model` 段
