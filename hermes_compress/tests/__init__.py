#!/usr/bin/env python3
"""
Hermes Compress 测试用例
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes_compress import compress, OutputCompressor

def test_git_status():
    """测试git status压缩"""
    input_text = """On branch main
Your branch is up to date with 'origin/main'.

Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
	modified:   .claude/CLAUDE.md

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   .bashrc

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	.bash_logout
	.bash_profile
	hermes-compress.py"""
    
    result = compress(input_text, cmd_type="git-status")
    assert "On branch main" in result
    assert "Staged (1)" in result
    assert "Unstaged (1)" in result
    assert "Untracked (3)" in result
    print("✅ git status 压缩测试通过")

def test_git_diff():
    """测试git diff压缩"""
    input_text = """diff --git a/.claude/CLAUDE.md b/.claude/CLAUDE.md
index 1234567..abcdefg 100644
--- a/.claude/CLAUDE.md
+++ b/.claude/CLAUDE.md
@@ -37,3 +37,8 @@
+- RTK 代理已启用
+- 使用 `rtk gain` 查看节省统计
+
+@RTK.md"""
    
    result = compress(input_text, cmd_type="git-diff")
    assert "1 files changed" in result
    assert ".claude/CLAUDE.md" in result
    print("✅ git diff 压缩测试通过")

def test_env():
    """测试env压缩"""
    input_text = """PATH=/usr/local/bin:/usr/bin:/bin
HOME=/root
USER=root
SECRET_TOKEN=abc123
PYTHON_VERSION=3.11
DOCKER_HOST=unix:///run/podman/podman.sock"""
    
    result = compress(input_text, cmd_type="env")
    assert "SECRET_TOKEN=***" in result  # 敏感变量被过滤
    assert "PATH" in result
    print("✅ env 压缩测试通过")

def test_grep():
    """测试grep压缩"""
    input_text = """file1.py:10:import os
file1.py:15:import sys
file2.py:5:import json
file2.py:20:import re"""
    
    result = compress(input_text, cmd_type="grep")
    assert "file1.py (2 matches)" in result
    assert "file2.py (2 matches)" in result
    print("✅ grep 压缩测试通过")

def test_find():
    """测试find压缩"""
    input_text = """./src/main.py
./src/utils.py
./src/config.py
./test/test_main.py
./test/test_utils.py"""
    
    result = compress(input_text, cmd_type="find")
    assert "./src/ (3 files)" in result
    assert "./test/ (2 files)" in result
    print("✅ find 压缩测试通过")

def test_log():
    """测试日志压缩"""
    input_text = """2026-06-15 10:00:00 INFO Starting service
2026-06-15 10:00:01 INFO Loading config
2026-06-15 10:00:02 ERROR Connection failed
2026-06-15 10:00:03 WARN Retrying...
2026-06-15 10:00:04 INFO Connected"""
    
    result = compress(input_text, cmd_type="log")
    assert "Log levels:" in result
    assert "ERROR: 1" in result
    assert "WARN: 1" in result
    print("✅ log 压缩测试通过")

def test_auto_detect():
    """测试自动检测"""
    # git status
    result1 = compress("On branch main\nnothing to commit")
    assert "On branch main" in result1
    
    # env
    result2 = compress("PATH=/usr/bin\nHOME=/root")
    assert "PATH" in result2
    
    print("✅ 自动检测测试通过")

def test_empty_input():
    """测试空输入"""
    result1 = compress("")
    assert result1 == ""
    
    result2 = compress("   \n  \n  ")
    assert result2.strip() == ""
    
    print("✅ 空输入测试通过")

def test_long_lines():
    """测试长行截断"""
    long_line = "x" * 300
    result = compress(long_line, cmd_type="generic")
    assert len(result) <= 203  # 200 + "..."
    print("✅ 长行截断测试通过")

def test_compression_ratio():
    """测试压缩率"""
    # 模拟git status输出
    lines = ["On branch main"]
    lines.extend([f"?? file{i}.py" for i in range(100)])
    input_text = "\n".join(lines)
    
    result = compress(input_text, cmd_type="git-status")
    original_lines = len(input_text.split('\n'))
    compressed_lines = len(result.split('\n'))
    
    compression_ratio = (1 - compressed_lines / original_lines) * 100
    assert compression_ratio > 80  # 压缩率应该大于80%
    print(f"✅ 压缩率测试通过: {compression_ratio:.1f}%")

def test_real_world():
    """真实世界测试"""
    # 测试实际的git status
    import subprocess
    try:
        result = subprocess.run(['git', 'status'], capture_output=True, text=True, cwd='/root')
        if result.returncode == 0:
            compressed = compress(result.stdout, cmd_type="git-status")
            original_lines = len(result.stdout.split('\n'))
            compressed_lines = len(compressed.split('\n'))
            ratio = (1 - compressed_lines / original_lines) * 100 if original_lines > 0 else 0
            print(f"✅ 真实git status测试: {original_lines}行 → {compressed_lines}行 (压缩率{ratio:.1f}%)")
    except Exception as e:
        print(f"⚠️ 真实git status测试跳过: {e}")

def main():
    """运行所有测试"""
    print("=== Hermes Compress 测试 ===\n")
    
    tests = [
        test_git_status,
        test_git_diff,
        test_env,
        test_grep,
        test_find,
        test_log,
        test_auto_detect,
        test_empty_input,
        test_long_lines,
        test_compression_ratio,
        test_real_world,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} 错误: {e}")
            failed += 1
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️ 有测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())