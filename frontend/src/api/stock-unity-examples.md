# Stock Unity API 使用示例文档

## 概述

Stock Unity API 是量华量化平台的前端股票数据统一接口，包含58个API函数，覆盖10个业务子模块。所有API都使用统一的错误处理和响应格式。

## 安装与导入

### ES6 模块导入
```javascript
// 导入所有API函数
import stockUnityApi from './api/stock-unity'

// 或者按需导入单个函数
import { getStockInfo, getStockLhbDetailEm } from './api/stock-unity'
```

### CommonJS 导入
```javascript
const stockUnityApi = require('./api/stock-unity')
```

## 统一响应格式

所有API函数返回统一的响应格式：

```javascript
{
  success: boolean,      // 请求是否成功
  data: any,            // 返回的数据
  error: string | null, // 错误信息，成功时为null
  timestamp: string,    // 响应时间戳
  symbol?: string       // 股票代码或标识符（部分接口）
}
```

## API 函数分类

### 1. 股票基本信息模块 (basic/ - 10个函数)
- `getStockInfo(symbol)` - 个股基础信息
- `getStockInfoJson(symbol)` - 个股信息(JSON格式)
- `getStockIndividualBasicInfoXq(symbol)` - 雪球公司概况
- `getAllStockCodes()` - 全市场股票代码
- `getAllStockCodesJson()` - 全市场股票代码(JSON)
- `stockInfoShNameCode()` - 上交所股票列表
- `stockInfoSzNameCode()` - 深交所股票列表
- `stockInfoBjNameCode()` - 北交所股票列表
- `stockInfoShDelist()` - 上交所退市股票
- `stockInfoSzDelist()` - 深交所退市股票

### 2. 股权质押模块 (pledge/ - 4个函数)
- `getStockGpzyProfileEm()` - 股权质押市场概况
- `getStockGpzyPledgeRatioEm(date)` - 指定日期质押比例
- `getStockGpzyIndividualPledgeRatioDetailEm(symbol)` - 个股质押明细
- `getStockGpzyIndustryDataEm()` - 行业质押比例

### 3. 财务报表模块 (financial/ - 6个函数)
- `getStockFinancialReportSina(stock, symbol)` - 新浪财务报表
- `getStockBalanceSheetByYearlyEm(symbol)` - 资产负债表(年度)
- `getStockProfitSheetByReportEm(symbol)` - 利润表(报告期)
- `getStockProfitSheetByYearlyEm(symbol)` - 利润表(年度)
- `getStockCashFlowSheetByReportEm(symbol)` - 现金流量表(报告期)
- `getStockProfitForecastThs(symbol, indicator)` - 盈利预测

### 4. 股东数据模块 (holder/ - 7个函数)
- `getStockAccountStatisticsEm()` - 月度账户统计
- `getStockCommentEm()` - 千股千评
- `getStockCommentDetailScrdFocusEm(symbol)` - 用户关注指数
- `getStockCommentDetailScrdDesireEm(symbol)` - 市场参与意愿
- `getStockZhAGdhs(date)` - 全市场股东户数
- `getStockZhAGdhsDetailEm(symbol)` - 个股股东户数详情

### 5. 龙虎榜模块 (lhb/ - 5个函数)
- `getStockLhbJgmmtjEm(startDate, endDate)` - 机构买卖统计
- `getStockLhbDetailEm(startDate, endDate)` - 龙虎榜详情
- `getStockLhbStockStatisticEm(symbol)` - 个股上榜统计
- `getStockLhbHyyybEm(startDate, endDate)` - 活跃营业部
- `getStockLhbYybDetailEm(symbol)` - 营业部历史明细

