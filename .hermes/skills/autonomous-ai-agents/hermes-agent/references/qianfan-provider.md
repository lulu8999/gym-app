# 百度千帆大模型平台 — Provider Configuration

## API 端点

千帆提供 OpenAI 兼容接口，可作为 `custom` provider 接入 Hermes。

```
Base URL:  https://qianfan.baidubce.com/v2
Endpoint:  /chat/completions
```

## 认证

```bash
# ~/.hermes/.env
QIANFAN_API_KEY=bce-v3/你的API Key
```

API Key 格式为 `bce-v3/` 开头的字符串，在百度智能云控制台「千帆大模型平台 → API Key 管理」创建。

## 常用模型

| 模型 | 说明 |
|------|------|
| `ernie-3.5-8k` | 速度快，成本低 |
| `ernie-4.0-8k` | 能力更强 |
| `ernie-speed-8k` | 极速响应 |
| `ernie-4.0-turbo-8k` | 均衡选择 |

## Hermes 配置

```bash
hermes config set model.base_url https://qianfan.baidubce.com/v2
hermes config set model.default ernie-3.5-8k
hermes config set model.provider custom
```

或在 `~/.hermes/.env` 中设置 `QIANFAN_API_KEY`，然后在 `config.yaml` 中配置 custom provider。

## 测试

```bash
# 快速测试
curl -X POST https://qianfan.baidubce.com/v2/chat/completions \
  -H "Authorization: Bearer $QIANFAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"ernie-3.5-8k","messages":[{"role":"user","content":"你好"}]}'

# 通过 Hermes 测试
hermes chat -q "你好" --provider custom
```

## 注意事项

- 千帆按调用次数计费，新用户有免费额度
- API Key 需要先在控制台开通千帆大模型平台服务
- 错误日志查看：`tail -f ~/.hermes/logs/agent.log`

## 参考

- 千帆控制台：https://cloud.baidu.com （千帆大模型平台）
- 文档：https://cloud.baidu.com/doc/qianfan/index.html
