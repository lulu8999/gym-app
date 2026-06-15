# WeCom 回调模式文件发送限制

## 症状

通过 `send_message` 工具向 `wecom_callback:KuHai` 发送文件（Excel/图片等附件）时：
- `send_message` 返回 **success**
- 但 note 显示 `chat_id: sisu.` **而非** `chat_id: KuHai`
- 用户实际 **收不到文件**

即使使用完整目标 ID `wecom_callback:ww815119bb08398d37:KuHai`，chat_id 仍然解析为 `sisu.`。

## 根因

尚未完全定位。可能与 wecom_callback 平台的用户映射机制有关：
- 同一企业微信 corpId 下的多个用户（KuHai 和 sisu.）在 Hermes 内部被映射到同一个 home channel
- 文件媒体附件（media 参数）的投递目标与文本消息不一致
- 可能底层企微 API 要求文件需先上传获取 media_id，Hermes 的 send_message 未实现该流程

## 当前限制（已知）

| 功能 | 微信 (weixin) | 企微回调 (wecom_callback) |
|------|---------------|--------------------------|
| 发送文本消息 | ✅ 正常 | ⚠️ 可能发错用户 |
| 发送文件附件 | ❌ 不支持 | ❌ 映射错误 |
| 发送图片 | ❌ 不支持 | ⚠️ 需验证 |

## 替代方案

如果需要给 KuHai 用户发送文件，目前可行的方案：

1. **文本内容直接发** — 将文件内容转为 Markdown 表格或文本，通过文本消息发送（微信文本消息是通的）
2. **企微主动拉取** — 通过 OpenClaw 网关的企业微信 AI Bot 模式发送（需正确配置 WeCom 插件的 bot_id/secret）
3. **下载链接** — 将文件放在可通过公网访问的 HTTP 服务上，发送下载链接
4. **OpenClaw agent** — 启动 OpenClaw 网关后，通过其 WeCom 集成发送文件

## 验证方法

发送测试消息时检查返回的 note 字段：
```python
# 正常应该显示 chat_id: KuHai
# 实际显示 chat_id: sisu. ← 说明映射有问题
{"note": "Sent to wecom_callback home channel (chat_id: sisu.)"}
```

查看通道目录确认用户 ID：
```bash
cat /root/.hermes/channel_directory.json | grep wecom_callback -A 4
```