### 6. 资金流向模块 (fund_flow/ - 8个函数)
- `getStockFundFlowIndividual(symbol)` - 个股资金流向
- `getStockFundFlowConcept(symbol)` - 概念板块资金流向
- `getStockIndividualFundFlow(stock, market)` - 个股资金流向(东方财富)
- `getStockIndividualFundFlowRank(indicator)` - 资金流向排名
- `getStockMarketFundFlow()` - 市场资金流向
- `getStockSectorFundFlowRank(indicator, sectorType)` - 板块资金流排名
- `getStockSectorFundFlowSummary(symbol, indicator)` - 行业个股资金流
- `getStockMainFundFlow(symbol)` - 主力净流入排名

### 7. 融资融券模块 (margin/ - 3个函数)
- `getStockMarginAccountInfo()` - 两融账户信息
- `getStockMarginSse(startDate, endDate)` - 上交所两融汇总
- `getStockMarginDetailSzse(date)` - 深交所两融明细
- `getStockMarginDetailSse(date)` - 上交所两融明细

### 8. 板块概念模块 (board/ - 5个函数)
- `getStockBoardConceptIndexThs(symbol, startDate, endDate)` - 概念板块指数
- `getStockBoardIndustrySummaryThs()` - 行业一览表
- `getStockBoardConceptInfoThs(symbol)` - 概念板块简介
- `getStockBoardIndustryIndexThs(symbol, startDate, endDate)` - 行业板块指数
- `getStockHotFollowXq(symbol)` - 雪球关注榜
- `getStockHotRankDetailEm(symbol)` - 股票热度趋势
- `getStockHotKeywordEm(symbol)` - 人气榜关键词
- `getStockChangesEm(symbol)` - 盘口异动
- `getStockBoardChangeEm()` - 板块异动详情

### 9. 涨跌停模块 (zt/ - 5个函数)
- `getStockZtPoolEm(date)` - 涨停股池
- `getStockZtPoolPreviousEm(date)` - 昨日涨停股池
- `getStockZtPoolStrongEm(date)` - 强势股池
- `getStockZtPoolZbgcEm(date)` - 炸板股池
- `getStockZtPoolDtgcEm(date)` - 跌停股池

### 10. 技术选股排名模块 (rank/ - 9个函数)
- `getStockRankCxgThs(symbol)` - 创新高数据
- `getStockRankLxszThs()` - 连续上涨
- `getStockRankCxflThs()` - 持续放量
- `getStockRankCxslThs()` - 持续缩量
- `getStockRankXstpThs(symbol)` - 向上突破
- `getStockRankLjqsThs()` - 量价齐升
- `getStockRankLjqdThs()` - 量价齐跌
- `getStockRankXzjpThs()` - 险资举牌

## 使用示例

### 示例1：获取个股基本信息
```javascript
import { getStockInfo } from './api/stock-unity'

async function fetchStockInfo() {
  const result = await getStockInfo('000001')
  
  if (result.success) {
    console.log('股票信息:', result.data)
    console.log('股票代码:', result.symbol)
  } else {
    console.error('获取失败:', result.error)
  }
}
```

### 示例2：获取龙虎榜详情
```javascript
import { getStockLhbDetailEm } from './api/stock-unity'

async function fetchLhbData() {
  const result = await getStockLhbDetailEm('20240417', '20240430')
  
  if (result.success) {
    console.log('龙虎榜数据条数:', result.data?.length || 0)
    console.log('标识符:', result.symbol)
  } else {
    console.error('获取龙虎榜失败:', result.error)
  }
}
```

### 示例3：获取财务报表
```javascript
import { getStockBalanceSheetByYearlyEm } from './api/stock-unity'

async function fetchBalanceSheet() {
  const result = await getStockBalanceSheetByYearlyEm('000001')
  
  if (result.success) {
    console.log('资产负债表数据:', result.data)
    // 处理数据...
  }
}
```

