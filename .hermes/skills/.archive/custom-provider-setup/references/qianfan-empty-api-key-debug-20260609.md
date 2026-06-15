# 千帆 401 排查实录 — `model.api_key: ''` 阻断 provider 级 key

## 问题现象

网关日志报 `invalid_iam_token`，但：
- curl 直测千帆 Coding Plan 端点 ✅ 成功（200）
- `.hermes/.env` 中 `QIANFAN_API_KEY` 存在且正确
- `providers.qianfan.api_key_env: QIANFAN_API_KEY` 正确配置

## 排查链路

### 第1步：检查 config.yaml 结构
```yaml
model:
  api_key: ''              # ← 空字符串！
  api_key_env: ''
  base_url: ''
  provider: qianfan

providers:
  qianfan:
    api_key_env: QIANFAN_API_KEY    # 配了
    base_url: https://qianfan.baidubce.com/v2/coding
    provider: custom
```

### 第2步：确认 API Key 有效性
- 系统 env：`${#QIANFAN_API_KEY}` = 77, 前缀 `bce-v3/ALT...`
- `.hermes/.env`：完全相同
- curl 直测：
  ```bash
  curl -s https://qianfan.baidubce.com/v2/coding/chat/completions \
    -H "Authorization: Bearer $QIANFAN_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"qianfan-code-latest","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
  ```
  返回 200 ✅

### 第3步：检查网关请求转储（找到根因）

```bash
ls -lt ~/.hermes/sessions/request_dump_*.json | head -3
```
读取最新 dump：
```python
import json
with open('/root/.hermes/sessions/request_dump_<timestamp>.json') as f:
    d = json.load(f)
print(d['request']['headers']['Authorization'][:50])
# → "Bearer no-key-required"  ← 问题在这里！
```

网关实际发的 Auth header 是 `Bearer no-key-required`，说明 `providers.qianfan.api_key_env` **没有被读取**，因为 `model.api_key: ''`（空字符串）抢了优先级。

### 第4步：修复

**方案 A**（推荐）：把 key 直接写到 model.api_key
```bash
hermes config set model.api_key "$QIANFAN_API_KEY"
```

**方案 B**：删除 model.api_key 空字符串行
```yaml
model:
  # api_key: ''   ← 删掉
```

### 第5步：验证

重启网关后重新创建会话，查 request dump 确认 Auth header 变为 `Bearer bce-v3/...`。

## 关键教训

`model.api_key` 即使为空字符串，优先级也高于 `providers.<name>.api_key_env`。永远不要留 `api_key: ''` 在 model 段——要么写实际 key，要么删掉整行让 provider 级配置接管。
