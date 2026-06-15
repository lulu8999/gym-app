# 为什么使用 Markdown + Pandoc 而非直接操作 Word

## 问题背景

AI 直接操作 Word 文档（通过 `python-docx`）时，表格内容很容易被错误地转换成独立段落。

### 典型问题示例

**错误的结果**（python-docx 直接操作）：
```
段落36: 【三、调节方式】
段落37: 【调节方式】 ← 这应该是表格标题行
段落38: 【特点】
段落39: 【例子】
段落40: 【神经调节】 ← 数据行被拆散
段落41: 【快、准、短】
段落42: 【膝跳反射...】
```

**正确的结果**（Markdown + Pandoc）：
```
段落1: 【三、调节方式】
段落2: 【表格：调节方式对比】
```

## 问题原因

1. **python-docx 的表格 API 复杂** - 需要精确控制每个单元格
2. **AI 容易混淆段落和表格** - 不能可靠地识别表格结构
3. **表格内容被拆散** - 每个单元格变成独立段落
4. **段落数量过多** - 575 段 vs 7 段

## 解决方案

```
AI 生成 Markdown → Pandoc 专业转换 → 标准 Word 文档
```

**优势**：
- AI 只需生成标准 Markdown，简单可靠
- Pandoc 是专业的文档转换工具，表格处理完美
- 生成的 Word 文档符合标准格式

## 测试验证

```python
from docx import Document

# 使用 Markdown + Pandoc 生成的文档
doc = Document('output.docx')
print(f"段落数: {len(doc.paragraphs)}")  # 输出: 7
print(f"表格数: {len(doc.tables)}")      # 输出: 1

# 直接操作生成的文档
doc = Document('bad.docx')
print(f"段落数: {len(doc.paragraphs)}")  # 输出: 575
print(f"表格数: {len(doc.tables)}")      # 输出: 0
```

## 结论

**始终使用 Markdown + Pandoc 流程**，避免直接操作 Word。

这是用户明确要求的工作流程，必须遵守。
