#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM核心业务服务模块

将LLM业务逻辑从路由层抽离，实现清晰的关注点分离：
- 路由层：HTTP请求处理、参数验证、响应组装
- 服务层：核心业务逻辑、数据操作、业务规则

遵循依赖注入原则，通过FastAPI的Depends()传递服务实例。

异常处理：所有异常通过raise抛出，由全局异常处理器捕获处理。
"""

import json, time, sys, os
from typing import Dict, List, Optional, Any
from fastapi import Depends
from utils.llm import LLM

class LLMService:
    """LLM核心服务"""
    
    def __init__(self):
        self._llm_client = LLM()
        self._chat_history: Dict[str, List[Dict[str, str]]] = {}
    
    def chat(self, message: str, session_id: str = None) -> Dict[str, Any]:
        """
        LLM聊天接口
        
        参数：
            message: 用户消息
            session_id: 会话ID（可选）
            
        返回：
            聊天响应
        """
        # 如果没有提供session_id，创建一个新的
        if not session_id:
            session_id = f"chat_{int(time.time())}_{hash(message) % 10000}"
        
        # 获取或初始化会话历史
        if session_id not in self._chat_history:
            self._chat_history[session_id] = []
        
        # 添加用户消息到历史
        self._chat_history[session_id].append({
            "role": "user",
            "content": message
        })
        
        # 调用LLM客户端
        response = self._llm_client.chat(
            messages=self._chat_history[session_id],
            session_id=session_id
        )
        
        # 添加助手响应到历史
        self._chat_history[session_id].append({
            "role": "assistant",
            "content": response
        })
        
        # 限制历史长度（防止内存过大）
        if len(self._chat_history[session_id]) > 20:
            self._chat_history[session_id] = self._chat_history[session_id][-10:]
        
        return {
            "success": True,
            "session_id": session_id,
            "response": response,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def get_chat_history(self, session_id: str) -> Dict[str, Any]:
        """
        获取聊天历史
        
        参数：
            session_id: 会话ID
            
        返回：
            聊天历史
        """
        if session_id not in self._chat_history:
            return {
                "success": True,
                "session_id": session_id,
                "history": [],
                "message": "会话不存在或历史为空"
            }
        
        return {
            "success": True,
            "session_id": session_id,
            "history": self._chat_history[session_id],
            "count": len(self._chat_history[session_id])
        }
    
    
    def clear_chat_history(self, session_id: str) -> Dict[str, Any]:
        """
        清除聊天历史
        
        参数：
            session_id: 会话ID
            
        返回：
            清除结果
        """
        if session_id in self._chat_history:
            del self._chat_history[session_id]
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "聊天历史已清除",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def analyze_text(self, text: str, analysis_type: str = "general") -> Dict[str, Any]:
        """
        文本分析
        
        参数：
            text: 待分析文本
            analysis_type: 分析类型（general, sentiment, summary, keywords等）
            
        返回：
            分析结果
        """
        # 根据分析类型构建提示
        if analysis_type == "sentiment":
            prompt = f"请分析以下文本的情感倾向（积极/消极/中性），并给出置信度：\n\n{text}"
        elif analysis_type == "summary":
            prompt = f"请对以下文本进行摘要，提取核心信息：\n\n{text}"
        elif analysis_type == "keywords":
            prompt = f"请从以下文本中提取关键词（3-5个）：\n\n{text}"
        else:  # general
            prompt = f"请对以下文本进行综合分析：\n\n{text}"
        
        # 调用LLM
        response = self._llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            session_id=f"analyze_{int(time.time())}"
        )
        
        return {
            "success": True,
            "analysis_type": analysis_type,
            "text_length": len(text),
            "result": response,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def batch_analyze(self, texts: List[str], analysis_type: str = "general") -> Dict[str, Any]:
        """
        批量文本分析
        
        参数：
            texts: 待分析文本列表
            analysis_type: 分析类型
            
        返回：
            批量分析结果
        """
        results = []
        
        for i, text in enumerate(texts):
            # 为每个文本调用分析
            result = self.analyze_text(text, analysis_type)
            results.append({
                "index": i,
                "text_preview": text[:50] + "..." if len(text) > 50 else text,
                "result": result["result"]
            })
        
        return {
            "success": True,
            "analysis_type": analysis_type,
            "batch_size": len(texts),
            "results": results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    

    def get_health_status(self) -> Dict[str, Any]:
        """
        获取服务健康状态
        
        返回：
            健康状态信息
        """
        # 测试LLM连接
        test_response = self._llm_client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            session_id=f"health_check_{int(time.time())}"
        )
        
        return {
            "success": True,
            "status": "healthy",
            "llm_connected": True,
            "active_sessions": len(self._chat_history),
            "total_messages": sum(len(history) for history in self._chat_history.values()),
            "test_response": test_response[:100] + "..." if len(test_response) > 100 else test_response,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


# ─── 依赖注入函数 ──────────────────────────────────────────────────────────────

def get_llm_service() -> LLMService:
    """获取LLM服务实例"""
    return LLMService()