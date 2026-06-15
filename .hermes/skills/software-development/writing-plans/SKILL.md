---
name: writing-plans
description: "Write implementation plans: bite-sized tasks, paths, code."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, design, implementation, workflow, documentation]
    related_skills: [subagent-driven-development, test-driven-development, requesting-code-review]
---

# Writing Implementation Plans

## Overview

Write comprehensive implementation plans assuming the implementer has zero context for the codebase and questionable taste. Document everything they need: which files to touch, complete code, testing commands, docs to check, how to verify. Give them bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the implementer is a skilled developer but knows almost nothing about the toolset or problem domain. Assume they don't know good test design very well.

**Core principle:** A good plan makes implementation obvious. If someone has to guess, the plan is incomplete.

## When to Use

**Always use before:**
- Implementing multi-step features
- Breaking down complex requirements
- Delegating to subagents via subagent-driven-development

**Don't skip when:**
- Feature seems simple (assumptions cause bugs)
- You plan to implement it yourself (future you needs guidance)
- Working alone (documentation matters)

## Bite-Sized Task Granularity

**Each task = 2-5 minutes of focused work.**

Every step is one action:
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step

**Too big:**
```markdown
### Task 1: Build authentication system
[50 lines of code across 5 files]
```

**Right size:**
```markdown
### Task 1: Create User model with email field
[10 lines, 1 file]

### Task 2: Add password hash field to User
[8 lines, 1 file]

### Task 3: Create password hashing utility
[15 lines, 1 file]
```

## ⚠️ User Preference: Phase-Level vs Task-Level Granularity

The default "bite-sized tasks (2-5 min)" works great for **pure software implementation**, but some tasks — especially **exploratory, hardware, security-research, or reverse-engineering** tasks — demand a different format.

**Real example from this user:**  
I wrote a 6-step granular plan for BLE door lock probing. The user compressed it instantly:
> "意思就是先做一个探测程序来检测我的锁，然后抓包回来分析，再写程序"

That's 6 steps → 4 phases. The user was right — it's clearer.

### How to decide which format to use

| Task type | Granularity | Example |
|:----|:----:|:----|
| Software implementation (standard coding) | **Bite-sized tasks** ✅ | ①Write failing test ②Implement ③Pass test ④Commit |
| Exploratory/Research/Hardware/Security | **Phase-level grouping** ✅ | ①探测扫描 ②抓包分析 ③写控制程序 |
| Mixed (software + uncertainty) | Start **phase-level**, expand per-phase | "Phase 1: Research protocol → if clear, write code" |

### Telltale signs a user wants phase-level plans

- They ask "先给我个plan" — they want the big picture first
- They compress your granular plan into fewer steps ("意思就是先X再Y" == "bundle my steps")
- They nod at phases but skip over micro-details

### When phase-level, each step looks like:

```markdown
### Phase 1: [Descriptive Name]

**Goal:** What this phase accomplishes (one sentence)

**Why:** Why it's a separate phase / what we'll learn

**Approach:** High-level method (1-2 sentences)

**Deliverable:** What exists after this phase

**Sub-steps (for execution reference, not for user-facing plan):**
- Detail 1
- Detail 2
- Detail 3
```

The key difference: phases state **what you'll figure out**, tasks state **what you'll build**. Research phases produce knowledge; implementation tasks produce code.

## Plan Document Structure

### Header (Required)

Every plan MUST start with:

