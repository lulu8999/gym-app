---
name: browser-tool-selection
description: 浏览器工具选择指南 — 何时使用内置浏览器、OpenClaw 或 curl，包含性能对比和最佳实践
triggers:
  - 浏览器选择
  - 工具选择
  - 网页抓取
  - 截图网页
  - 浏览器性能
---

# 浏览器工具选择指南

## 工具概览

| 工具 | 用途 | 优点 | 缺点 |
|------|------|------|------|
| **内置浏览器** (Browserbase) | 简单页面操作 | 快速、集成度高 | 容易被反爬检测 |
| **OpenClaw** | 复杂页面/反爬绕过 | 真实浏览器环境 | 命令开销大、较慢 |
| **curl/wget** | 静态内容获取 | 最快、最稳定 | 无JS渲染 |
| **web_extract** | 页面内容提取 | 智能提取 | 需要网络 |

## 选择决策树

```
任务类型？
├── 获取静态内容（HTML/JSON）→ curl/wget
│   └── 示例：API调用、静态页面
├── 需要JS渲染 → 浏览器工具
│   ├── 简单页面（无反爬）→ 内置浏览器
│   │   └── 示例：普通网页截图、表单填写
│   └── 复杂页面（有反爬）→ OpenClaw
│       └── 示例：Cloudflare保护、需要登录
├── 提取页面内容 → web_extract
│   └── 示例：文章提取、数据抓取
└── 批量操作 → 脚本化
    └── 示例：批量截图、批量下载
```

## 性能对比

### 速度测试（实际测量）

| 操作 | 内置浏览器 | OpenClaw | curl |
|------|-----------|----------|------|
| 导航到页面 | 2-5秒 | 3-8秒 | 0.5-2秒 |
| 截图 | 1-2秒 | 2-3秒 | N/A |
| 点击元素 | 0.5-1秒 | 1-2秒 | N/A |
| 滚动页面 | 0.3-0.5秒 | 0.5-1秒 | N/A |

### 内存占用

| 工具 | 内存占用 | 说明 |
|------|---------|------|
| 内置浏览器 | 低 | 云端运行 |
| OpenClaw | 中-高 | 本地Chrome进程 |
| curl | 极低 | 命令行工具 |

## 使用场景

### 1. 简单页面截图
```bash
# 推荐：内置浏览器
browser_navigate("https://example.com")
browser_screenshot()
```

### 2. 有反爬的页面
```bash
# 推荐：OpenClaw
openclaw browser navigate "https://example.com"
openclaw browser screenshot t1
```

### 3. 获取API数据
```bash
# 推荐：curl
curl -s "https://api.example.com/data" | jq .
```

### 4. 提取文章内容
```bash
# 推荐：web_extract
web_extract("https://blog.example.com/article")
```

### 5. 批量截图
```bash
# 推荐：脚本化 + OpenClaw
#!/bin/bash
for url in "${urls[@]}"; do
  openclaw browser navigate "$url"
  sleep 2
  openclaw browser screenshot t1
done
```

## 最佳实践

### 1. 优先使用简单工具
- 能用 curl 解决的不用浏览器
- 能用内置浏览器的不用 OpenClaw
- 减少不必要的工具切换

### 2. 错误处理
```bash
# 内置浏览器超时
try:
    browser_navigate(url)
except TimeoutError:
    # 切换到 OpenClaw
    openclaw browser navigate "$url"
```

### 3. 资源管理
```bash
# 用完及时关闭
openclaw browser close t1

# 清理临时文件
rm -f ~/.openclaw/media/browser/*.png
```

### 4. 并发控制
```bash
# 避免同时打开太多标签页
# 最多同时 3-5 个标签页
```

## 故障排除

### 内置浏览器无法访问
```bash
# 检查网络
curl -I https://example.com

# 检查浏览器配置
cat ~/.hermes/config.yaml | grep browser

# 尝试 OpenClaw
openclaw browser navigate "https://example.com"
```

### OpenClaw 无响应
```bash
# 检查进程
ps aux | grep openclaw

# 重启
openclaw browser stop
openclaw browser start
```

### 截图为空
```bash
# 等待页面加载
sleep 3
openclaw browser screenshot t1

# 检查页面内容
openclaw browser tabs
```

## 集成到工作流

### 1. 自动降级
```python
def smart_browser_navigate(url):
    """智能选择浏览器工具"""
    try:
        # 先尝试内置浏览器
        browser_navigate(url)
        return "builtin"
    except:
        # 失败则用 OpenClaw
        subprocess.run(["openclaw", "browser", "navigate", url])
        return "openclaw"
```

### 2. 结果缓存
```bash
# 缓存截图，避免重复抓取
CACHE_DIR="/root/.cache/screenshots"
md5=$(echo -n "$url" | md5sum | cut -d' ' -f1)
cache_file="$CACHE_DIR/$md5.png"

if [ -f "$cache_file" ]; then
    echo "Using cached screenshot"
else
    openclaw browser navigate "$url"
    openclaw browser screenshot t1
    cp ~/.openclaw/media/browser/*.png "$cache_file"
fi
```

### 3. 批量处理
```bash
# 批量截图脚本
#!/bin/bash
URLS_FILE="urls.txt"
OUTPUT_DIR="screenshots"
mkdir -p "$OUTPUT_DIR"

while IFS= read -r url; do
    filename=$(echo "$url" | md5sum | cut -d' ' -f1).png
    openclaw browser navigate "$url"
    sleep 2
    openclaw browser screenshot t1
    cp ~/.openclaw/media/browser/*.png "$OUTPUT_DIR/$filename"
done < "$URLS_FILE"
```

## 相关 Skill

- `anti-scraping-strategies` - 反爬绕过策略
- `hermes-agent` - Hermes 配置和工具管理
- `vps-file-hosting` - 大文件托管
