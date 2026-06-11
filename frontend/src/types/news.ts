// 新闻类型定义

// 新闻板块
export type NewsSection = 'company' | 'cls' | 'global' | 'report' | 'cctv';

// 新闻板块名称映射
export const NEWS_SECTION_NAMES: Record<NewsSection, string> = {
  company: '公司动态',
  cls: '财联社',
  global: '全球新闻',
  report: '研报',
  cctv: '新闻联播',
};

// 影响等级类型
export type ImpactLevel = 1 | 2 | 3 | 4 | 5;

// 影响方向类型
export type ImpactDirection = 1 | 0 | -1;

// 情感标签类型
export type SentimentLabel = 1 | 0 | -1;

// 单条新闻数据结构
export type NewsItem = {
  id: number;
  title: string;
  content: string;
  url?: string;
  source: string;
  source_category: string;
  news_type: NewsSection;
  publish_time: string;
  collect_time?: string;
  
  // AI分析结果
  ai_interpretation?: string;           // AI核心解读
  ai_event_type?: string;               // 事件类型
  ai_impact_level?: ImpactLevel;        // 影响等级 1-5
  ai_impact_direction?: ImpactDirection; // 影响方向：1=利好, 0=中性, -1=利空
  ai_risk_level?: ImpactLevel;          // 风险等级 1-5
  ai_benefit_sectors?: string;          // 受益板块（逗号分隔）
  ai_benefit_stocks?: string;           // 受益个股（逗号分隔）
  ai_keywords?: string;                 // 核心关键词（逗号分隔）
  
  // 分类标签
  is_official?: number;                 // 是否官方公告
  is_breaking?: number;                 // 是否突发新闻
  
  // 情感分析
  sentiment?: number;                   // 情感得分 -1.0 ~ 1.0
  sentiment_label?: SentimentLabel;     // 情感标签
  
  // 系统字段
  ai_analyze_time?: string;
  need_analyze?: number;
  source_level?: number;                // 来源可信度等级
  
  // 辅助字段
  _source?: 'redis' | 'mysql';          // 数据来源
  _table_name?: string;                 // 表名
};

// 新闻板块查询响应
export type NewsFetchResponse = {
  status: 'success' | 'error' | 'empty' | 'collecting';
  section: NewsSection;
  section_name: string;
  date: string;
  is_today: boolean;
  data_source: 'redis' | 'mysql' | 'collect' | 'none';
  count: number;
  data: NewsItem[];
  message?: string;
};

// 全量多板块聚合查询响应
export type NewsFetchAllResponse = {
  status: 'success' | 'error' | 'empty' | 'collecting';
  date: string;
  is_today: boolean;
  sections: Record<NewsSection, NewsFetchResponse>;
  total_count: number;
  message?: string;
};

// 新闻统计数据
export type NewsStats = {
  totalToday: number;
  positive: number;
  negative: number;
  neutral: number;
  highImpact: number;
  bySection: Record<NewsSection, number>;
  bySource: { name: string; count: number }[];
};

// 新闻筛选条件
export type NewsFilter = {
  section?: NewsSection | 'all';
  sentiment?: 'positive' | 'negative' | 'neutral' | 'all';
  impactLevel?: ImpactLevel | 0;
  keyword?: string;
  isBreaking?: boolean;
  isOfficial?: boolean;
};
