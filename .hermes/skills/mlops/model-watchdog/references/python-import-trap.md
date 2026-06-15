# Python 导入陷阱：`__import__('urllib.request')`  

## 症状

```python
__import__('urllib.request')
req = urllib.request.Request(url, ...)
```
→ `AttributeError: module 'urllib' has no attribute 'Request'`

## 原因

`__import__('urllib.request')` 返回的是**顶层 `urllib` 模块**，不是 `urllib.request` 子模块。  
Python 文档中 `__import__` 的语义：对点分隔的模块名，返回最左侧的包。

## 修复

```python
# 正确方案 1：顶层 import
import urllib.request
req = urllib.request.Request(url, ...)

# 正确方案 2：from 导入
from urllib.request import Request, urlopen
req = Request(url, ...)

# 错误方案（不工作）：
__import__('urllib.request').Request  # AttributeError
```

## 为什么会在看门狗脚本中出现

初始版本为了"零依赖"（只 import stdlib），用了 `__import__` 动态导入。但 `urllib` vs `urllib.request` 的嵌套模块导入行为不一样。改成顶层 `import urllib.request` 后修复。

## 教训

`__import__` 在动态导入**子模块**时行为反直觉。除非你真的需要动态导入（不知道模块名直到运行时），否则用普通 `import`。
