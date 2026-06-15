# 中文 AI 模型提供商公司对照表

避免误删/误改不同公司的 provider。⚠️ 核心教训：**名称相似的 provider 可能属于不同公司。**

## 公司 - Provider 映射

| 公司 | 品牌/平台 | Provider 名称 | 备注 |
|------|-----------|---------------|------|
| **百度** | 千帆 (Qianfan) | `qianfan` | 文心一言系列模型。`base_url: https://qianfan.baidubce.com/v2/coding` |
| **阿里巴巴** | 阿里云百炼 (DashScope) | `dashscope` | 通义千问 (Qwen) 系列模型。`DASHSCOPE_API_KEY` |
| **小米** | 小米 MiMo | `xiaomi-mimo` | MoE 模型 mimo-v2.5 |
| **月之暗面** | Kimi / Moonshot | `kimi` 或 `kimi-coding` | 长上下文模型 |
| **DeepSeek** | DeepSeek | `deepseek` | 推理模型 v4 |
| **字节跳动** | 火山引擎 / 豆包 | `doubao` / `ark` | — |
| **智谱** | 智谱AI (Zhipu) | `zhipu` / `glm` | GLM系列 |
| **腾讯** | 混元 | `hunyuan` | — |
| **华为** | 盘古 | `pangu` | — |
| **商汤** | 日日新 | `sensechat` | — |
| **MiniMax** | MiniMax | `minimax` | — |
| **零一万物** | Yi | `yi` | — |
| **百川智能** | Baichuan | `baichuan` | — |

## 容易混淆的

| 容易混淆的 | 实际所属 | 陷阱 |
|------------|----------|------|
| `qianfan`（千帆）↔ 阿里巴巴 | **百度** | 名字是中文自然语义，不是公司名。千帆 = 百度 |
| `qwen`（通义千问）↔ 任何名字带"通义"的 | **阿里巴巴** | qwen = 阿里系 |
| `glm` / `chatglm` | **智谱AI** | 非清华官方，是智谱 |
| `yi` / `yi-34b` | **零一万物**（李开复） | 非阿里/百度 |

## 删除原则

用户说"删掉XX的API"时：
1. 先确认XX指的是**公司名**还是**品牌名**
2. 如果是公司名（如"阿里巴巴"），精确找到该公司的 provider 再删
3. **不要仅凭名称相似度下判断** — qianfan（千帆）听起来像阿里系，实际是百度
4. 如果有疑问，先列出相关 provider 让用户确认再执行
