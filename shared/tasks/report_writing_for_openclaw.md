## 任务：接管股票报告生成与发送

> 写入时间：2026-06-10

### 背景
Hermes 当前通过 cron 运行以下两个报告任务，但应该分配给 OpenClaw 来执行：

1. **📊 股票晨报（工作日 10:00）**
   - 运行 `/root/stock_analyzer/main.py --official` 生成 Lulu 的完整报告
   - 再分别用 `--report --user FengZaiQiShi` 和 `--report --user LuWeiFeng` 生成师父和老爹的报告
   - 附带天气信息（从 `/root/.hermes/scripts/location_server/locations.json` 读取城市）
   - 通过企业微信发送给 KuHai、FengZaiQiShi、LuWeiFeng

2. **📉 股票收盘报告（工作日 15:30）**
   - 运行 `/root/stock_analyzer/main.py --verify` 验证昨日预测
   - 运行 `/root/stock_analyzer/main.py --report` 生成当日收盘报告
   - 通过企业微信发送

### 关键技术信息
- 股票分析系统：`/root/stock_analyzer/`
- 企业微信发送脚本：`/root/stock_analyzer/send_wecom.py <userId> <消息内容>`
- 企微配置：`/root/.openclaw/openclaw.json` (channels.wecom)
- 天气数据：wttr.in API
- 用户映射：KuHai（Lulu）、FengZaiQiShi（师父）、LuWeiFeng（老爹）

### 要求
1. OpenClaw 接管以上两个定时报告任务
2. 保持与现有相同的发送频率和收件人
3. Hermes 那边的对应 cron 任务（📊 股票晨报、📉 股票收盘报告）可以停掉
4. 报告格式和内容保持不变

### 确认
完成后请通过企业微信通知 Lulu："股票报告已由 OpenClaw 接管 ✅"