### 示例4：批量获取多个数据
```javascript
import { 
  getStockInfo, 
  getStockLhbDetailEm,
  getStockFundFlowIndividual 
} from './api/stock-unity'

async function fetchMultipleData() {
  const [infoResult, lhbResult, fundFlowResult] = await Promise.all([
    getStockInfo('000001'),
    getStockLhbDetailEm('20240417', '20240430'),
    getStockFundFlowIndividual('即时')
  ])
  
  // 处理所有结果
  if (infoResult.success) {
    console.log('股票信息获取成功')
  }
  
  if (lhbResult.success) {
    console.log(`获取到 ${lhbResult.data?.length || 0} 条龙虎榜数据`)
  }
  
  if (fundFlowResult.success) {
    console.log('资金流向数据获取成功')
  }
}
```

### 示例5：使用默认导出
```javascript
import stockUnityApi from './api/stock-unity'

async function useDefaultExport() {
  // 调用basic模块函数
  const infoResult = await stockUnityApi.getStockInfo('000001')
  
  // 调用lhb模块函数
  const lhbResult = await stockUnityApi.getStockLhbDetailEm('20240417', '20240430')
  
  // 调用fund_flow模块函数
  const fundFlowResult = await stockUnityApi.getStockFundFlowIndividual('即时')
  
  // 处理结果...
}
```

## 错误处理

所有API函数都包含统一的错误处理：

```javascript
import { getStockInfo } from './api/stock-unity'

async function safeFetch() {
  try {
    const result = await getStockInfo('INVALID_SYMBOL')
    
    if (!result.success) {
      // API返回的业务错误
      console.error('业务错误:', result.error)
      // 可以在这里显示用户友好的错误消息
      alert(`获取股票信息失败: ${result.error}`)
      return
    }
    
    // 成功处理数据
    console.log('数据:', result.data)
    
  } catch (error) {
    // 网络错误或系统错误
    console.error('系统错误:', error)
    alert('网络连接失败，请检查网络设置')
  }
}
```

## 参数说明

### 日期格式
- 大多数日期参数使用 `YYYYMMDD` 格式，如 `20240417`
- 部分接口可能使用 `YYYY-MM-DD` 格式，请参考具体函数文档

### 股票代码格式
- 普通股票代码：`000001`、`600000`
- 带市场前缀：`SZ000001`、`SH600000`（部分接口需要）
. 港股/美股：根据具体接口要求

### 枚举参数
- 使用字符串常量，如 `"近一月"`、`"今日"`、`"即时"`
- 具体可选值请参考函数文档注释

## 最佳实践

1. **错误处理**：始终检查 `result.success` 字段
2. **参数验证**：在调用前验证参数格式
3. **加载状态**：显示加载提示，提升用户体验
4. **缓存策略**：考虑对频繁请求的数据进行缓存
5. **批量请求**：使用 `Promise.all` 进行并行请求
6. **超时处理**：长时间无响应时提供取消选项

## 调试技巧

### 1. 查看完整响应
```javascript
const result = await getStockInfo('000001')
console.log('完整响应:', JSON.stringify(result, null, 2))
```

### 2. 网络请求监控
- 使用浏览器开发者工具的Network面板
- 查看请求URL、参数、响应状态码
- 检查响应数据格式

### 3. 错误排查
```javascript
const result = await getStockInfo('000001')
if (!result.success) {
  console.error('错误详情:', {
    error: result.error,
    timestamp: result.timestamp,
    status: result.status // 如果有的话
  })
}
```

## 常见问题

### Q1: API返回404错误
- 检查URL路径是否正确
- 确认后端服务是否运行
- 检查路由配置

### Q2: 参数格式错误
- 确认日期格式是否正确
- 检查股票代码是否包含正确的前缀
- 验证枚举参数值是否在允许范围内

### Q3: 响应数据为空
- 检查请求日期是否有数据
- 确认股票代码是否正确
- 查看后端日志是否有错误

### Q4: 网络超时
- 增加timeout配置
- 检查网络连接
- 考虑实现重试机制

## 版本历史

- v1.0.0 (2026-04-17): 初始版本，包含58个API函数
- 统一错误处理和响应格式
- 按业务模块分类组织
- 完整的类型注释和文档

## 联系与支持

如有问题或建议，请联系项目维护团队。