```markdown
# [Feature Name] Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

### 架构师模式（需求分析框架）

在开始写计划之前，如果需求不够清晰，使用以下框架进行需求分析：

**角色设定：** 你现在是一个资深系统架构师，请先不要写代码。

**8个分析维度：**
1. 这个需求真正要解决的问题是什么？
2. 它的核心用户是谁？
3. 最小可行版本 MVP 应该包含哪些功能？
4. 哪些功能现在不该做，容易浪费时间？
5. 这个系统可能有哪些技术风险？
6. 数据结构、接口、前端、后端应该怎么拆？
7. 给我3套实现方案：
   - 最快上线版
   - 稳定可扩展版
   - 低成本个人开发版
8. 每套方案说明：
   - 优点
   - 缺点
   - 开发周期
   - 适合什么场景

**最终输出：** 给我一个推荐方案，并说明为什么。

**设计逻辑：** 这个框架的核心是"先分析需求再动手"，避免直接进入细节实现，确保方向正确。通过多方案对比，让用户做出明智选择。

**来源：** 霖贝塔AI日记分享的9个实用提示词（2026-06-14）

### 产品经理模式（需求验证框架）

当用户提出一个产品想法时，使用以下框架验证需求：

**角色设定：** 你现在是一个经验丰富的产品经理。

**10个关键问题（必须覆盖）：**
1. 目标用户是谁？
2. 用户现在用什么方式解决这个问题？
3. 这个问题是否高频？
4. 这个问题是否足够痛？
5. 用户是否愿意付费？
6. 现有竞品是谁？
7. 我的差异化在哪里？
8. 第一个版本应该只做什么？
9. 哪些功能现在绝对不要做？
10. 怎么用最低成本验证需求？

**回答完后整理成：**
- 产品定位
- 用户画像
- 核心卖点
- MVP 功能列表
- 7 天验证计划

**设计逻辑：** 这个框架的核心是"先验证需求再动手"，通过苏格拉底式引导，挖掘深层信息，避免浪费时间做不值得的项目。

**来源：** 霖贝塔AI日记分享的9个实用提示词（2026-06-14）

### 老板视角模式（项目评估框架）

当需要判断一个项目、工具、网站到底值不值得做时，使用以下框架：

**角色设定：** 你现在不是程序员，也不是产品经理，你现在是一个只关心现金流、投入产出比和风险控制的老板。

**分析维度：**
- 现金流：这个项目能带来多少收入？需要多少投入？
- 投入产出比：ROI是多少？多久能回本？
- 风险控制：有哪些风险？如何规避？

**设计逻辑：** 这个框架的核心是"从商业角度评估项目价值"，避免技术思维陷阱，确保项目有商业可行性。

**来源：** 霖贝塔AI日记分享的9个实用提示词（2026-06-14）

### 增长顾问模式（内容增长框架）

当需要做短视频、网站流量、AI工具推广时，使用以下框架：

**角色设定：** 你现在是一个增长顾问。

**10个拆解维度：**
1. 目标用户是谁？
2. 用户为什么会关注我？
3. 我的内容钩子是什么？
4. 哪些话题最容易带来转发？
5. 哪些内容最容易带来收藏？
6. 哪些内容最容易带来评论？
7. 我应该模仿哪些账号？
8. 每天应该发什么类型内容？
9. 7天内怎么测试方向是否有效？
10. 30天内如何形成稳定内容资产？

**最终输出：**
- 账号定位一句话
- 3个爆款选题
- 5条推文标题
- 7天内容计划
- 一个可执行的涨粉闭环

**设计逻辑：** 这个框架的核心是"从增长角度拆解内容策略"，通过用户洞察、内容策略、竞品分析、测试迭代、长期资产构建的完整链条，确保内容有增长潜力。

**来源：** 霖贝塔AI日记分享的9个实用提示词（2026-06-14）

### Task Structure

Each task follows this format:

````markdown
### Task N: [Descriptive Name]

**Objective:** What this task accomplishes (one sentence)

**Files:**
- Create: `exact/path/to/new_file.py`
- Modify: `exact/path/to/existing.py:45-67` (line numbers if known)
- Test: `tests/path/to/test_file.py`

**Step 1: Write failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify failure**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: FAIL — "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify pass**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Writing Process

### Step 1: Understand Requirements

Read and understand:
- Feature requirements
- Design documents or user description
- Acceptance criteria
- Constraints

### Step 2: Explore the Codebase

Use Hermes tools to understand the project:

```python
# Understand project structure
search_files("*.py", target="files", path="src/")

# Look at similar features
search_files("similar_pattern", path="src/", file_glob="*.py")

