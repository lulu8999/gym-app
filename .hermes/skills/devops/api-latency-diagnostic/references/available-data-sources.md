# 国内可用数据源（VPS 直连，无需代理）

## 腾讯财经
- **大盘指数**: `https://qt.gtimg.cn/q=sh000001,sz399001,sz399006`
  - 返回格式: `var hq_str_sh000001="...~名称~代码~价格~...~涨跌幅~..."`
  - 字段用 `~` 分隔，第3个是价格，第5个是涨跌幅
  - 编码: GBK

## 新浪财经
- **全球市场**: `https://hq.sinajs.cn/list=int_dji,int_nasdaq,int_sp500,b_TWSE,b_HSI`
  - 返回: `var hq_str_int_dji="道琼斯,46247.29,299.97,0.65"`
  - 格式: 名称,价格,涨跌额,涨跌幅
  - 需要 Header: `Referer: https://finance.sina.com.cn`
  - 编码: GBK

- **大宗商品**: `https://hq.sinajs.cn/list=hf_GC,hf_SI,hf_CL,hf_NG,hf_HG`
  - 返回: `var hq_str_hf_GC="4351.997,,4353.800,4508.700,..."`
  - 格式: 当前价,(空),开盘,最高,最低,...,昨收,...
  - **涨跌幅需计算**: `(当前价 - 昨收) / 昨收 × 100`（昨收在 vals[7]）
  - 需要 Header: `Referer: https://finance.sina.com.cn`
  - 编码: GBK

## akshare（不稳定）
- VPS 直连经常 `RemoteDisconnected`，适合做备用源
- 部分接口可用（行业板块、权威数据），部分不可用（指数实时行情偶尔失败）
- 超时设为 300s，加重试逻辑

## 东方财富
- push2.eastmoney.com API 从 VPS 直连被拒（RemoteDisconnected）
- datacenter-web.eastmoney.com 部分可用（融资融券等）
- 建议用新浪/腾讯替代

## 注意事项
- 新浪 API 需要 `Referer` Header，否则返回空
- 所有 API 返回 GBK 编码，Python 需 `.decode('gbk')`
- 代理可用时（mihomo），可访问被墙的数据源
