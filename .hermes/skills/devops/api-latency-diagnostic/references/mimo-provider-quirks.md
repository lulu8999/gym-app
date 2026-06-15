# MiMo Provider 特殊行为

## Thinking 控制

MiMo 的 reasoning/thinking 控制机制与其他 provider 不同：

### ❌ 无效的方式
```python
extra_body["reasoning"] = {"enabled": False}  # MiMo 完全忽略这个参数
```

### ✅ 正确的方式
```python
extra_body["thinking"] = {"type": "disabled"}  # 与 Kimi 相同的机制
```

### 实测数据

| 参数 | reasoning_tokens | 耗时 |
|------|-----------------|------|
| 无参数（默认） | 16-19 | 1.4s |
| `reasoning.enabled=false` | 16-19（无效） | 1.4s |
| `thinking.type=disabled` | **0** | 1.2s |
| `reasoning_effort=none` | 400 Bad Request | — |

### Hermes 中的配置路径

1. `config.yaml` → `agent.reasoning_effort: 'none'`
2. → `parse_reasoning_effort("none")` → `{"enabled": False}`
3. → 传入 `chat_completions.py` 的 `reasoning_config`
4. → **xiaomi 插件** `build_api_kwargs_extras()` 检查 `reasoning_config.enabled`
5. → 添加 `extra_body["thinking"] = {"type": "disabled"}`

**注意：** 默认情况下 `reasoning_config` 为 None，thinking 保持开启。

### xiaomi 插件实现

位置：`plugins/model-providers/xiaomi/__init__.py`

```python
class XiaomiProvider(ProviderProfile):
    def build_api_kwargs_extras(self, *, reasoning_config=None, **context):
        thinking_enabled = True
        if reasoning_config and isinstance(reasoning_config, dict):
            if reasoning_config.get("enabled") is False:
                thinking_enabled = False
        return {"thinking": {"type": "enabled" if thinking_enabled else "disabled"}}, {}
```

## 缓存行为

- MiMo API 返回的 `prompt_tokens_details` 字段**始终为空**
- 但这不代表缓存没生效
- 日志中的 `cache=N/M (X%)` 是准确的缓存命中率（实测 98-100%）
- 不需要额外传递 `cache_control` 参数

## 连接稳定性

- 偶发 `RemoteProtocolError: peer closed connection without sending complete message body`
- 属于 API 端抖动，Hermes 自动重试（最多 3 次）
- 高峰期（A股收盘前后）更频繁
- 不需要特殊处理，重试机制已覆盖

## 数据源可用性（VPS 国内环境）

| 数据源 | 状态 | 说明 |
|--------|------|------|
| akshare (东方财富) | ⚠️ 不稳定 | `RemoteDisconnected` 频发，需重试 |
| 腾讯财经 qt.gtimg.cn | ✅ 可用 | 实时指数，作为备用源 |
| 新浪财经 hq.sinajs.cn | ✅ 可用 | 全球市场+大宗商品 |
| 东方财富 push2 API | ❌ 被墙 | VPS IP 被限制 |
| 东方财富 datacenter | ⚠️ 部分可用 | 融资融券等接口偶尔超时 |
| 中国债券信息网 | ✅ 可访问 | 国债收益率 |

### 新浪财经 API 格式

**全球市场：**
```
var hq_str_int_dji="道琼斯,46247.29,299.97,0.65";
→ 解析: name, price, change, change_pct
```

**大宗商品：**
```
var hq_str_hf_GC="4351.997,,4353.800,4354.300,4508.700,4336.600,04:59:59,4505.000,4503.000,...";
→ vals[0]=当前价, vals[7]=昨收价
→ 涨跌幅 = (当前价 - 昨收) / 昨收 × 100
```
