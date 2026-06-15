# Codex + DeepSeek 接入方案

## 方案：Codex 走 LiteLLM 访问 DeepSeek

### 原理
```
Codex → Mac 本地 LiteLLM (localhost:41111) → DeepSeek API
```

LiteLLM 提供 OpenAI 兼容 API，Codex 无需修改代码，只需配置环境变量。

### 配置步骤

```bash
# Mac 上配置环境变量
export OPENAI_API_BASE=http://localhost:41111/v1
export OPENAI_API_KEY=你的-deepseek-api-key
```

### 优点
- 统一 API 管理（一个 DeepSeek 账号养所有 Agent）
- 无需额外购买 OpenAI 账号
- 可复用 VPS 上的 LiteLLM 配置

### 前提
- Mac 上 LiteLLM 必须正在运行
- LiteLLM 配置了 DeepSeek 作为上游 provider

### 状态
- Mac LiteLLM: ⏳ 待配置（用户自己配 API）
- VPS LiteLLM: ✅ 运行中