# Check existing tests
search_files("*.py", target="files", path="tests/")

# Read key files
read_file("src/app.py")
```

### Step 3: Design Approach

Decide:
- Architecture pattern
- File organization
- Dependencies needed
- Testing strategy

### Step 4: Write Tasks

Create tasks in order:
1. Setup/infrastructure
2. Core functionality (TDD for each)
3. Edge cases
4. Integration
5. Cleanup/documentation

### Step 5: Add Complete Details

For each task, include:
- **Exact file paths** (not "the config file" but `src/config/settings.py`)
- **Complete code examples** (not "add validation" but the actual code)
- **Exact commands** with expected output
- **Verification steps** that prove the task works

### Step 6: Add Pros and Cons Section

**Required for all plans** - after the task list, add a "Pros and Cons" section:

```markdown
## 优缺点分析

### 优点
- ✅ [Benefit 1]
- ✅ [Benefit 2]
- ✅ [Benefit 3]

### 缺点
- ❌ [Drawback 1]
- ❌ [Drawback 2]
- ❌ [Drawback 3]
```

**Why this matters:** Users explicitly want to see trade-offs before committing to a solution. This helps them make informed decisions and reduces back-and-forth clarifications.

**Example from real session:**
- User asked: "你列个plan我看看，把优缺点都发给我"
- Response included: 优缺点分析表格 with ✅/❌ indicators
- Result: User could quickly evaluate and approve the plan

### Step 6: Review the Plan

Check:
- [ ] Tasks are sequential and logical
- [ ] Each task is bite-sized (2-5 min)
- [ ] File paths are exact
- [ ] Code examples are complete (copy-pasteable)
- [ ] Commands are exact with expected output
- [ ] No missing context
- [ ] DRY, YAGNI, TDD principles applied

### Step 7: Save the Plan

```bash
mkdir -p docs/plans
# Save plan to docs/plans/YYYY-MM-DD-feature-name.md
git add docs/plans/
git commit -m "docs: add implementation plan for [feature]"
```

## Principles

### DRY (Don't Repeat Yourself)

**Bad:** Copy-paste validation in 3 places
**Good:** Extract validation function, use everywhere

### YAGNI (You Aren't Gonna Need It)

**Bad:** Add "flexibility" for future requirements
**Good:** Implement only what's needed now

```python
# Bad — YAGNI violation
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.preferences = {}  # Not needed yet!
        self.metadata = {}     # Not needed yet!

# Good — YAGNI
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
```

### TDD (Test-Driven Development)

Every task that produces code should include the full TDD cycle:
1. Write failing test
2. Run to verify failure
3. Write minimal code
4. Run to verify pass

See `test-driven-development` skill for details.

### Frequent Commits

Commit after every task:
```bash
git add [files]
git commit -m "type: description"
```

## Common Mistakes

### Vague Tasks

**Bad:** "Add authentication"
**Good:** "Create User model with email and password_hash fields"

### Incomplete Code

**Bad:** "Step 1: Add validation function"
**Good:** "Step 1: Add validation function" followed by the complete function code

### Missing Verification

**Bad:** "Step 3: Test it works"
**Good:** "Step 3: Run `pytest tests/test_auth.py -v`, expected: 3 passed"

### Missing File Paths

**Bad:** "Create the model file"
**Good:** "Create: `src/models/user.py`"

## Execution Handoff

After saving the plan, offer the execution approach:

**"Plan complete and saved. Ready to execute using subagent-driven-development — I'll dispatch a fresh subagent per task with two-stage review (spec compliance then code quality). Shall I proceed?"**

When executing, use the `subagent-driven-development` skill:
- Fresh `delegate_task` per task with full context
- Spec compliance review after each task
- Code quality review after spec passes
- Proceed only when both reviews approve

## Remember

```
Bite-sized tasks (2-5 min each)
Exact file paths
Complete code (copy-pasteable)
Exact commands with expected output
Verification steps
DRY, YAGNI, TDD
Frequent commits
```

**A good plan makes implementation obvious.**
