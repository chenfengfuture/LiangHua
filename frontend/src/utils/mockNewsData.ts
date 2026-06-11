import dayjs from 'dayjs';
import type { NewsItem, NewsSection, NewsFetchAllResponse, NewsFetchResponse, NewsStats } from '../types/news';
import { NEWS_SECTION_NAMES } from '../types/news';

// 全局递增计数器，确保每次调用 generateMockNews 生成唯一 ID
let globalIdCounter = Math.floor(Date.now() / 1000) * 10000;

// 生成模拟新闻数据
const generateMockNews = (section: NewsSection, count: number): NewsItem[] => {
  const sources: Record<NewsSection, string[]> = {
    company: ['东方财富', '同花顺', '雪球', '证券时报'],
    cls: ['财联社', '财新网', '第一财经', '新浪财经'],
    global: ['路透社', '彭博', '华尔街日报', '金融时报'],
    report: ['中信证券', '国泰君安', '中金公司', '招商证券'],
    cctv: ['央视新闻', '新闻联播', '经济半小时', '央视财经'],
  };

  const eventTypes = ['财报', '并购', '政策', '研发', '诉讼', '高管变动', '战略合作', '产能扩张', '业务调整', '风险事件'];
  const sectors = ['新能源', '半导体', '人工智能', '医药生物', '白酒', '银行', '证券', '房地产', '汽车', '消费电子'];
  const stocks = ['贵州茅台', '宁德时代', '比亚迪', '腾讯控股', '阿里巴巴', '科大讯飞', '中芯国际', '招商银行', '恒瑞医药', '隆基绿能'];

  // 生成基础数据 — 使用全局递增计数器确保唯一 ID
  const baseData = Array.from({ length: count }, (_, i) => {
    const sentimentValue = (Math.random() - 0.5) * 2;
    const sentimentLabel = sentimentValue > 0.2 ? 1 : sentimentValue < -0.2 ? -1 : 0;
    const uniqueId = ++globalIdCounter;
    return {
      id: uniqueId,
      content: generateNewsContent(section),
      url: `https://example.com/news/${section}/${i}`,
      source: sources[section][Math.floor(Math.random() * sources[section].length)],
      source_category: '主流媒体',
      news_type: section,
      publish_time: dayjs().subtract(Math.floor(Math.random() * 12), 'hour').format('YYYY-MM-DD HH:mm:ss'),
      collect_time: dayjs().format('YYYY-MM-DD HH:mm:ss'),
      
      ai_interpretation: 'AI核心解读：该新闻对市场有一定影响，建议关注相关板块走势。',
      ai_event_type: eventTypes[Math.floor(Math.random() * eventTypes.length)],
      ai_impact_level: (Math.floor(Math.random() * 5) + 1) as 1 | 2 | 3 | 4 | 5,
      ai_impact_direction: sentimentLabel as 1 | 0 | -1,
      ai_risk_level: (Math.floor(Math.random() * 3) + 1) as 1 | 2 | 3 | 4 | 5,
      ai_benefit_sectors: sectors.slice(0, 3).join(','),
      ai_benefit_stocks: stocks.slice(0, 2).join(','),
      ai_keywords: sectors.slice(0, 4).join(','),
      
      is_official: Math.random() > 0.7 ? 1 : 0,
      is_breaking: Math.random() > 0.85 ? 1 : 0,
      
      sentiment: parseFloat(sentimentValue.toFixed(2)),
      sentiment_label: sentimentLabel as 1 | 0 | -1,
      
      ai_analyze_time: dayjs().format('YYYY-MM-DD HH:mm:ss'),
      need_analyze: 0,
      source_level: Math.floor(Math.random() * 3) + 1,
      
      _source: 'redis',
      _table_name: `news_${section}_${dayjs().format('YYYYMM')}`,
    };
  });

  // 强制加入 3 条突发新闻、5 条官方新闻、5 条重大影响新闻（用于测试筛选）
  const forcedCount = Math.min(10, Math.floor(count / 3));
  for (let i = 0; i < forcedCount; i++) {
    const idx = Math.floor(Math.random() * baseData.length);
    if (i < 3) baseData[idx].is_breaking = 1;
    else if (i < 6) baseData[idx].is_official = 1;
    else baseData[idx].ai_impact_level = 5;
  }

  return baseData;
};

// 生成新闻标题
function generateNewsTitle(section: NewsSection): string {
  const templates: Record<NewsSection, string[]> = {
    company: [
      '{}发布2026年Q1财报，营收同比增长{}%',
      '{}宣布重大资产重组，涉及金额超{}亿元',
      '{}获机构密集调研，行业龙头地位稳固',
      '{}与{}达成战略合作，共拓新市场',
      '{}高管团队调整，新CEO正式上任',
      '{}发布新产品发布会预告，市场期待高涨',
    ],
    cls: [
      '监管层释放重要信号，{}板块迎政策利好',
      '{}家机构今日集中调研这{}只个股',
      '北上资金今日净流入{}亿元，重点加仓这些板块',
      '市场情绪回暖，三大指数集体走强',
      '机构策略：当前市场处于底部配置区间',
      '主力资金流向曝光，这些个股获持续加仓',
    ],
    global: [
      '美联储宣布{}，全球市场应声上涨',
      '国际油价{}，能源板块集体异动',
      '{}央行调整货币政策，全球流动性迎来变化',
      '地缘政治局势缓和，全球风险偏好回升',
      '美股三大指数收涨，纳指创历史新高',
      '人民币汇率持续走强，外资加速流入A股',
    ],
    report: [
      '{}：{}行业景气度持续上行，维持"买入"评级',
      '深度研报：{}产业链全景图与投资机会',
      '策略研报：{}月市场展望与配置建议',
      '{}上调目标价至{}元，看好长期发展',
      '行业研报：{}板块进入景气上行周期',
      '量化研报：多因子模型捕捉超额收益机会',
    ],
    cctv: [
      '新闻联播关注资本市场健康发展',
      '国家出台新政策支持实体经济发展',
      '我国科技创新取得重大突破',
      '金融业对外开放迈出新步伐',
      '经济高质量发展取得新成效',
      '资本市场改革持续深化，投资者信心稳步提升',
    ],
  };

  const template = templates[section][Math.floor(Math.random() * templates[section].length)];
  const companies = ['贵州茅台', '宁德时代', '比亚迪', '腾讯', '阿里巴巴', '科大讯飞', '中芯国际', '华为'];
  const company = companies[Math.floor(Math.random() * companies.length)];
  
  return template.replace(/\{\}/g, () => {
    if (Math.random() > 0.5) return company;
    return Math.floor(Math.random() * 100).toString();
  });
}

