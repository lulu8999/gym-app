# 图片类社交媒体内容提取工作流

适用场景：抖音/小红书等平台的图文轮播帖（图片里嵌文字，不是纯文本页面）。

## 核心原则

**图片里有内容 → 直接用 vision_analyze 看图，不要尝试文本提取。**

用户明确纠正过：网页提取、DOM解析等方式对图片帖无效，应直接走视觉模型。

## 标准流程

### Step 1: 解析短链接获取真实 URL
```bash
curl -sL -o /dev/null -w '%{url_effective}' "https://v.douyin.com/xxxxx/"
# 输出: https://www.douyin.com/note/7651185161635392936
```

### Step 2: 用浏览器打开页面
```python
browser_navigate(url=真实URL)
```

### Step 3: 用 JS Console 提取图片 URL
```javascript
const images = document.querySelectorAll('img');
const urls = [];
images.forEach(img => {
  if (img.src && !img.src.includes('data:') && img.width > 100) {
    urls.push({src: img.src, width: img.width, height: img.height});
  }
});
JSON.stringify(urls);
```

注意：每张图通常有两个尺寸（缩略图+大图），需要按宽度去重。

### Step 4: 下载图片到本地
```bash
mkdir -p /tmp/extracted_images
curl -sL -o /tmp/extracted_images/img_00.webp '图片URL'
```

### Step 5: 用 vision_analyze 逐张分析
```python
vision_analyze(
    image_url="/tmp/extracted_images/img_00.webp",
    question="这张图片上的所有文字内容是什么？"
)
```

## 注意事项

- **抖音图文帖**：17页的帖子可能只加载了前10张左右的图片，后续需要翻页
- **翻页**：浏览器内翻页按钮可能不好定位，可以在 JS Console 里操作
- **输出整理**：分析完所有图片后，给用户做结构化总结（标题、内容、分类）
- **web_extract 对图片帖无效**：只能拿到页面框架和评论区，拿不到图片内容

## 已知平台

| 平台 | 图片提取 | 备注 |
|------|----------|------|
| 抖音（图文） | ✅ 本流程 | 图片CDN: p3-pc-sign.douyinpic.com |
| 小红书 | ✅ 同理 | 图片嵌在页面中 |
| 微博 | ⚠️ 部分 | 有些帖是纯文本 |
