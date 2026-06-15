# Gateway 系统通知抑制规则

多用户部署时，系统通知必须只发管理员，不能发给其他用户。

## 通知类型

| 类型 | 触发时机 | 默认行为 | 抑制方法 |
|------|---------|---------|---------|
| **Shutdown 通知** | 网关收到 SIGINT/SIGTERM | 发到 home channel | 已正确（仅 KuHai）✅ |
| **Auto-resume 中断注** | 网关重启后自动恢复会话 | 注入到所有活跃会话 | agent 侧静默处理 |
| **Self-improvement review** | 每次 turn 结束后 | 显示在会话中 | `display.turn_completion_explainer: false` |
| **权限审批通知** | 用户越权操作 | 转发建议给 admin | 仅发 KuHai（send_wecom.py） |
| **Background process 完成** | 后台进程退出 | 注入到关联会话 | 已在 config.yaml 设置 `background_process_notifications: false` |

## 配置方法

### 关闭 Self-improvement review

```bash
hermes config set display.turn_completion_explainer false
```

### 静默背景进程通知

```yaml
# config.yaml
display:
  background_process_notifications: false
```

### 设置 home channel（仅此通道收系统通知）

```
/sethome
```

验证：
```bash
grep HOME_CHANNEL /root/.hermes/.env
```

### 自动 resume 中断通知

当网关重启后自动恢复会话时，会注入 `[System note: ... interrupted ...]` 到**所有**活跃会话，包括非管理员用户。

**抑制方法：** agent 检测到此注记时，对非管理员用户**不生成可见回复**。涉及的 skill：
- `gateway-restart-handler` — 单个会话级别处理
- `gateway-administration` — 整体部署配置（本文件）

## 验证清单

部署后检查：

- [ ] gateway 日志显示 `Sent shutdown notification to active chat weixin:...`（仅管理员）
- [ ] gateway 日志显示 `Scheduled auto-resume for N session(s)`（有这个正常，但非管理员会话不应产生可见消息）
- [ ] config.yaml 中 `display.turn_completion_explainer: false`
- [ ] config.yaml 中 `display.background_process_notifications: false`
- [ ] 企微消息中，非管理员用户没有收到任何系统通知
- [ ] 每日总结 cron 有 `script: calculate_token_cost.py`（token 费用精确计算）
