# 三阶段 API 配置清理模式（2026-06-13）

## 适用场景

多个 API 配置需要系统化检查和修复时。按固定顺序逐步清理，避免漏修或修出新的问题。

## 固定顺序

```
阶段1: API Key 完整性  →  阶段2: Provider 字段  →  阶段3: .env 瘦身
```

**为什么是这个顺序**：Key 不修废了全部 provider；provider 字段不修正 Key 对也没用；最后再收尾清理. env。

---

## 阶段1：检查所有 API Key 是否被截断

### 典型症状
- Provider 配置正常但 API 调用 401
- 终端显示的 key 被自动截断（如 `sk-cpy...lfby`），直接复制写入就是废 key
- `.env` 中有完整 key，config.yaml 中写的是截断版

### 检查方法

```python
# 对每个 provider 检查 key 长度
with open('/root/.hermes/config.yaml') as f:
    content = f.read()
import re
for m in re.finditer(r'(\w[\w-]+):\n(  .+\n)+', content):
    block = m.group(0)
    name = block.split(':')[0].strip()
    for line in block.split('\n'):
        if 'api_key:' in line and 'api_key_env' not in line:
            key = line.split(': ', 1)[1].strip()
            status = '✅' if len(key) > 20 else '❌'
            print(f'{status} {name}: key_len={len(key)}')
```

### 修复方法

Key 被截断的特征：长度远小于预期（如 13 位的 `sk-cpy...lfby` 实际应为 51 位）。

从 `.env` 读取完整 Key 并更新 config.yaml：
```python
# 从 .env 拿完整 key
key = None
with open('/root/.hermes/.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('XIAOMI_API_KEY=***            key = line.split('=', 1)[1]
            break

# 更新 config.yaml
with open('/root/.hermes/config.yaml') as f:
    content = f.read()
content = content.replace('sk-cpy...lfby', key)
with open('/root/.hermes/config.yaml', 'w') as f:
    f.write(content)
```

**⚠️ 关键陷阱**：不要从终端回显复制 key，终端会自动截断显示为 `sk-xxx...yyy`（字面 `...`）。必须从 `.env` 原文或 Python 逐字符提取。

---

## 阶段2：检查 Provider 字段

### 典型症状
- Gateway 日志报 `unknown config keys ignored: provider`
- Provider 配置看起来完整但不生效

### 检查方法

```bash
grep "    provider:" /root/.hermes/config.yaml
```

### 修复标准

| provider 值 | 状态 | 说明 |
|-------------|------|------|
| `openai` | ✅ 正确 | 所有 OpenAI 兼容 API 统一用 |
| `custom` | ❌ 已废弃 | Gateway 不认识，静默忽略 |
| `anthropic` | ✅ 正确 | Anthropic 原生 API |

**2026-06-13 实测验证**：千帆和 DeepSeek 从 `provider: custom` 改为 `provider: openai` 后，API 200 通过，Gateway 0 警告。

### API 测试

改完每个 provider 后必须 curl 验证：
```bash
KEY="<从 config.yaml 读到的 key>"
BASE="<base_url>"
MODEL="<default_model>"

curl -s "$BASE/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $KEY" \
  -d '{"model":"'$MODEL'","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
```

---

## 阶段3：清理 .env 注释和空行

### 典型症状
- `.env` 文件超 400 行，90% 是注释和空行
- 实际需要的活跃变量只占 5-10%

### 清理方法

```python
import shutil, datetime

# 备份
backup = f'/root/.hermes/.env.backup.{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
shutil.copy('/root/.hermes/.env', backup)

# 清理（保留活跃变量，删除注释和空行）
with open('/root/.hermes/.env') as f:
    lines = f.readlines()

active = []
for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith('#'):
        active.append(line)

with open('/root/.hermes/.env', 'w') as f:
    f.writelines(active)

print(f'Cleaned: {len(lines)} → {len(active)} lines')
print(f'Backup: {backup}')
```

### 注意
- **不要删除 active 变量** — 只删注释和空行
- **备份一定要留** — 出错了可以恢复
- **config.yaml 中的 Key 独立于 .env** — 清理 .env 不影响已写死在 config.yaml 中的 Key
- **⚠️ 不要删 .env 中的 DEEPSEEK_API_KEY** — 虽然 config.yaml 已有 key，但 delegation/tts/stt 可能读 .env

---

## 清理后验证检查清单

- [ ] 所有 provider API 都 200 ✅
- [ ] 无 `unknown config keys ignored` 警告
- [ ] `.env` 备份存在
- [ ] config.yaml key 长度正常（>20 字符）
- [ ] `provider: custom` 已全部替换为 `provider: openai`
