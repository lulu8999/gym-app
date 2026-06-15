---
name: api-latency-diagnostic
description: "诊断 API 响应慢的原因：上下文过长、API 抖动、网络问题。自动检测并给出解决方案。"
version: 1.0.0
author: 小小陆
metadata:
  hermes:
    tags: [diagnostic, api, latency, performance]
---

# API 延迟诊断策略

当用户反馈"回复慢"、"卡住了"、"等很久"时，按以下步骤诊断。

## 诊断流程

### Step 1: 快速定位（30秒内）

```bash
# 1. 检查网关日志中的实际 API 耗时
grep "API call" ~/.hermes/logs/agent.log | tail -10

# 2. 检查网络延迟
ping -c 3 api.xiaomimimo.com 2>&1 | tail -2

# 3. 检查系统负载
uptime

# 4. 检查代理干扰（VPS 常见陷阱）
# 如果 HTTP(S)_PROXY 设置了 mihomo/clash，国内 API（MiMo、DeepSeek）不应走代理
echo "HTTPS_PROXY=$HTTPS_PROXY"
echo "HTTP_PROXY=$HTTP_PROXY"
echo "no_proxy=$no_proxy"
# 如果国内 API 被强制走代理，请求可能超时或返回异常
```

### Step 2: 分析日志数据

从 `agent.log` 中提取关键指标：
- **latency=Xs** — 单次 API 调用耗时
- **in=N** — 输入 token 数
- **cache=N/M (X%)** — 缓存命中率

### Step 3: 判断原因

| 症状 | 原因 | 解决方案 |
|------|------|---------|
| in > 50000 且 latency > 5s | 上下文过长 | 开新会话 `/new` |
| cache% < 50% | 缓存未命中 | 检查 system prompt 稳定性 |
| latency 波动大（3s-16s） | API 服务端抖动 | 等待或切换 provider |
| 出现 `RemoteProtocolError` | API 连接中断 | 自动重试，严重时切换 |
| latency 稳定 > 10s | 模型本身慢 | 考虑换更快的模型 |
| ping > 100ms | 网络问题 | 检查代理/路由 |

### Step 4: 执行修复

**上下文过长（最常见）：**
```
直接告诉用户：上下文已达到 X 万 tokens，建议开新会话。
不要自行压缩，让用户决定。
```

**API 抖动：**
```
检查是否是整点时段（DeepSeek 整点有 180s 卡顿）。
如果是偶发，建议重试；如果持续，建议切换 provider。
```

**缓存问题：**
```
检查 config.yaml 中 prompt_caching 配置。
MiMo 的缓存机制可能与 OpenAI 不同。
```

### Step 5: 报告格式

```
📊 API 延迟诊断报告

【问题】用户反馈回复慢
【诊断】
- 上下文大小：X 万 tokens
- 缓存命中率：X%
- API 平均延迟：X 秒
- 网络延迟：X ms
- 系统负载：X

【原因】上下文过长 / API 抖动 / 网络问题
【建议】开新会话 / 等待 / 切换 provider
```

## 直连 API 延迟基准（MiMo mimo-v2.5）

实测数据（VPS → api.xiaomimimo.com，ping 34ms）：

| 场景 | prompt tokens | 平均耗时 | reasoning_tokens |
|------|--------------|---------|-----------------|
| 短问题 | 15 | 1.2s | 15-19 |
| 带 system prompt | 250 | 1.7s | 49 |
| 带工具定义 | 350 | 2.0s | 25-81 |
| 长上下文 | 4000 | 2.1s | 40-49 |
| 实际 Hermes（8-9万 tokens）| 80000-90000 | 5-16s | — |

**结论：** API 本身很快，上下文大小是延迟的主要决定因素。

## MiMo Provider 特殊行为

详见 `references/mimo-provider-quirks.md`（含实测数据、API 格式、数据源可用性）。

核心要点：
- `extra_body.reasoning` 对 MiMo **无效**，必须用 `thinking: {"type": "disabled"}`
- MiMo 默认 always thinking（即使简单问题也消耗 reasoning_tokens）
- 缓存命中率在日志中显示 98-100%，但 `prompt_tokens_details` 字段为空（MiMo 不返回缓存统计）
- 偶发 `RemoteProtocolError`（连接中断），属于 API 端抖动
- 国内 VPS 数据源：akshare 不稳定，腾讯/新浪可用作为备用
- **xiaomi provider plugin 已支持 thinking 控制**：`build_api_kwargs_extras` 根据 `reasoning_config` 自动设置 `thinking: {"type": "enabled/disabled"}`。config.yaml 设 `reasoning_effort: 'none'` 即可关闭思考模式

## Cron 脚本超时排查

当 cron 任务报 `Script timed out after 120s` 时：
1. 手动运行脚本确认是否能成功：`python3 /path/to/script.py`
2. 如果手动成功但 cron 超时 → 增加 `cron.script_timeout_seconds`（config.yaml）
3. 默认 120s，建议改为 300s（数据抓取类脚本需要余量）
4. 修改 config 后需重启网关生效

## 502 Bad Gateway 诊断

当 API 返回 502 时，**是服务端网关层（openresty/nginx）挂了**，不是我们的问题。

### 诊断流程

