# LiteLLM Mac Mini 部署 — 排错参考

## 环境信息

- Mac Mini M4, macOS Sequoia
- Python 3.14 (brew default) + 3.12 (brew install python@3.12)
- LiteLLM v1.88.0, venv at `/Users/lulu/.litellm-venv312`
- VPS Tailscale IP: 100.80.33.29, mihomo proxy at :7890

## 排错历史

### 1. Python 3.14 + orjson 编译失败

**错误**：`Failed to build a native library through cargo` (orjson)

**根因**：PyO3（Rust 的 Python 绑定库）仅支持到 Python 3.13。3.14 的 C API 有 breaking changes。

**尝试过的无效方案**：
- `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` — Cargo 编译阶段仍报错
- `--only-binary :all:` — PyPI 没有 3.14 的预编译 wheel

**解决**：用 Python 3.12 创建独立 venv：
```bash
/opt/homebrew/bin/python3.12 -m venv /Users/lulu/.litellm-venv312
/Users/lulu/.litellm-venv312/bin/pip install litellm[proxy]
```

### 2. API Key 跨机器传输导致 401

**现象**：LiteLLM health check 返回 401 `Authentication Fails`，key 尾巴 `****3d23` 看起来正确。

**根因**：从 PM2 jlist 获取的 key hex 中，第 18 位从 `35`（数字5）变成了 `53`（大写S）。Key 显示时被 redact 截断，看不到差异。`sk-5b896...` vs `sk-5b896S...` — 只差一个字符。

**调试路径**：
1. VPS LiteLLM 正常 → Mac LiteLLM 401 → key 问题？
2. Mac .env 的 hex 和 VPS .env 的 hex **看起来一致**（70 chars）→ 但实际字节不同
3. 逐字符 `ord()` 对比发现 position 18 差异：`0x53` vs `0x35`
4. 重新从 PM2 用 `f'{ord(c):02x}' for c in key` 逐字符生成 hex，传输后成功

**教训**：跨机器传 key 时，`scp` 整个文件最安全。不要手工拼 hex 或用 `sed` 替换。

### 3. Mac 无法直连 DeepSeek API

**现象**：相同的 key，VPS 直接 curl 成功，Mac 直接 curl 返回 401。

**根因**：不是认证问题，是**网络问题**。Mac 在国内直连 DeepSeek API 时，请求可能被中间网络修改（header 被篡改、TLS 拦截等），导致 Bearer token 到达 DeepSeek 时已失效。

**验证**：
```bash
# Mac 直连 → 401
curl -s https://api.deepseek.com/v1/chat/completions -H "Authorization: Bearer sk-xxx" -d '...'
# Mac 通过 VPS 代理 → 200
curl -s --proxy http://100.80.33.29:7890 https://api.deepseek.com/v1/chat/completions -H "Authorization: Bearer sk-xxx" -d '...'
```

**解决**：launchd plist 中加入代理环境变量：
```xml
<key>HTTP_PROXY</key>
<string>http://100.80.33.29:7890</string>
<key>HTTPS_PROXY</key>
<string>http://100.80.33.29:7890</string>
```

### 4. plist 中 API Key 写入方法

**问题**：用 `sed` 替换 plist 中的占位 key 时，redact 层会把 `sk-xxx` 替换为 `***` 或截断值，导致写入错误。

**解决**：用 Python plistlib 从 .env 读取完整 key 后写入：
```python
import plistlib
plist_path = "/Users/lulu/Library/LaunchAgents/com.litellm.proxy.plist"
with open(plist_path, "rb") as f:
    plist = plistlib.load(f)
# Read key from .env (file on disk is correct, only display is masked)
with open("/Users/lulu/.claude-code-litellm/.env") as f:
    for line in f:
        if line.startswith("DEEPSEEK_API_KEY="):
            real_key = line.strip().split("=", 1)[1]
            break
plist["EnvironmentVariables"]["DEEPSEEK_API_KEY"] = real_key
with open(plist_path, "wb") as f:
    plistlib.dump(plist, f)
```

## 最终验证命令

```bash
# 服务状态
launchctl list | grep litellm

# 健康检查
curl -s http://localhost:41111/health

# 日志查看
tail -20 /Users/lulu/Library/Logs/litellm.log
tail -5 /Users/lulu/Library/Logs/litellm.err

# 实际 API 测试
curl -s http://localhost:41111/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```
