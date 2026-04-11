"""
api/llm/routes.py — 大模型（LLM）对话接口

独立于业务模块，提供通用的 AI 对话能力：
  - POST /api/ai/chat       普通对话（非流式）
  - POST /api/ai/stream      流式对话（SSE）
  - GET  /api/ai/models      获取可用模型列表
"""

import json
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from utils.llm import LLM, AVAILABLE_MODELS

router = APIRouter(prefix="/api/ai", tags=["AI"])

# 获取 LLM 单例实例
_llm = LLM()


# ═══════════════════════════════════════════════════════════════════
#  请求 / 响应模型
# ═══════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户输入消息", min_length=1)
    model: Optional[str] = Field(None, description="模型名称，默认使用系统默认模型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    temperature: float = Field(0.7, description="温度 0~1", ge=0, le=2)
    max_tokens: int = Field(4096, description="最大生成 token 数", ge=1, le=32768)
    history: Optional[List[dict]] = Field(None, description="历史消息列表 [{role, content}, ...]")


class ChatResponse(BaseModel):
    """对话响应"""
    success: bool = True
    model: str = ""
    content: str = ""
    error: Optional[str] = None


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    description: str = ""


# ═══════════════════════════════════════════════════════════════════
#  接口实现
# ═══════════════════════════════════════════════════════════════════

@router.post("/chat", response_model=ChatResponse, summary="普通对话")
async def chat(req: ChatRequest):
    """
    调用大模型进行对话（非流式）。

    支持传入历史消息实现多轮对话。
    """
    try:
        # 如果有历史消息，使用 chat_with_history
        if req.history:
            result = _llm.chat_with_history(
                message=req.message,
                history=req.history,
                model=req.model,
                system_prompt=req.system_prompt,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            )
        else:
            result = _llm.chat(
                prompt=req.message,
                model=req.model,
                system_prompt=req.system_prompt,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            )

        used_model = req.model or _llm.default_model
        return ChatResponse(success=True, model=used_model, content=result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)}")


@router.post("/stream", summary="流式对话（SSE）")
async def stream_chat(req: ChatRequest):
    """
    调用大模型进行流式对话，返回 Server-Sent Events（SSE）。

    每条 SSE 数据格式：
      data: {"content": "文本片段"}

    结束标记：
      data: [DONE]
    """

    def generate():
        try:
            if req.history:
                # 带历史的流式：手动构建 messages 列表
                msgs = []
                if req.system_prompt:
                    msgs.append({"role": "system", "content": req.system_prompt})
                msgs.extend(req.history)
                msgs.append({"role": "user", "content": req.message})

                for chunk in _llm.stream(
                    messages=msgs,
                    model=req.model,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                ):
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            else:
                for chunk in _llm.stream(
                    prompt=req.message,
                    model=req.model,
                    system_prompt=req.system_prompt,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                ):
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/models", response_model=List[ModelInfo], summary="获取可用模型列表")
async def list_models():
    """返回所有可用的大模型列表"""
    models = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        models.append(ModelInfo(id=model_id, name=model_name))
    return models
