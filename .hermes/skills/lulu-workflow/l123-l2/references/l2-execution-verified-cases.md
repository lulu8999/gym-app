# L2 验证案例 — 端到端执行记录

## 案例 1：健身管理网页（2026-06-12）

```
输入: "帮我写一个健身管理网页，记录健身动作与组数，同时记录心情，
      记录每次体重，引入常用食谱，支持用户登录使用，
      先出 plan 然后执行，执行之后给报告"

L1: coding → claude_code, is_complex=1
L2 (DeepSeek): 6 步
  1. [claude_code] 设计数据库模型与API
  2. [claude_code] 实现用户登录与认证
  3. [claude_code] 实现健身记录与心情体重功能
  4. [claude_code] 引入常用食谱模块
  5. [claude_code] 构建前端页面与交互
  6. [hermes] 集成测试与部署准备

结果: ✅ 6/6 通过，部署到 gym.lulugame.fun
Bug 修复: litellm 未装、关键词"网页"误伤 scraping、handler 被覆盖为 l2_dispatcher
```

## 案例 2：新闻爬虫 + 图片生成（2026-06-12）

```
输入: "把刚刚做的健身网页去掉，dns也去掉，然后写一个爬虫脚本，
      能爬取今日头条的热门二十条新闻，然后汇总成图片发给我"

L1: coding → claude_code, is_complex=1
L2 (DeepSeek): 3 步
  1. [claude_code] 移除健身网页和DNS配置
  2. [openclaw] 编写爬虫脚本爬取今日头条热门新闻
  3. [claude_code] 将新闻汇总生成图片

结果: ✅ 3/3 通过，铁律指令有效（agent 严格逐步执行，未跳步）
每步输出 "[L2] Step N 完成" 标记
```

## 关键教训

### 中文图片生成：Noto Sans CJK SC + BMP-Only 过滤

**问题**：新闻标题含 emoji → Noto Sans CJK SC 字体无对应 glyph → 方块/空白

**错误方案**：用 `font.getmask()` 逐字检查 → 对所有中文返回空 mask，全部被过滤

**正确方案**：
```python
def strip_unsupported(text, font):
    """只移除 BMP 外的 emoji，保留所有中文和标点"""
    result = []
    for ch in text:
        cp = ord(ch)
        if cp <= 0xFFFF:           # BMP 内：中文、标点、字母数字全保留
            result.append(ch)
        elif 0x20000 <= cp <= 0x2FFFF:  # SIP: CJK 扩展
            result.append(ch)
        # 跳过 emoji (0x1F000-0x1FFFF)
    return "".join(result)
```

**字体选择**：`/usr/share/fonts/chinese/NotoSansCJKsc-Regular.otf`（系统自带，无需额外安装）

### 头条爬虫：API 优于 Selenium

**方案**：直接调用头条热榜 API `https://www.toutiao.com/hot-event/hot-board/` 而非 Selenium 模拟浏览器。
- 返回 JSON → 直接解析 → 无需等渲染
- 无登录墙、无验证码
- 速度快（<1s vs 10s+）
