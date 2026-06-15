# DeepSeek API 常见故障模式

## Stale Stream 超时（最常见）

**症状：** cron 任务中 API 请求卡住 180 秒后超时。

**日志特征：**
```
Stream stale for 180s — no chunks received.
peer closed connection without sending complete message body
http_status=200 bytes=0 chunks=0 elapsed=180.18s ttfb=-
upstream=[server=openresty]
```

**关键信号：**
- `http_status=200` — 连接已建立，但无数据返回
- `ttfb=-` — 首字节时间不存在（模型从未开始推流）
- `upstream=openresty` — DeepSeek 用的 OpenResty
- `Stream drop on attempt 2/3 — retrying` — 自动重试

**原因：** DeepSeek 网关接受了请求但模型后端没有响应。不是网络问题，是后端容量/排队问题。整点附近（6:00、8:00）较常见。

**处理：**
- 不需要手动干预 — Hermes 自动重试，第三次通常成功
- 不会产生额外 token 消耗（请求没进到模型不计费）

## 正常延迟范围

| 指标 | 正常 | 异常 |
|------|------|------|
| API 延迟 | 1-12 秒 | >30 秒 |
| 首字节时间 | <3 秒 | >10 秒 |
| 缓存命中率 | 80-100% | <50% |