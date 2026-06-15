---
name: chinese-kaoyan-medical-prep
description: Assisting with Chinese medical postgraduate entrance exam preparation (西医综合306), including material organization, chapter analysis, and exam point prediction based on historical patterns.
author: Assistant
category: education
---

# Chinese Medical Postgraduate Exam Prep (306 Western Medicine)

Assisting users (or their friends/family like "师傅") preparing for the 306 Western Medicine Comprehensive (西医综合) postgraduate entrance examination.

## Key Domain Knowledge

- **Exam Structure**: 306西医综合 includes Physiology (生理学), Biochemistry (生物化学), Pathology (病理学), Internal Medicine (内科学,含诊断), Surgery (外科学,含总论).
- **Question Types**: A-type (best choice, 16 questions), B-type (matching, 4 questions), X-type (multiple multiple-choice, 6 questions) for Physiology specifically (42 points total).
- **Data Limitations**: Official past papers are NOT publicly available. Only "recall versions" (回忆版) collected by apps like 医考帮 or trainers like 贺银成/天天师兄 exist.
- **Current Edition**: As of 2026, the 10th edition (第十版) of People's Medical Publishing House (人卫) textbooks are the standard.
- **Key Chapters by Weight** (Physiology): Circulation (血液循环) > Nervous System (神经系统) > Endocrine (内分泌) > Cell Function (细胞功能) > Respiration (呼吸) > Urinary (泌尿).

## Workflow

1. **Clarify Scope**: Confirm exam type (306 vs. independent命题), target year (e.g., 2027考研), textbook edition, and target school (if relevant for independent命题).
2. **Material Intake**: If user provides PDFs (讲义, textbooks, slides):
   - Use `pdftotext` to extract text from large PDFs (may be 50MB+).
   - Store extracted text in `/tmp/` for analysis.
3. **Data Strategy**:
   - **DO NOT** attempt to scrape 医考帮, 蓝基因, or other commercial APPs (anti-crawl, encryption, mobile-only, legal risk).
   - **DO** analyze user-provided materials and public domain analysis to build:
     - Chapter score distribution tables (章节分值分布表).
     - High-frequency topic lists (高频考点清单) based on repetition 3+ times.
     - Yearly predictions (重点预测) based on trends.
     - Common pitfalls lists (易错点速查表) extracted from "易错小结" sections.
4. **Reporting Style**: User prefers **step-by-step reporting** (干一步报告一步). Report completion of each intermediate file/table before proceeding to the next. Do not batch everything into one final delivery.
5. **Review Checkpoint**: User prefers to **review intermediate outputs** ("做好了先发给我看看") before final compilation. Pause and wait for confirmation after each major deliverable.

## Output Structure

Create organized markdown files in the user's designated directory (e.g., `/root/users-data/[User]/生理考研资料/`):
- `章节分值分布表.md` - Historical score weight by chapter (2006-2025).
- `高频考点清单.md` - Topics appearing frequently in past exams.
- `2027重点预测.md` - Predicted focus areas based on trends (e.g., Starling机制, EPSP/IPSP for 2027).
- `易错点速查表.md` - Common pitfalls extracted from materials (口诀, 混淆点).

## Tools & Techniques

- **PDF Processing**: `pdftotext` (from poppler-utils package) for text extraction when standard file reading fails or for large files (49MB+).
- **Analysis**: Pattern matching for chapter headings, keyword frequency analysis for importance weighting.
- **Constraints**: Respect copyright; do not reproduce full proprietary question banks. Use analysis and summary only.

## Common High-Frequency Topics (Physiology)

Must-knows for prediction:
- Circulation: Starling mechanism (Starling机制), Cardiac pump regulation (前负荷-异长调节), Myocardial electrophysiology (心肌电生理-自律性).
- Nervous System: EPSP vs IPSP, Specific vs Non-specific projection systems (特异/非特异投射系统), Neurotransmitters (Ach/NE/GABA).
- Endocrine: Insulin/Glucagon, Thyroid hormones, Glucocorticoids (糖皮质激素), Calcium regulation.

## Pitfalls

- Do not confuse "recall version" (回忆版) with official questions when citing sources.
- Do not attempt to provide exact original question text (copyright risk); provide summaries and analysis instead.
- When user says "抓包试试看", explain the technical and legal barriers clearly, then pivot to the analysis-based approach.