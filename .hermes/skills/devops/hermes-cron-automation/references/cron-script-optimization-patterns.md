# Cron 脚本优化模式

## skip_official 模式（多用户推送）

**问题：** 脚本对每个用户分别跑 `main.py --official`，每次 ~50s × N 用户 = 超时。

**解决：** 添加 `skip_official` 参数，只采集一次数据，其他用户复用。

```python
def generate_report(user_id='lulu', skip_official=False):
    """生成报告。skip_official=True 时跳过数据采集，复用已有报告文件。"""
    if not skip_official:
        try:
            subprocess.run(
                ['python3', 'main.py', '--official'],
                cwd=STOCK_DIR, capture_output=True, text=True, timeout=300
            )
        except subprocess.TimeoutExpired:
            print("⚠️ 报告生成超时，尝试读取已有数据")
        except Exception as e:
            print(f"⚠️ 报告生成异常: {e}")

    if user_id != 'lulu':
        try:
            subprocess.run(
                ['python3', 'main.py', '--report', '--user', user_id],
                cwd=STOCK_DIR, capture_output=True, text=True, timeout=30
            )
        except:
            pass

    files = sorted(glob.glob(os.path.join(REPORT_DIR, 'report_*.md')), reverse=True)
    if files:
        with open(files[0], encoding='utf-8') as f:
            return f.read().strip()
    return '⚠️ 报告生成失败'

# 主流程
lulu_report = generate_report('lulu')              # 采集+生成（~50s）
other_report = generate_report('UserB', skip_official=True)  # 复用数据（<1s）
```

**验证结果（2026-06-07）：**
- 修复前：2 分 27 秒（3 次 official 调用）
- 修复后：53 秒（1 次 official 调用）

## 文本裁剪模式（替代 subprocess）

如果 `--report --user` 不可用，可以用正则裁剪完整报告：

```python
import re

def strip_portfolio(report):
    """去掉报告中的持仓段落"""
    pattern = r'──────────────────────────────\n📋 持仓.*?(?=──────────────────────────────|$)'
    return re.sub(pattern, '', report, flags=re.DOTALL).strip()
```

## 数据源超时处理

akshare 等数据源偶尔连接断开（`RemoteDisconnected`），导致重试：
- `retry_call(max_retries=2, delay=2)` — 每个接口最多 3 次尝试
- 7 个接口串行调用，最坏情况：7 × 30s × 3 = 630s
- 建议：cron 超时设 300s，脚本内部子进程超时也设 300s
