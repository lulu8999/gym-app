---
name: anti-scraping-strategies
description: 反爬绕过策略 — 当内置浏览器被封时，使用 OpenClaw 作为备用方案，包含工具选择决策树和最佳实践
triggers:
  - 网站被封
  - 浏览器超时
  - 反爬机制
  - 爬虫失败
  - 采集素材
  - 截图网页
---

# 反爬绕过策略指南

## 工具选择决策树

```
需要浏览器操作？
├── 简单页面（无JS/反爬）→ 内置浏览器 (Browserbase)
│   └── 优点：快速、集成度高
│   └── 缺点：容易被反爬检测
├── 复杂页面（有JS/反爬）→ OpenClaw
│   └── 优点：真实浏览器环境、绕过大部分反爬
│   └── 缺点：命令开销大、需要单独管理
└── 静态内容 → curl/wget + 终端
    └── 优点：最快、最稳定
    └── 缺点：无JS渲染
```

## 内置浏览器被反爬的信号

1. **页面超时**：`Page.navigate` 命令超时
2. **空内容**：页面加载但内容为空
3. **验证码**：出现 Cloudflare/challenge 页面
4. **403/429错误**：HTTP 状态码异常
5. **无限加载**：页面一直处于 loading 状态

## OpenClaw 备用方案

### 安装检查
```bash
# 检查 OpenClaw 是否可用
openclaw --version
# 如果未安装，参考 hermes-agent skill 安装
```

### 常用命令

```bash
# 启动浏览器（如果未运行）
openclaw browser start

# 导航到页面
openclaw browser navigate "https://example.com"

# 查看当前标签页
openclaw browser tabs

# 截图
openclaw browser screenshot t1

# 滚动
openclaw browser press PageDown
openclaw browser press End

# 点击元素（需要先获取元素ID）
openclaw browser snapshot t1
openclaw browser click t1 <element-id>

# 输入文字
openclaw browser type t1 <element-id> "text"
```

### 批量截图脚本

```bash
#!/bin/bash
# batch_screenshot.sh - 批量截图多个页面

URLS=(
  "https://example.com/page1"
  "https://example.com/page2"
  "https://example.com/page3"
)

OUTPUT_DIR="/root/screenshots"
mkdir -p "$OUTPUT_DIR"

for i in "${!URLS[@]}"; do
  url="${URLS[$i]}"
  filename="page_$((i+1)).png"
  
  echo "Processing: $url"
  
  # 导航
  openclaw browser navigate "$url" 2>&1 | tail -2
  
  # 等待加载
  sleep 3
  
  # 截图
  openclaw browser screenshot t1 2>&1 | tail -2
  
  # 复制到输出目录
  cp ~/.openclaw/media/browser/*.png "$OUTPUT_DIR/$filename"
  
  echo "Saved: $OUTPUT_DIR/$filename"
  
  # 间隔，避免触发反爬
  sleep 2
done

echo "Done! Screenshots saved to $OUTPUT_DIR"
```

## 最佳实践

### 1. 间隔控制
- 每次请求间隔 2-3 秒
- 批量操作时每 10 个请求休息 10 秒
- 避免在高峰期（工作日白天）大量请求

### 2. User-Agent 轮换
```bash
# OpenClaw 默认使用真实 Chrome User-Agent，无需额外配置
```

### 3. 错误处理
```bash
# 检查命令返回值
if ! openclaw browser navigate "$url" 2>&1 | grep -q "navigated"; then
  echo "Navigation failed, retrying..."
  sleep 5
  openclaw browser navigate "$url"
fi
```

### 4. 资源清理
```bash
# 关闭不需要的标签页
openclaw browser close t2 t3 t4

# 清理媒体文件
rm -f ~/.openclaw/media/browser/*.png
```

## 故障排除

### OpenClaw 无响应
```bash
# 检查进程
ps aux | grep openclaw

# 重启 OpenClaw
openclaw browser stop
openclaw browser start
```

### 截图为空
```bash
# 检查页面是否加载
openclaw browser tabs

# 等待更长时间
sleep 5
openclaw browser screenshot t1
```

### 内存占用过高
```bash
# 关闭多余标签页
openclaw browser tabs
openclaw browser close t2 t3 t4 t5
```

## 与内置浏览器的对比

| 场景 | 内置浏览器 | OpenClaw |
|------|-----------|----------|
| 简单静态页面 | ✅ 推荐 | ⚠️ 可用但开销大 |
| 有JS渲染的页面 | ⚠️ 可能失败 | ✅ 推荐 |
| 有反爬机制的页面 | ❌ 容易被封 | ✅ 推荐 |
| 需要登录的页面 | ⚠️ 需要配置Cookie | ✅ 支持 |
| 批量采集 | ⚠️ 有限制 | ✅ 推荐 |
| 性能要求高 | ✅ 推荐 | ⚠️ 较慢 |

## 实际案例

### 案例1：21st.dev 素材采集
- **问题**：内置浏览器访问 21st.dev 超时
- **解决**：切换到 OpenClaw，成功采集 13 类组件截图
- **耗时**：约 15 分钟完成全部采集

### 案例2：Cloudflare 保护的网站
- **问题**：内置浏览器遇到 Cloudflare 验证
- **解决**：OpenClaw 可以自动处理大部分 Cloudflare 验证
- **注意**：部分高级验证仍需手动处理

## 相关 Skill

- `hermes-agent` - Hermes 配置和工具管理
- `vps-file-hosting` - 大文件托管（采集的素材可以托管）
- `ncm-converter` - 文件转换（如果需要转换采集的文件）
