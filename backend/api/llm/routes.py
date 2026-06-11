#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大模型（LLM）对话接口 - 简化版本

重构原则：
1. 路由层只负责HTTP请求处理、参数验证、响应组装
2. 业务逻辑通过服务层调用
3. 使用依赖注入传递服务实例
4. 禁止在路由中直接操作LLM客户端
"""
import time, json
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# 导入依赖注入
from .dependencies import get_llm_service

router = APIRouter(prefix="/api/ai", tags=["AI"])


# ═══════════════════════════════════════════════════════════════════
#  请求 / 响应模型
# ═══════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户输入消息", min_length=1)
    session_id: Optional[str] = Field(None, description="会话ID")


class ChatResponse(BaseModel):
    """对话响应"""
    success: bool = True
    session_id: Optional[str] = None
    model: str = ""
    content: str = ""
    error: Optional[str] = None
    timestamp: str = ""


# ═══════════════════════════════════════════════════════════════════
#  REST API 接口
# ═══════════════════════════════════════════════════════════════════

@router.get("/")
def root() -> Dict[str, Any]:
    """根路径"""
    # 导入service_result模块
    from system_service.service_result import success_result
    
    # 构建返回数据
    data = {
        "module": "ai",
        "message": "量华量化平台AI对话API运行中",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 使用service_result模块的success_result函数构建统一格式的返回体
    return success_result(data=data, message="AI服务运行正常")


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    llm_service = Depends(get_llm_service)
) -> ChatResponse:
    """
    普通对话（非流式）
    
    参数：
        message: 用户消息
        session_id: 会话ID（可选）
        
    返回：
        对话响应
    """
    try:
        # 调用LLM服务
        result = llm_service.chat(request.message, request.session_id)
        
        return ChatResponse(
            success=result["success"],
            session_id=result["session_id"],
            model="ark-code-latest",
            content=result["response"],
            timestamp=result["timestamp"]
        )
    except Exception as e:
        return ChatResponse(
            success=False,
            model="",
            content="",
            error=f"对话失败: {str(e)}",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )


@router.get("/health")
def health_check(
    llm_service = Depends(get_llm_service)
) -> Dict[str, Any]:
    """
    健康检查接口
    
    返回：
        服务健康状态
    """
    try:
        health_status = llm_service.get_health_status()
        return health_status
    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "llm_connected": False,
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


@router.post("/analyze")
def analyze_text(
    text: str,
    analysis_type: str = "general",
    llm_service = Depends(get_llm_service)
) -> Dict[str, Any]:
    """
    文本分析接口
    
    参数：
        text: 待分析文本
        analysis_type: 分析类型（general, sentiment, summary, keywords）
        
    返回：
        分析结果
    """
    try:
        result = llm_service.analyze_text(text, analysis_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本分析失败: {str(e)}")