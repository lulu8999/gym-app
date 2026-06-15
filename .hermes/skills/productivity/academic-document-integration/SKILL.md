---
title: Academic Document Integration
name: academic-document-integration
description: |
  Integrate scattered academic materials (lecture notes, exam patterns, mnemonics) into 
  unified study guides. Covers content extraction, structural organization, format 
  conversion (Markdown→PDF), and exam-focused summarization.
triggers:
  - 整理考研资料
  - 整合讲义
  - 生成复习资料
  - 转成PDF
  - 合并文档
  - 制作考点汇总
  - academic study guide creation
  - exam prep material organization
  - markdown to pdf conversion
  - 口诀汇总
  - 真题规律整理
---

# Academic Document Integration

## Purpose
Transform fragmented academic materials into structured, exam-ready study guides.

## Core Workflow

### Phase 1: Source Analysis
1. **Identify material types**
   - Lecture notes (讲义) - often verbose, need condensation
   - Historical exam patterns (真题规律) - statistical analysis
   - Mnemonics/memory aids (口诀) - preserve exactly
   - Errata/common mistakes (易错点) - highlight prominently

2. **Extract with structure preservation**
   - Use `read_file` with appropriate limits for large files
   - For PDFs: `pdftotext` or Python extraction
   - Note chapter hierarchy and key relationships

### Phase 2: Content Integration

**Document Architecture (Standard Template):**
```
# [Subject] Exam Prep Guide

## 📊 Historical Exam Pattern Analysis
- Chapter weight distribution table
- Year-by-year trend analysis
- Difficulty classification

## 🎯 Current Year Predictions
- Tier 1 (Must-know topics)
- Tier 2 (High-frequency)
- Tier 3 (Understanding level)

## 📚 Chapter-by-Chapter Core Points
Each chapter includes:
- Key concepts with mnemonics
- Common pitfalls highlighted
- Comparison tables (similar concepts)

## 📝 Quick Reference Tables
- Mnemonic index
- Easy-to-confuse concepts
- Formula/equation summary

## 📅 Study Schedule
- 3-round review plan
- Time allocation by chapter weight
```

### Phase 3: Format Conversion

**Markdown → PDF Pipeline:**

1. **Pre-processing (CRITICAL for Chinese content)**
   ```python
   # Replace emoji with ASCII equivalents - prevents encoding issues
   md_content = md_content.replace('⭐', '*')  # Star emoji to asterisk
   md_content = md_content.replace('🔥', '[HOT]')  # Fire emoji
   md_content = md_content.replace('⚠️', '[!]')  # Warning emoji
   md_content = md_content.replace('📝', '[NOTE]')  # Note emoji
   # Add other emoji replacements as needed
   ```

2. Install tools: `python3 -m pip install markdown weasyprint`

3. Convert MD→HTML with extensions:
   ```python
   import markdown
   html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
   ```

4. Add CSS styling with Chinese font stack:
   ```css
   @page { size: A4; margin: 2cm; }
   body { 
       font-family: "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei", "SimSun", sans-serif;
       font-size: 10.5pt;
       line-height: 1.5;
   }
   table { font-size: 9.5pt; }  /* Tables slightly smaller */
   ```

5. Generate PDF:
   ```python
   from weasyprint import HTML
   HTML(string=html_content).write_pdf(output_path)
   ```

**Font troubleshooting:**
- If characters still garbled, install system fonts: `apt-get install fonts-noto-cjk`
- Check available fonts: `fc-list :lang=zh`
- Emoji-free output is more reliable than emoji-included for weasyprint

### Phase 4: Delivery
- Generate both MD (editable) and PDF (printable) versions
- Report file locations clearly
- Offer cleanup of temporary files

## User Preferences (Embedded)

### Reporting Style
- **CRITICAL**: User prefers "做一步报告一步" (step-by-step reporting)
- After EACH significant action, report:
  - What was completed
  - Current status
  - Next step preview
- Do NOT batch multiple operations silently

### Document Delivery
- Ask preference: MD source vs PDF vs both
- For large documents, warn about size
- Offer to send via available messaging platforms

### Content Organization
- User values comprehensive integration over brevity
- Include all mnemonics/口诀 exactly as provided
- Highlight 易错点 (common mistakes) prominently
- Maintain original author attribution (e.g., "天天师兄版")

## Pitfalls

1. **PDF conversion failures**
   - Check `weasyprint` installation
   - Ensure Chinese font support in CSS
   - Fallback: Generate HTML first, verify rendering

2. **Large file handling**
   - PDFs >50MB may fail to send via messaging
   - Offer split documents or cloud links

3. **Encoding issues**
   - Always use UTF-8 for Chinese text
   - Verify file paths handle Chinese characters

## Verification Checklist
- [ ] All chapters from source material covered?
- [ ] Mnemonics preserved exactly?
- [ ] Exam predictions clearly marked?
- [ ] Both MD and PDF versions generated?
- [ ] File locations reported clearly?
- [ ] Cleanup offered for temp files?

## Related Skills
- `document-editing` - for .docx manipulation
- `powerpoint` - if slides needed
- `ocr-and-documents` - for scanned source materials