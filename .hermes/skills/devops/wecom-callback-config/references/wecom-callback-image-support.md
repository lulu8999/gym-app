# WeCom Callback 图片消息支持

## 修改内容

在 `gateway/platforms/wecom_callback.py` 的 `_build_event` 方法中增加了图片消息处理。

## 改动点

1. **第350行：** 允许的 MsgType 集合从 `{"text", "event"}` 扩展为 `{"text", "event", "image"}`
2. **新增第368-379行：** 处理 image 类型消息
   - 从 XML 中提取 `PicUrl`（图片URL，可下载）和 `MediaId`（素材ID，需调用企微API下载）
   - 以 `[图片] PicUrl=xxx MediaId=xxx` 格式创建 MessageEvent
   - 消息类型设为 `MessageType.PHOTO`

## 代码片段

```python
# Handle image messages
if msg_type == "image":
    pic_url = root.findtext("PicUrl", default="")
    media_id = root.findtext("MediaId", default="")
    content = f"[图片] PicUrl={pic_url} MediaId={media_id}"
    return MessageEvent(
        text=content,
        message_type=MessageType.PHOTO,
        source=source,
        raw_message=xml_text,
        message_id=msg_id,
    )
```

## 使用方式

用户通过企微应用发图片后，agent 会收到形如 `[图片] PicUrl=https://xxx MediaId=xxx` 的文本消息。agent 可用 `curl` 或 `urllib` 下载 PicUrl 链接的图片，再调用 Kimi 视觉 API 进行识别。

## 后续可扩展

- 文件类型（MsgType=file）：提取 `MediaId` 和 `FileName`
- 语音类型（MsgType=voice）：提取 `MediaId` 和 `Format`
- 图片自动下载（通过 MediaId + 企维 access_token 下载）
