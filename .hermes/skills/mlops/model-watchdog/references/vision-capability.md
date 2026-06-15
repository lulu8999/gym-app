# Vision 模型能力诊断参考

## 当前环境可用模型（2026-06）

| 模型 | 提供商 | 支持视觉 | 状态 |
|------|--------|---------|------|
| deepseek-v4-flash | DeepSeek | ❌ | ✅ API Key 有效 |
| deepseek-v4-pro | DeepSeek | ❌ | ✅ API Key 有效 |
| moonshot-v1-*-vision-preview | Kimi (Moonshot) | ✅ | ❌ API Key 过期 (401) |

## API Key 存放位置

| Key | 位置 | 说明 |
|-----|------|------|
| DEEPSEEK_API_KEY | Hermes 进程环境（/proc/<pid>/environ） | 当前对话可用的 key，仅 Hermes 进程持有 |
| DEEPSEEK_API_KEY | /root/.claude-code-litellm/.env | 同一服务商，两个文件可能用不同 key（一个过期另一个还活着） |
| KIMI_API_KEY | /root/.kimi_key | 视觉专用 key，当前已失效 |
| KIMI_API_KEY | 环境变量 | Hermes providers.kimi 配置了 `api_key_env: KIMI_API_KEY`，但 env var 也未设 |

## LiteLLM `supports_vision: true` 陷阱

LiteLLM `/root/.claude-code-litellm/config.yaml` 中 `claude-sonnet-4-20250514` 的 `model_info.supports_vision: true` 是**假阳性**：

```yaml
model_list:
  - model_name: claude-sonnet-4-20250514
    litellm_params:
      model: openai/deepseek-chat  # ← 实际是 DeepSeek Chat，不支持视觉
      api_base: https://api.deepseek.com/v1
    model_info:
      supports_vision: true        # ← 这是错误的
```

所以 LiteLLM 上的所有"claude"系列模型（claude-sonnet-4-8, claude-haiku-4-8 等）也都是 DeepSeek Chat 的别名，**都不支持视觉输入**。

向 LiteLLM 发 vision 请求会返回 400：
> "unknown variant \`image_url\`, expected \`text\`"

## Vision 故障排查流程

```
用户发图
  ↓
尝试 Hermes 内置 vision (auxiliary.vision provider=auto)
  ↓ 失败？
检查 Kimi API Key (/root/.kimi_key)
  ↓ 401 过期？
检查 DeepSeek 是否支持 vision（当前全系不支持）
  ↓
检查 LiteLLM Claude 别名（全是 DeepSeek，不支持）
  ↓
所有现有模型均无 vision 能力 → 需要新 Key 或新提供商
```

## 修复方案

### 方案 A：补 Kimi Key
从用户获取新 Key → 写入 `/root/.kimi_key`：
```python
with open('/root/.kimi_key', 'w') as f:
    f.write(new_key)
```

### 方案 B：换一家视觉提供商
串通：用户给一个真实支持视觉的 API Key（如 Google Gemini、OpenAI GPT-4o、真正的 Anthropic Claude），配到 Hermes config 中。

### 方案 C：DeepSeek 原生视觉（未来）
如果 DeepSeek 未来推出 vision 原生的模型，直接用 `DEEPSEEK_API_KEY` + `deepseek-chat` 即可，无需额外配置。

## 历史

- 2026-06-04: 发现在 Hermes 对话中用 Kimi 视觉失败，Key 401。全链路追查确认当前无可用 vision 模型。
- 2026-06-04: 确认 LiteLLM 的 `supports_vision: true` 是假阳性配置。
- 2026-06-04: 发现 Hermes 进程的 DEEPSEEK_API_KEY 与 `.claude-code-litellm/.env` 中的 Key **不是同一份**，后者已过期。
