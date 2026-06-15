# 百度千帆 Coding Plan 401 诊断记录 (2026-06-09)

## 场景
切换模型到 qianfan (glm-5.1) 时报 401 `invalid_iam_token`。

## 诊断过程

### 1. 端点测试

```bash
# 测试通用端点 → 报错：coding_plan_api_key_not_allowed
# 说明 Key 是 Coding Plan 专用，必须用 /v2/coding 端点
curl https://qianfan.baidubce.com/v2/chat/completions ...
# → {"error":{"code":"coding_plan_api_key_not_allowed",...}}

# 测试正确端点但旧 Key → 401 invalid_iam_token
curl https://qianfan.baidubce.com/v2/coding/chat/completions ...
# → {"error":{"code":"invalid_iam_token",...}}
# Key 已过期（IAM 临时令牌有有效期）
```

### 2. 根因

**两个问题叠加：**

a) **API Key 过期** — `bce-v3/...` 格式是 IAM 临时令牌，需要去百度控制台重新生成

b) **`providers.qianfan` 块缺 `provider: custom`** — Hermes 在 `providers` 段的子块内必须显式声明 `provider: custom`，否则不会用 OpenAI 兼容格式调接口。配置：

```yaml
providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY
    base_url: https://qianfan.baidubce.com/v2/coding
    default_model: qianfan-code-latest
    models: '["qianfan-code-latest"]'
    provider: custom    # ← 缺了这个
```

### 3. 修复

1. 用户提供新 Key → 更新 `.env` 中 `QIANFAN_API_KEY`
2. 补上 `provider: custom` 到 `config.yaml` 的 `providers.qianfan` 块
3. 重启网关
