# 百度千帆 Coding Plan — Provider 配置参考

## 概述

千帆 Coding Plan 是百度千帆大模型平台专门为代码场景提供的 API 服务。使用的 Key 有特殊的 Coding Plan 标识，必须走专有端点。

## 配置方式

### 获取 Key

Key 格式：`bce-v3/ALTAK.../...`（百度 IAM 临时 token）

在百度智能云控制台 → 千帆大模型平台 → API Key 管理 中创建。

### Hermes 配置

```bash
# 设置 base_url（必须有 /coding 后缀）
hermes config set model.base_url "https://qianfan.baidubce.com/v2/coding"

# 设置默认模型
hermes config set model.default "qianfan-code-latest"

# 设置 provider
hermes config set model.provider "custom"

# 写入 API Key（⚠️ 必须为字面值，不支持 api_key_env）
python3 -c "
import os
key = os.environ.get('QIANFAN_API_KEY', '')
if key:
    from subprocess import run
    run(['hermes', 'config', 'set', 'model.api_key', key], check=True)
    print('Key set from QIANFAN_API_KEY env var')
else:
    print('QIANFAN_API_KEY not set in env')
"
```

### 最终 config.yaml 效果

```yaml
model:
  base_url: https://qianfan.baidubce.com/v2/coding
  default: qianfan-code-latest
  provider: custom
  api_key: bce-v3/ALTAK.../...               # 实际 Key 值
```

### .env 配置

```bash
# ~/.hermes/.env
QIANFAN_API_KEY=bce-v3/你的API Key
QIANFAN_BASE_URL=https://qianfan.baidubce.com/v2/coding
```

## 🕐 IAM Token 过期处理

**这是最常见的"突然不能用了"原因。** IAM token 有有效期（通常数天到数周），到期后必须**重新生成**而非续期。

### 症状

- 之前正常使用的 Key 突然报 `HTTP 401 invalid_iam_token`
- 未修改任何配置，curl 直测也返回 401

### 解决步骤

1. **生成新 Key**：去百度智能云控制台 → 千帆大模型平台 → API Key 管理，重新创建 IAM Token
2. **更新 `.env`**：
   ```bash
   sed -i 's|^QIANFAN_API_KEY=.*|QIANFAN_...y>|' ~/.hermes/.env
   ```
3. **验证新 Key**：
   ```bash
   source ~/.hermes/.env
   curl -s -X POST "https://qianfan.baidubce.com/v2/coding/chat/completions" \
     -H "Authorization: Bearer $QIANFAN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
   ```
4. **确认是否重启网关**：
   - 如果用的是 `providers.<name>` 段 + `api_key_env` → 只需更新 `.env`，重启网关后生效
   - 如果 `model.api_key` 写的是字面值 → 需要重新运行 Key 写入脚本（见上方"配置方式"）

### 排查技巧

> 分不清是 Key 过期还是模型不兼容？换一个 coding 模型测（如 `deepseek-v4-flash`）。
> - 通了 → Key 没问题，是原模型不兼容 coding 端点
> - 还是 401 → Key 过期了

---

## 与标准千帆的区别

| 对比项 | 标准千帆 | Coding Plan |
|--------|---------|-------------|
| base_url | `https://qianfan.baidubce.com/v2` | `https://qianfan.baidubce.com/v2/coding` |
| 可用模型 | `ernie-3.5-8k`, `ernie-4.0-8k` 等 | `qianfan-code-latest` |
| 认证 | 标准 IAM token | 需 Coding Plan 专属 Key |
| 适用场景 | 通用对话 | 代码生成与分析 |

## 测试

```bash
# 直接用 Hermes 测试
hermes chat -q "你好"

# 或者 curl 直接测
curl -X POST "https://qianfan.baidubce.com/v2/coding/chat/completions" \
  -H "Authorization: Bearer $QIANFAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qianfan-code-latest","messages":[{"role":"user","content":"你好"}]}'
```

## 坑 & 踩过的坑

1. **不要用 `api_key_env`** — `model` 段不支持这个字段，会变成 `Bearer no-key-required`
2. **`api_key` 必须写字面值** — 如果写 `QIANFAN_API_KEY`，会被当成字符串原文发送
3. **URL 必须带 `/coding`** — 用标准端点 `https://qianfan.baidubce.com/v2` 会报 `coding_plan_api_key_not_allowed`
4. **Key 写进 `.env` 也需要手动传给 model.api_key** — Hermes 的 `model` 段不会自动从 `.env` 读
5. **注意 `-Q` 和 redact** — `hermes chat -q "你好"` 出错时用 `-v` 或查看 request_dump 看真实请求头
