/**
 * HTTP 客户端 — 全项目统一 axios 实例
 *
 * 配置：
 *   - baseURL 从环境变量 VITE_API_BASE_URL 读取
 *   - 响应拦截器自动提取 response.data
 *   - 错误拦截器统一格式化
 */

import axios from 'axios';
import { HTTP_TIMEOUT } from '../config';

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: HTTP_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
http.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.debug(`[HTTP] ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// 响应拦截器
http.interceptors.response.use(
  (response) => {
    // 统一解构：直接返回 data
    return response.data;
  },
  (error) => {
    const msg = error.response?.data?.message
      || error.response?.data?.detail
      || error.message
      || '请求失败';
    if (import.meta.env.DEV) {
      console.error(`[HTTP] 错误: ${msg}`, error.config?.url);
    }
    return Promise.reject(new Error(msg));
  },
);

export default http;
export { http as httpClient };