// 生成新闻内容
function generateNewsContent(section: NewsSection): string {
  const contents = [
    '近日，市场传来重要消息。分析人士认为，该事件对相关行业将产生深远影响，建议投资者密切关注后续发展动态。从基本面来看，行业整体景气度持续上行，龙头企业优势明显。',
    '据权威媒体报道，相关政策正在逐步落地，预计将对行业格局产生积极影响。多家机构表示看好后续发展，认为当前是较好的布局时机。从技术面来看，板块指数已突破关键阻力位。',
    '业内专家指出，随着行业集中度的不断提升，头部企业的竞争优势将进一步扩大。同时，政策层面的持续支持也为行业发展提供了有力保障。建议投资者关注具有核心竞争力的优质标的。',
    '最新数据显示，行业需求持续复苏，产业链上下游协同效应显著。多家上市公司发布的业绩预告也印证了行业的高景气度。机构研报普遍认为，行业长期发展趋势向好。',
    '在多重利好因素的共同推动下，市场信心持续恢复。分析人士表示，当前市场估值处于历史相对低位，具备较好的中长期配置价值。建议投资者根据自身风险偏好合理配置资产。',
  ];
  return contents[Math.floor(Math.random() * contents.length)];
}

// 生成单板块响应
export const generateSectionResponse = (section: NewsSection): NewsFetchResponse => {
  const count = Math.floor(Math.random() * 30) + 10;
  return {
    status: 'success',
    section,
    section_name: NEWS_SECTION_NAMES[section],
    date: dayjs().format('YYYY-MM-DD'),
    is_today: true,
    data_source: 'redis',
    count,
    data: generateMockNews(section, count),
  };
};

// 生成全量新闻响应
export const generateAllNewsResponse = (): NewsFetchAllResponse => {
  const sections: Record<NewsSection, NewsFetchResponse> = {
    company: generateSectionResponse('company'),
    cls: generateSectionResponse('cls'),
    global: generateSectionResponse('global'),
    report: generateSectionResponse('report'),
    cctv: generateSectionResponse('cctv'),
  };
  
  const total_count = Object.values(sections).reduce((sum, s) => sum + s.count, 0);
  
  return {
    status: 'success',
    date: dayjs().format('YYYY-MM-DD'),
    is_today: true,
    sections,
    total_count,
  };
};

// 生成新闻统计数据
export const generateNewsStats = (): NewsStats => {
  const totalToday = Math.floor(Math.random() * 500) + 1000;
  const positive = Math.floor(totalToday * 0.45);
  const negative = Math.floor(totalToday * 0.28);
  const neutral = totalToday - positive - negative;
  
  return {
    totalToday,
    positive,
    negative,
    neutral,
    highImpact: Math.floor(totalToday * 0.08),
    bySection: {
      company: Math.floor(totalToday * 0.28),
      cls: Math.floor(totalToday * 0.25),
      global: Math.floor(totalToday * 0.20),
      report: Math.floor(totalToday * 0.15),
      cctv: Math.floor(totalToday * 0.12),
    },
    bySource: [
      { name: '央视新闻', count: Math.floor(totalToday * 0.12) },
      { name: '东方财富网', count: Math.floor(totalToday * 0.18) },
      { name: '财联社', count: Math.floor(totalToday * 0.15) },
      { name: '证券时报', count: Math.floor(totalToday * 0.13) },
      { name: '上海证券报', count: Math.floor(totalToday * 0.11) },
      { name: '中国证券报', count: Math.floor(totalToday * 0.10) },
      { name: '其他', count: Math.floor(totalToday * 0.21) },
    ],
  };
};

// 获取所有新闻（合并各板块）
export const getAllNews = (): NewsItem[] => {
  const response = generateAllNewsResponse();
  return Object.values(response.sections).flatMap(s => s.data);
};

// 按板块获取新闻
export const getNewsBySection = (section: NewsSection): NewsItem[] => {
  return generateMockNews(section, Math.floor(Math.random() * 20) + 10);
};

// 按情感筛选新闻
export const filterNewsBySentiment = (news: NewsItem[], sentiment: 'positive' | 'negative' | 'neutral'): NewsItem[] => {
  const labelMap = { positive: 1, negative: -1, neutral: 0 };
  return news.filter(n => n.sentiment_label === labelMap[sentiment]);
};

// 按影响等级筛选
export const filterNewsByImpact = (news: NewsItem[], level: number): NewsItem[] => {
  return news.filter(n => (n.ai_impact_level || 0) >= level);
};
