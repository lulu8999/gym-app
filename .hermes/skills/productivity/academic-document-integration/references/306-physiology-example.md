# Example: 306 Physiology Exam Prep Guide

## Session Context
- **User**: Lulu (helping master prepare for exam)
- **Source material**: 天天师兄 core lecture notes (16,863 lines, 49MB PDF)
- **Output**: Unified 17-page study guide with exam predictions

## Document Structure Used

### 1. Front Matter
```markdown
# 306西医综合 · 生理学考研复习资料（整合版）
> 适用：2027考研（人卫第10版教材）  
> 来源：天天师兄核心精讲 + 历年真题规律  
> 目标：南通大学医学院
```

### 2. Historical Analysis Section
- 20-year chapter weight distribution table
- Question type breakdown (A/B/X型题)
- Difficulty classification per chapter

### 3. Prediction Tiers
**Tier 1 (Must-know)**: Cardiac electrophysiology, pump function, synaptic transmission
**Tier 2 (High-frequency)**: Signal transduction, transmembrane transport, endocrine
**Tier 3 (Understanding)**: Digestion, reproduction, sensory organs

### 4. Chapter Sections
Each followed pattern:
- Core concepts with mnemonics (口诀)
- Comparison tables for similar concepts
- Pitfall highlights (易错点)

### 5. Quick Reference
- Mnemonic index table (10+ entries)
- Common mistakes by chapter
- Answer techniques by question type

## Technical Implementation

### PDF Generation Pipeline
```python
# Tools: markdown + weasyprint
import markdown
from weasyprint import HTML

html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
# Added Chinese font CSS
HTML(string=html).write_pdf(pdf_path)
```

### File Outputs
- Markdown source (31.9 KB) - editable
- PDF (685.8 KB, ~17 pages) - printable
- Both delivered to user

## User Preferences Observed
- Required step-by-step reporting (做一步报告一步)
- Valued comprehensive integration over brevity
- Preferred receiving both formats
- Wanted cleanup offered after confirmation

## Key Mnemonics Preserved
- 组织要我机灵些 (体液分布)
- 快准短 (神经调节特点)
- 嗷嗷待串 (自身调节例子)
- 四排一凝胃胰动恶魔 (正反馈例子)
- 快钠慢钙 (心肌细胞)
- 前负荷看Starling (心输出量调节)
- 右移释放氧 (氧解离曲线)
- 兴奋钠进，抑制氯进 (突触传递)
- 快A慢C，快定位慢模糊 (痛觉传导)
- 应激追儿，应激追皮 (肾上腺激素)

## Lessons Applied
- Reported after each major step
- Asked format preference before conversion
- Maintained original author attribution
- Offered cleanup of temp files
