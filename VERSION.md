# LiangHua 量化平台

## 项目信息
- **项目名称**: lianghua
- **版本号**: 20260411-17
- **生成时间**: 2026年4月11日 17:26
- **仓库地址**: https://github.com/chenfengfuture/LiangHua.git

## 项目概述
量华量化平台是一个基于 Python Flask + React 的股票量化分析系统，包含：
- 股票K线数据获取与分析
- 量化新闻采集与AI分析
- 实时数据处理与可视化
- 智能选股系统

## 技术栈
- **后端**: Python Flask, MySQL, Redis
- **前端**: React, TypeScript, Ant Design
- **数据源**: akshare, qstock, 东方财富
- **AI分析**: 火山方舟大模型

## 主要功能模块
1. 新闻系统 - 三层Redis管道架构
2. 股票数据服务 - 实时行情与历史数据
3. LLM智能分析 - 8线程并行处理
4. 全量新闻修复服务
5. 智能选股引擎

## 启动方式
```bash
# Windows
启动量华平台.bat

# PowerShell
启动量华平台.ps1
```

## 版本历史
- 20260411-17: 初始版本上传