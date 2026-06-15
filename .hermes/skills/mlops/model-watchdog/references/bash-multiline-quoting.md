# Bash 多行 curl 引号陷阱

## 症状

Bash 脚本中多行 curl 命令：
```bash
http_code=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer *** \
    --connect-timeout 5 --max-time 8 "$url" 2>/dev/null | tail -1)
```
→ `unexpected EOF while looking for matching '"'`

## 原因

`"Authorization: Bearer $api_key \` 中：
- 最后一个 `\` 是**行连续符**（escape newline），不是引号转义
- `$api_key` 后的 `"` 本意是关闭字符串，但由于 `\` 的存在，bash 认为 `\"` 是转义的双引号字符（不关闭字符串！）
- 结果这个 `"` 是**字面量**而不是字符串结束符
- 后续整个命令都在未关闭的字符串内，直到 EOF

## 关键区分

| 写法 | 含义 |
|------|------|
| `"abc\"` | 字符串 `abc"` —— `\"` 是转义的双引号字符，不关闭字符串 |
| `"abc" \` | 字符串 `abc`，加行连续符 |
| `"abc"` | 正常关闭的字符串 |

## 修复

```bash
# ❌ 错误：行尾 \" 不关闭字符串
    -H "Authorization: Bearer *** \

# ✅ 正确：先关闭引号，再行连续
    -H "Authorization: Bearer ***" \
```

## 通用规则

- 行连续符 `\` 让下一行**以文本方式**拼接到当前行，引号跨度也一同拼接
- `\"` 在双引号内是字面量 `"`，不结束字符串
- 行连续时，`"` 必须在本行内显式闭合，`"xxx\"` 是**未闭合**的
- 替代方案：Python 多行字符串比 bash 连续行安全得多
