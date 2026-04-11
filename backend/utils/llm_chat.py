"""
utils/llm_chat.py — 兼容导入层（已迁移到 utils/llm.py）

旧代码中的 `from utils.llm_chat import call_llm` 仍然有效。
所有逻辑已迁移到 utils/llm.py，此文件仅做转发。
"""

# 纯转发，保持向后兼容
from utils.llm import (
    call_llm,
    stream_llm,
    call_llm_with_history,
    AVAILABLE_MODELS,
)
