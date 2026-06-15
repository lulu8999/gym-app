# WeasyPrint 中文 PDF 生成指南

## 安装
```bash
pip install weasyprint
# 或已预装在 Hermes venv 中
```

## 基本用法
```bash
weasyprint input.html output.pdf
```

## 字体配置

### 检查可用中文字体
```bash
fc-list :lang=zh
```

### 常见中文字体路径
- `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
- `/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc`
- `/usr/share/fonts/chinese/NotoSansCJKsc-Regular.otf`

### CSS 字体声明
```css
body {
    font-family: "Noto Sans CJK SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
}
```

### ⚠️ Noto Sans CJK SC 不支持的内容
以下字符会触发 `notdef glyph` 警告（不影响 PDF 生成，但显示为空白）：
- Emoji：⭐ 🔐 ✅ ❌ ⚠️ 🔓 🛡️ ➡️ ❓
- 解决方案：用纯文本替代
  - `⭐⭐⭐` → `[高]` 或 `(3/5)`
  - `✅` → `[OK]`
  - `❌` → `[X]`

## 分页控制

```css
.page-break { page-break-before: always; }
.cover {
    text-align: center;
    padding-top: 120px;
    page-break-after: always;
}
```

## 表格样式（推荐）
```css
table { border-collapse: collapse; width: 100%; font-size: 10pt; }
th, td { border: 1px solid #ddd; padding: 8px 10px; }
th { background-color: #0f3460; color: white; }
tr:nth-child(even) { background-color: #f8f9fa; }
```

## 安全标签颜色
```css
.danger { background-color: #ffebee; color: #c62828; }
.warning { background-color: #fff8e1; color: #f57f17; }
.safe { background-color: #e8f5e9; color: #2e7d32; }
```

## PDF 封面模板
```html
<div class="cover">
  <h1>报告标题<br>副标题</h1>
  <div class="subtitle">报告说明</div>
  <div class="date">2026 年 6 月 · 小小陆 出品</div>
</div>
```

## 预算成本参考
- 纯文本报告（~2500字HTML，10+品牌）：~0 额外 token（数据已搜完）
- 含 5 次 web_search 调研：~500-1000 token
- delegate_task 全品牌调研：~5000-6000 token（回传摘要）
