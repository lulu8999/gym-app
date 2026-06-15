# MiMo (小米) Provider 配置参考

## 基本信息

| 参数 | 值 |
|------|-----|
| 官网 | https://platform.xiaomimimo.com |
| API Base | `https://api.xiaomimimo.com/v1` |
| Provider 类型 | `openai`（OpenAI 兼容） |
| Key 格式 | `sk-xxx`（51字符） |

## 可用模型（2026-06-15 实测）

| 模型名 | 状态 | 用途 |
|--------|------|------|
| `mimo-v2-flash` | ✅ 正常 | 轻量快速 |
| `mimo-v2-pro` | ✅ 正常（未实测） | 标准版 |
| `mimo-v2.5` | ✅ 正常 | 新版标准（含视觉） |
| `mimo-v2.5-pro` | ❌ 502/超时 | 新版增强 — **MiMo 后端自身不稳定** |
| `mimo-v2.5-pro-ultraspeed` | ✅ 正常 | **ultra 版，响应更快** — `mimo-v2.5-pro` 的推荐替代 |
| `mimo-v2.5-asr` | — | 语音识别（需特定格式消息） |
| `mimo-v2.5-tts` | — | 语音合成 |
| `mimo-v2.5-tts-voiceclone` | — | 语音克隆 |
| `mimo-v2.5-tts-voicedesign` | — | 语音设计 |

> 📝 2026-06-15 实测：`mimo-v2.5-pro-ultraspeed` 是 `mimo-v2.5-pro` 的稳定替代品，响应速度更快。建议设为默认模型。

## 视觉能力

MiMo v2.5 及以上自带视觉能力，可用作 `auxiliary.vision`。

配置示例（直接写 key，不用 env 间接引用）：
```yaml
auxiliary:
  vision:
    provider: openai
    model: mimo-v2.5
    base_url: https://api.xiaomimimo.com/v1
    api_key: sk-实际Key
    timeout: 120
    download_timeout: 30
```

> ⚠️ 注意：配置 `auxiliary.vision` 时不要同时写 `api_key` 和 `api_key_env`，只用 `api_key` 直接写。

## 常见问题

### 401 / Provider unknown 错误
- **首要检查**：确认 `api_key` **直接写**在 config.yaml 的 `api_key` 字段中，**不是**通过 `api_key_env` 引用 `.env` 文件。Gateway 进程**不会自动加载** `.env`，即使 `.env` 文件存在且 Key 正确，`api_key_env` 引用的环境变量仍是空的。
- 检查 `provider` 字段是否为 `openai`（不是 `custom`）
- 确认 Key 是否已过期（MiMo Key 有时效）

### 502 Bad Gateway 诊断 ⭐

**症状**：使用 `mimo-v2.5-pro` 时返回 502，切换报错。

**根因**：**MiMo 的 OpenResty 网关**返回的 502，非我们这边的问题。
```
<html>
<head><title>502 Bad Gateway</title></head>
<hr><center>openresty</center>  ← 小米自己的 API 网关
</html>
```
`mimo-v2.5-pro` 模型后端高负载时，小米自己的反向代理扛不住就直接甩 502。

**诊断步骤**：

1. **测试单个模型** — 别假定所有模型都坏：
   ```bash
   python3 -c "
   import urllib.request, json
   proxy_handler = urllib.request.ProxyHandler({})  # 不走代理
   opener = urllib.request.build_opener(proxy_handler)
   
   for model in ['mimo-v2.5-pro', 'mimo-v2.5-pro-ultraspeed', 'mimo-v2.5', 'mimo-v2-flash']:
       req = urllib.request.Request(
           'https://api.xiaomimimo.com/v1/chat/completions',
           data=json.dumps({'model': model, 'messages': [{'role': 'user', 'content': 'hi'}], 'max_tokens': 3}).encode(),
           headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
       )
       try:
           resp = opener.open(req, timeout=15)
           print(f'OK  {model}')
       except urllib.error.HTTPError as e:
           body = e.read().decode()[:200]
           print(f'ERR {model} - {e.code}')
           if 'openresty' in body: print('     → MiMo 自身网关问题')
       except Exception as e:
           print(f'TIM {model} - timeout')
   "
   ```

2. **直连绕过代理** — MiMo 是国内 API，**不需要走 mihomo 代理**：
   ```python
   # 必须用 ProxyHandler({}) 绕开系统代理
   proxy_handler = urllib.request.ProxyHandler({})
   opener = urllib.request.build_opener(proxy_handler)
   # 或 curl 用 --noproxy "*"
   ```

3. **排查结果示例**（2026-06-15 实测）：
   - ✅ `mimo-v2.5-pro-ultraspeed` — 200, 0.5s（可替代）
   - ✅ `mimo-v2.5` — 200（标准版可用）
   - ✅ `mimo-v2-flash` — 200, 0.5s（轻量版）
   - ❌ `mimo-v2.5-pro` — 超时/502（MiMo 后端问题）

**解决方案**：切到 `mimo-v2.5-pro-ultraspeed`（`hermes config set model.default mimo-v2.5-pro-ultraspeed`），无需等 MiMo 修。

### MiMo API 直连注意事项

- **必须绕代理**：VPS 上全局走了 mihomo 代理（`HTTPS_PROXY=http://127.0.0.1:7890`），但 MiMo 国内 API 不需要代理。测试时必须显式绕过。
- **模型列表接口** `GET /v1/models` 响应快且几乎不失败
- **Chat 接口** `POST /v1/chat/completions` 对 `mimo-v2.5-pro` 不稳定
- **Key 在 `.env` 中**：变量名 `XIAOMI_API_KEY`，用 `xxd /root/.hermes/.env | grep XIAOMI` 可提取完整值

### 不支持某些模型
- 确认模型名是否在新旧版本之间被重命名
- 旧版 `mimo-v2` 系列和新版 `mimo-v2.5` 系列是不同的模型集

## 模型切换流程（快速版）

```bash
# 改默认模型
hermes config set model.default mimo-v2.5-pro-ultraspeed

# 重启网关（⚠️ 从网关会话内不能重启，需在新会话/外部终端执行）
hermes gateway restart
```

> ⚠️ `hermes gateway restart` **从网关内部的会话里无法执行**（防死循环机制）。  
> 只能在新会话中执行，或从外部终端执行。改完 model.default 后告知用户开新会话/手动重启即可生效。
