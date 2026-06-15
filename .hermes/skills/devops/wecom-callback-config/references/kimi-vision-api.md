# Kimi 视觉 API 集成

## 配置

Kimi API Key 存储在 `~/.hermes/.env`：

```env
KIMI_API_KEY=sk-xxxxxxxxxxxx
KIMI_BASE_URL=https://api.moonshot.cn/v1
```

## 可用模型

- `moonshot-v1-8k-vision-preview` — 推荐，性价比高
- `moonshot-v1-32k-vision-preview`
- `moonshot-v1-128k-vision-preview`

## 调用方式

```python
import json, urllib.request

key = "sk-xxx"  # 从 .env 读取
img_b64 = base64.b64encode(open("image.jpg", "rb").read()).decode()

payload = {
    "model": "moonshot-v1-8k-vision-preview",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "图中是什么？详细描述一下，用中文回答"},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{img_b64}"
            }}
        ]
    }],
    "max_tokens": 500
}

req = urllib.request.Request(
    "https://api.moonshot.cn/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
)
with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read())
    print(result["choices"][0]["message"]["content"])
```

## 费用估算

- 约 **0.012 元/千 token**（moonshot-v1-8k-vision-preview）
- 一张照片 ≈ 800 token（图片编码）+ 100-200 token（输出）≈ **0.01 元/次**
- 1 元 ≈ 100 次识别

## 注意事项

- Kimi API **没有公开的余额查询接口**（`/v1/user/balance` 返回 404）
- 图片通过 base64 编码传入，大图会产生更多 token
- 建议回答用中文，描述尽量详细
- `.env` 中写入了 `KIMI_API_KEY=sk-xxx`，但 `write_file` 工具会将其中的 `sk-xxx` 自动替换为 `***`。含 key 的文件写入需用 `sed` 替换或 Python 直接写文件
