/**
 * 新闻数据服务（对接后端真实 API）
 *
 * 后端接口：
 *   - GET /api/news/fetch             全量拉取所有板块
 *   - GET /api/news/fetch/{section}   单板块新闻
 *   - GET /api/news/fetch/status      采集状态
 *   - GET /api/news/collect_all       手动触发采集
 *   - GET /api/news/status            详细状态
 */

import http from './http';
import { generateAllNewsResponse, generateSectionResponse, generateNewsStats, getAllNews as getMockAllNews, getNewsBySection as getMockSectionNews } from '../utils/mockNewsData';
import type {
  NewsItem,
  NewsSection,
  NewsFetchAllResponse,
  NewsFetchResponse,
  NewsStats,
} from '../types/news';
import { NEWS_API } from '../config';

// 后端响应包裹层（{success, message, data}）
type ApiResponse<T> = {
  success: boolean;
  message?: string;
  data?: T;
};

// 后端 fetch 接口的返回结构
interface BackendFetchAllData {
  sections: Record<string, BackendSectionResponse>;
  total_count: number;
  status: string;
  date: string;
  is_today: boolean;
  message?: string;
}

interface BackendSectionResponse {
  status: string;
  section: string;
  section_name: string;
  date: string;
  is_today: boolean;
  data_source: string;
  count: number;
  data: NewsItem[];
  message?: string;
}

// 后端状态接口返回结构
interface BackendStatusData {
  success: boolean;
  timestamp: string;
  collect_status: Record<string, string>;
  analyzer: {
    running: boolean;
    alive_threads: number;
    pending_llm_size: number;
    pending_persist_size: number;
  };
  persist: {
    running: boolean;
    total_persisted: number;
    pending_persist_size: number;
  };
  queues: {
    pending_llm: number;
    pending_persist: number;
  };
}

/**
 * 从后端 API 响应中提取安全的 data 值
 * 后端统一返回 {success, message, data}，但有些接口可能直接返回
 */
function safeData<T>(resp: any, fallback: T): T {
  if (resp?.success && resp?.data != null) return resp.data;
  if (resp?.data != null) return resp.data;
  if (resp?.sections != null) return resp as unknown as T;
  return fallback;
}

export const newsService = {
  /**
   * 全量拉取所有板块新闻
   * GET /api/news/fetch
   */
  fetchAllNews: async (): Promise<NewsFetchAllResponse> => {
    try {
      const resp: any = await http.get(NEWS_API.FETCH_ALL);
      const data: BackendFetchAllData = safeData(resp, {
        sections: {} as Record<string, BackendSectionResponse>,
        total_count: 0,
        status: 'empty',
        date: new Date().toISOString().split('T')[0],
        is_today: true,
      });

      // 将后端 section 字典映射为前端期望的 Record<NewsSection, NewsFetchResponse>
      const sections = {} as Record<NewsSection, NewsFetchResponse>;
      for (const [key, val] of Object.entries(data.sections)) {
        const s = val as BackendSectionResponse;
        sections[key as NewsSection] = {
          status: s.status as 'success' | 'empty' | 'collecting' | 'error',
          section: s.section as NewsSection,
          section_name: s.section_name,
          date: s.date,
          is_today: s.is_today,
          data_source: s.data_source as 'redis' | 'mysql' | 'collect' | 'none',
          count: s.count,
          data: s.data.map(normalizeNewsItem),
          message: s.message,
        };
      }

      return {
        status: data.status as 'success' | 'empty' | 'collecting' | 'error',
        date: data.date,
        is_today: data.is_today,
        sections,
        total_count: data.total_count,
        message: data.message,
      };
    } catch (e: any) {
      console.warn('[newsService] fetchAllNews 失败，降级到模拟数据:', e.message);
      return generateAllNewsResponse();
    }
  },

  /**
   * 获取指定板块新闻
   * GET /api/news/fetch/{section}?limit=500
   */
  fetchNewsBySection: async (
    section: NewsSection,
    limit: number = 500,
  ): Promise<NewsFetchResponse> => {
    try {
      const resp: any = await http.get(NEWS_API.FETCH_SECTION(section), {
        params: { limit },
      });
      // 兼容两种响应格式：直接 NewsFetchResponse 或包裹在 {success, data} 中
      const data: BackendSectionResponse = safeData(resp, resp as BackendSectionResponse);
      return {
        status: data.status as 'success' | 'empty' | 'collecting' | 'error',
        section: data.section as NewsSection,
        section_name: data.section_name,
        date: data.date,
        is_today: data.is_today,
        data_source: data.data_source as 'redis' | 'mysql' | 'collect' | 'none',
        count: data.count,
        data: (data.data || []).map(normalizeNewsItem),
        message: data.message,
      };
    } catch (e: any) {
      console.warn(`[newsService] fetchNewsBySection ${section} 失败，降级到模拟数据:`, e.message);
      return generateSectionResponse(section);
    }
  },

  /**
   * 获取新闻统计数据（前端从全量数据计算）
   */
  fetchNewsStats: async (): Promise<NewsStats> => {
    try {
      const allResp = await newsService.fetchAllNews();
      return computeStats(allResp);
    } catch {
      return fallbackStats();
    }
  },

  /**
   * 获取所有板块的扁平新闻列表
   */
  getAllNews: async (): Promise<NewsItem[]> => {
    try {
      const allResp = await newsService.fetchAllNews();
      const items: NewsItem[] = [];
      for (const section of Object.values(allResp.sections)) {
        items.push(...section.data);
      }
      return items;
    } catch {
      return [];
    }
  },

  /**
   * 按板块获取新闻列表
   */
  getNewsBySection: async (section: NewsSection): Promise<NewsItem[]> => {
    try {
      const resp = await newsService.fetchNewsBySection(section);
      return resp.data;
    } catch {
      console.warn('[newsService] getNewsBySection 降级到模拟数据');
      return getMockSectionNews(section);
    }
  },

  /**
   * 搜索新闻（前端本地过滤）
   */
  searchNews: async (keyword: string): Promise<NewsItem[]> => {
    try {
      const allNews = await newsService.getAllNews();
      const lowerKeyword = keyword.toLowerCase();
      return allNews.filter(
        (news) =>
          news.title?.toLowerCase().includes(lowerKeyword) ||
          news.content?.toLowerCase().includes(lowerKeyword) ||
          news.ai_keywords?.toLowerCase().includes(lowerKeyword),
      );
    } catch {
      return [];
    }
  },

  /**
   * 手动触发全量新闻采集
   * GET /api/news/collect_all
   */
  triggerCollect: async (): Promise<{ success: boolean; message: string }> => {
    try {
      const resp: any = await http.get(NEWS_API.COLLECT_ALL);
      return {
        success: resp?.success !== false,
        message: resp?.message || resp?.data?.message || '新闻采集任务已启动',
      };
    } catch (e: any) {
      return { success: false, message: e.message };
    }
  },

  /**
   * 获取采集器/LLM/持久化状态
   * GET /api/news/status
   */
  getCollectStatus: async (): Promise<{
    status: string;
    pending_llm: number;
    pending_persist: number;
    collecting_sections: string[];
  }> => {
    try {
      const resp: any = await http.get(NEWS_API.STATUS);
      const data: BackendStatusData = safeData(resp, {} as BackendStatusData);
      return {
        status: data?.analyzer?.running ? 'running' : 'stopped',
        pending_llm: data?.queues?.pending_llm ?? data?.analyzer?.pending_llm_size ?? 0,
        pending_persist:
          data?.queues?.pending_persist ?? data?.persist?.pending_persist_size ?? 0,
        collecting_sections: data?.collect_status
          ? Object.entries(data.collect_status)
              .filter(([, v]) => v !== 'never')
              .map(([k]) => k)
          : [],
      };
    } catch {
      return { status: 'unknown', pending_llm: 0, pending_persist: 0, collecting_sections: [] };
    }
  },
};

