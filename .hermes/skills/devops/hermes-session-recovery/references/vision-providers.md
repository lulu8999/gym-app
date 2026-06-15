# Vision/图像识别提供商可用状态

当前可用提供商（2026-06-04 确认）：

## DeepSeek V4
- 模型: `deepseek-v4-flash`, `deepseek-v4-pro`
- 支持: ❌ 不支持 image_url/image content type
- 返回: 400 — "unknown variant `image_url`, expected `text`"

## Kimi (Moonshot)
- 模型: `moonshot-v1-8k-vision-preview`
- Key 位置: `~/.kimi_key`
- 支持: ✅ 理论上支持视觉
- 状态: ⚠️ Key 已过期 (401 Incorrect API key)
- 恢复方式: 用户提供新的 Kimi API Key → 写入 `~/.kimi_key`

## 备选方案 (未配置)
如需视觉能力，需用户提供以下任一 API Key:
- Claude Sonnet 4 (Anthropic) — 原生支持视觉
- GPT-4o (OpenAI) — 原生支持视觉
- Gemini (Google) — 原生支持视觉

## 使用方式
Kimi 视觉的调用方式（当 Key 有效时）:
```python
from openai import OpenAI
client = OpenAI(api_key=key, base_url='https://api.moonshot.cn/v1')
resp = client.chat.completions.create(
    model='moonshot-v1-8k-vision-preview',
    messages=[{'role':'user','content':[
        {'type':'text','text':'描述图片'},
        {'type':'image_url','image_url':{'url':f'data:image/jpeg;base64,{b64}'}}
    ]}]
)
```

LiteLLM 代理 (`localhost:41111`) 上的 "claude" 系列模型全部映射到 DeepSeek Chat（不支持视觉），不可用于看图。
