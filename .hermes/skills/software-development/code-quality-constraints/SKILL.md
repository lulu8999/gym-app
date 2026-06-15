---
name: code-quality-constraints
category: software-development
description: 代码质量约束——禁止行为、代码审查标准、命名规范、错误处理规范、性能考虑
tags: [code-quality, best-practices, development]
version: 1.0.0
---

# 代码质量约束

## 一、禁止行为

- ❌ 不写兼容性代码（除非用户明确要求）
- ❌ 不在原有代码上加 if 分支来"修复"问题
- ❌ 不添加不必要的错误处理
- ❌ 不过度抽象
- ❌ 不创建"以防万一"的功能
- ❌ 不写死循环或无限递归
- ❌ 不硬编码敏感信息

## 二、应该做的

- ✅ 直接修改问题代码
- ✅ 保持代码简洁
- ✅ 只实现当前需求
- ✅ 删除无用代码
- ✅ 优先简单方案
- ✅ 写完后检查语法错误

## 三、代码审查标准

每次写完代码，必须过一遍以下检查清单：

### 安全检查（必须）
- [ ] 有无 SQL 注入风险？
- [ ] 有无 XSS 漏洞？
- [ ] 敏感信息是否硬编码？
- [ ] 文件路径是否有目录遍历风险？
- [ ] 用户输入是否做了校验和过滤？
- [ ] API Key / 密码等是否在代码中暴露？

### 可读性检查（必须）
- [ ] 变量名是否清晰易懂？
- [ ] 函数是否超过 50 行？（超过应拆分）
- [ ] 是否有不必要的嵌套？
- [ ] 关键逻辑是否有注释？
- [ ] 代码缩进和格式是否一致？

### 功能完整性检查（必须）
- [ ] 是否覆盖了所有边界情况？
- [ ] 返回值是否一致？
- [ ] 错误处理是否完善？
- [ ] 输入校验是否完整？
- [ ] 是否处理了空值/None？

### 可维护性检查（建议）
- [ ] 是否有重复代码可以提取？
- [ ] 是否有硬编码的配置可以抽成常量？
- [ ] 函数职责是否单一？
- [ ] 是否便于单元测试？

### 代码审计模式（深度检查）

当需要深度审查代码时（如审查他人代码、AI生成代码、或关键项目代码），使用以下10维度检查框架：

**角色设定：** 你现在是一个资深代码审计专家，请以非常严格的标准检查代码。

**10个检查维度：**
1. 是否有隐藏bug？
2. 是否有边界条件没处理？
3. 是否可能出现性能问题？
4. 是否有安全风险？
5. 是否有硬编码密钥、Token、密码？
6. 是否有重复代码？
7. 是否有不容易维护的设计？
8. 是否有未来扩展时会踩坑的地方？
9. 是否有异常处理不完整的问题？
10. 是否有日志、错误提示不清晰的问题？

**输出格式：**
- 最危险的问题：
- 可能导致的后果：
- 具体出问题的位置：
- 推荐修改方式：
- 修改后的代码示例：

**约束：** 如果代码整体设计不合理，请直接指出，不要为了礼貌而模糊表达。

**来源：** 霖贝塔AI日记分享的9个实用提示词（2026-06-14）

## 四、命名规范

### 变量命名
- 布尔值：`is_`、`has_`、`can_` 前缀，如 `is_valid`、`has_permission`
- 列表：复数形式，如 `users`、`items`
- 字典：单数形式，如 `config`、`user_info`
- 常量：全大写，如 `MAX_RETRY_COUNT`、`API_TIMEOUT`

### 函数命名
- 动词开头，如 `get_user()`、`create_order()`、`validate_input()`
- 查询类：`find_`、`search_`、`query_`
- 判断类：`is_`、`has_`、`can_`
- 更新类：`update_`、`set_`、`modify_`
- 删除类：`delete_`、`remove_`

### 类命名
- 大驼峰，如 `UserService`、`OrderManager`
- 避免缩写，用 `Application` 不用 `App`
- 接口类：`I` 前缀或 `Interface` 后缀（如 `IRepository` 或 `RepositoryInterface`）

### 文件命名
- Python：小写下划线，如 `user_service.py`
- JS/TS：小写横线，如 `user-service.ts`
- 测试文件：`test_` 前缀或 `.test.` 后缀
- 配置文件：`.config.` 后缀

### API/URL 命名
- RESTful：复数名词 + 动词，如 `GET /users`、`POST /orders`
- 驼峰：用于 JSON 字段，如 `userName`、`orderTime`
- 下划线：用于 URL 参数，如 `user_name`、`order_time`

## 五、错误处理规范

### 什么时候该加 try/catch
- ✅ 文件读写操作
- ✅ 网络请求
- ✅ 用户输入解析
- ✅ 外部 API 调用
- ✅ 数据库操作
- ✅ JSON 解析
- ❌ 简单变量赋值（不需要）
- ❌ 纯计算逻辑（不需要）
- ❌ 已经有类型校验的操作（不需要）

### 错误处理原则
1. **捕获具体异常**，不要 `except Exception`
   - Python：`except FileNotFoundError:`、`except ValueError:`
   - JS/TS：`catch (e instanceof TypeError)`
2. **记录有意义的错误信息**，包含上下文
3. **向上层报告错误**，不要静默吞掉
4. **用户可见错误要友好提示**，不要暴露技术细节
5. **资源清理**：用 finally / with 确保释放

### 异常处理模板

```python
# Python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"操作失败: {e}")
    return {"success": False, "error": str(e)}
finally:
    cleanup()
```

```typescript
// TypeScript
try {
  const result = await riskyOperation();
} catch (e) {
  if (e instanceof SpecificError) {
    console.error('操作失败:', e.message);
    return { success: false, error: e.message };
  }
  throw e; // 未知异常继续抛出
}
```

### 日志规范
- DEBUG：开发调试信息
- INFO：正常流程记录
- WARN：警告但不影响运行
- ERROR：错误但程序可继续
- FATAL：致命错误，程序退出

## 六、性能考虑

### 什么时候需要优化
- 循环超过 10000 次
- 数据库查询超过 1000 条
- 文件超过 100MB
- 用户反馈响应慢
- 内存占用持续增长
- CPU 使用率持续 >80%

### 优化原则
1. **先确保正确，再优化性能**
2. **用 profiling 找瓶颈**，不要凭感觉优化
3. **优先算法优化**，其次缓存，最后并发
4. **过早优化是万恶之源**
5. **优化要有数据支撑**，不要"感觉快了"

### 常见优化手段

#### 数据库
- 加索引（WHERE、JOIN、ORDER BY 的字段）
- 分页查询（LIMIT/OFFSET 或游标分页）
- 批量操作（INSERT/UPDATE 批量执行）
- 避免 SELECT *，只查需要的字段
- 使用连接池

#### 文件 I/O
- 流式处理（不要一次性读取整个文件）
- 分块读取（大文件分块处理）
- 异步 I/O（不阻塞主线程）
- 缓存常用文件

#### 计算
- 缓存结果（memoize）
- 减少重复计算（避免循环内重复调用）
- 延迟计算（lazy evaluation）
- 并行处理（多线程/多进程）

#### 网络
- 减少请求次数（批量请求）
- 压缩数据（gzip）
- 设置超时（避免长时间等待）
- 重试机制（指数退避）

### 性能测试工具
- Python：cProfile、line_profiler、memory_profiler
- JS/TS：console.time()、Chrome DevTools
- 数据库：EXPLAIN 分析查询计划