// ─── 工具函数 ─────────────────────────────────────────────────────

/**
 * 标准化单条新闻字段
 */
export function normalizeNewsItem(item: any): NewsItem {
  return {
    id: item.id ?? 0,
    title: item.title ?? '',
    content: item.content ?? '',
    url: item.url,
    source: item.source ?? '',
    source_category: item.source_category ?? '',
    news_type: item.news_type as NewsSection,
    publish_time: item.publish_time ?? '',
    collect_time: item.collect_time,
    ai_interpretation: item.ai_interpretation,
    ai_event_type: item.ai_event_type,
    ai_impact_level: item.ai_impact_level,
    ai_impact_direction: item.ai_impact_direction,
    ai_risk_level: item.ai_risk_level,
    ai_benefit_sectors: item.ai_benefit_sectors,
    ai_benefit_stocks: item.ai_benefit_stocks,
    ai_keywords: item.ai_keywords,
    sentiment: item.sentiment,
    sentiment_label: item.sentiment_label,
    is_official: item.is_official,
    is_breaking: item.is_breaking,
    ai_analyze_time: item.ai_analyze_time,
    need_analyze: item.need_analyze,
    source_level: item.source_level,
    _source: item._source,
    _table_name: item._table_name,
  };
}

/**
 * 从全量响应前端计算统计数据
 */
export function computeStats(resp: NewsFetchAllResponse): NewsStats {
  const allItems: NewsItem[] = [];
  const bySection: Record<string, number> = {};
  const bySourceMap: Record<string, number> = {};

  for (const [section, secResp] of Object.entries(resp.sections)) {
    bySection[section] = (secResp.data || []).length;
    for (const item of secResp.data || []) {
      allItems.push(item);
      const src = item.source || '未知';
      bySourceMap[src] = (bySourceMap[src] || 0) + 1;
    }
  }

  const positive = allItems.filter((n) => n.sentiment_label === 1).length;
  const negative = allItems.filter((n) => n.sentiment_label === -1).length;
  const neutral = allItems.filter((n) => n.sentiment_label === 0).length;
  const highImpact = allItems.filter((n) => (n.ai_impact_level || 0) >= 4).length;

  const bySource = Object.entries(bySourceMap)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  return {
    totalToday: resp.total_count,
    positive,
    negative,
    neutral,
    highImpact,
    bySection: bySection as Record<NewsSection, number>,
    bySource,
  };
}

function fallbackStats(): NewsStats {
  return {
    totalToday: 0,
    positive: 0,
    negative: 0,
    neutral: 0,
    highImpact: 0,
    bySection: { company: 0, cls: 0, global: 0, report: 0, cctv: 0 },
    bySource: [],
  };
}

export default newsService;