```bash
# 1. 确认是 provider 服务端问题而非本地问题
# 用 config 里的 key 直连测试 API
python3 -c "
import yaml, urllib.request
with open('/root/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
providers = cfg.get('providers', {})
for k,v in providers.items():
    if 'mimo' in k.lower():
        req = urllib.request.Request(
            v.get('base_url','').rstrip('/') + '/models',
            headers={'Authorization': f'Bearer {v.get(\"api_key\",\"\")}'}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            print(f'{k}: {resp.status} OK - 服务正常')
        except urllib.error.HTTPError as e:
            print(f'{k}: {e.code} {e.reason}')
            print(f'  body: {e.read().decode(\"utf-8\",\"replace\")[:200]}')
        except Exception as ex:
            print(f'{k}: {ex}')
"

# 2. 检查网关日志中的 502 记录
journalctl --user -u hermes-gateway --since "30 min ago" --no-pager | grep -E "502|Bad Gateway"
```

### 502 vs 429 区分

| 症状 | 含义 | 行为 |
|------|------|------|
| HTTP 429 + `Too many requests` | 速率限制 | 等几秒重试通常能恢复 |
| HTTP 500 + `502 Bad Gateway` (openresty) | 服务端网关层崩溃 | 不会自动恢复，需等 provider 修复 |
| 429 后紧接 502 | 服务端过载导致网关崩溃 | 等 5-10 分钟再测 |

### 实际案例（2026-06-15）

MiMo API 从 429 限流恶化到 502：
- 16:06 连续 429，3次重试全部失败
- 16:09 变成 502 Bad Gateway（openresty 层）
- 16:12 恢复正常（200 OK）
- **持续约 6 分钟**，用户在微信端看到 502 错误

**结论：** 502 = provider 服务端问题，等几分钟自行恢复，不需要重启网关。

### MiMo 模型层降级检测（快速定位是不是模型故障）

当 `mimo-v2.5-pro` 返回 502/超时时，**先测试 `mimo-v2-flash`**，快速判断是模型级还是 API 级故障：

```bash
# 测试轻量模型（不走代理）
curl -s --noproxy "*" --max-time 15 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(grep XIAOMI_API_KEY ~/.hermes/.env | cut -d= -f2)" \
  -d '{"model":"mimo-v2-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":5}' \
  https://api.xiaomimimo.com/v1/chat/completions | head -c 200
```

| 结果 | 含义 | 处理 |
|------|------|------|
| `mimo-v2-flash` ✅ OK, `v2.5-pro` ❌ 502 | **模型级故障**：v2.5-pro 后端过载 | 切 v2-flash 临时用，或等恢复 |
| 两个都 ❌ | **API 级故障**：整个 MiMo 挂了 | 切其他 provider（DeepSeek） |
| 直连 ❌ 走代理 ✅ | **代理问题**：mihomo 干扰了国内 API | 配置 `--noproxy "*"` 直连 |

## 关键原则

1. **不要猜原因，先看日志** — `agent.log` 里有每次 API 调用的精确数据（latency、tokens、cache%）
2. **直连测试排除法** — 用 Python urllib 直连 API，对比网关日志，区分"API 慢"和"Hermes 慢"
3. **缓存统计不一定准确** — MiMo 不返回 `prompt_tokens_details`，但不代表缓存没生效，看日志中的 `cache=N/M (X%)`
4. **DeepSeek 整点有 180s 卡顿** — 已知问题，避开整点时段
5. **开新会话是最快的修复** — 上下文清零，延迟立刻回到基准水平

## 429 限流诊断（Rate Limiting）

当 API 返回 429 错误时，按以下流程判断是服务端限流还是我们请求过多：

### 诊断流程

```bash
# 1. 查看错误日志中的具体限流信息
grep -i "429\|rate.*limit" ~/.hermes/logs/errors.log | tail -10

# 2. 检查是否是特定 provider 的问题
# 3. 尝试切换到其他 provider 测试
```

### 限流类型判断

| 错误码/信息 | 含义 | 解决方案 |
|------------|------|---------|
| `coding_plan_cluster_rate_limited` | 百度千帆 coding 集群过载 | 等待恢复 或 切换 provider |
| `rate_limit_exceeded` (通用) | API 请求频率超限 | 降低并发 或 等待 |
| `requests_per_day_limit` | 日请求量超限 | 等待次日 或 升级套餐 |
| `tokens_per_minute_limit` | token 速率超限 | 减少输入长度 或 等待 |

### 关键判断：是我们的问题还是服务端的问题？

**服务端问题（常见）：**
- 错误信息提到 "high demand"、"cluster"、"overloaded"
- 同一 provider 的所有用户都受影响
- 切换到其他 provider 后正常
- **解决方案**：等待恢复 或 切换 provider

**我们的问题（少见）：**
- 错误信息提到 "per_minute"、"per_day"、"quota"
- 只有我们的请求被限流
- 降低请求频率后恢复
- **解决方案**：优化请求频率 或 升级套餐

### 百度千帆特定问题

百度千帆的 `bce-v3/...` 格式 Key 是 IAM 临时 token，有时效性：
- `invalid_iam_token` → Key 过期，需要重新生成
- `coding_plan_cluster_rate_limited` → 服务端集群过载，等待即可
- **调试口诀**：先换 provider 测试（如切到 DeepSeek），如果正常 → 千帆服务端问题
