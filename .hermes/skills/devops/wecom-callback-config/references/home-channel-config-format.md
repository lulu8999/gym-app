# Home Channel 配置格式问题

## 问题描述

`home_channel` 在 `config.yaml` 中必须是对象格式，不能是字符串。

## 错误示例

```yaml
# ❌ 错误：字符串格式
home_channel: wecom_callback:sisu.
```

**报错信息**：
```
TypeError: string indices must be integers, not 'str'
# 或
KeyError: 'chat_id'
```

## 正确格式

```yaml
# ✅ 正确：对象格式
home_channel:
  platform: wecom_callback
  channel: sisu.
  chat_id: sisu.
```

## 字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `platform` | 平台标识符 | `wecom_callback` |
| `channel` | 频道/会话标识 | `sisu.` |
| `chat_id` | 聊天ID（与channel相同） | `sisu.` |

## 修复步骤

1. 用 `hermes config set` 设置三个字段：
```bash
hermes config set gateway.platforms.wecom_callback.home_channel.platform wecom_callback
hermes config set gateway.platforms.wecom_callback.home_channel.channel sisu.
hermes config set gateway.platforms.wecom_callback.home_channel.chat_id sisu.
```

2. 删除旧的字符串格式行：
```bash
sed -i '/home_channel: wecom_callback:sisu./d' ~/.hermes/config.yaml
```

3. 重启网关：
```bash
hermes gateway restart
```

## 诊断命令

查看网关启动错误：
```bash
journalctl --user -u hermes-gateway -n 30 --no-pager
```

检查配置是否正确：
```bash
grep -A 5 "home_channel:" ~/.hermes/config.yaml
```
