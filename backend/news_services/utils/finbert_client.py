"""
news_services/utils/finbert_client.py — FinBERT 金融情感分析客户端（单例）

职责：
  - 懒加载 transformers 模型（首次调用时初始化，主进程 lifespan 可显式 warmup）
  - 提供 predict_batch(texts) 接口，返回每条文本的三分类概率 + 综合得分
  - 屏蔽 transformers/torch 的依赖细节，对上层只暴露纯 Python 数据结构

健壮性策略（防止模型不可用阻塞主流程）：
  - 加载前预先设置 HuggingFace 镜像源（HF_ENDPOINT）和 transformers 离线友好模式
  - 加载超时控制：使用线程 + 短超时（默认 20s），失败立即降级
  - 加载失败后：is_available() 返回 False，上层服务跳过 FinBERT 阶段
  - 失败状态可重试：调用 reset_and_retry() 重新加载

输出字段（与 DDL 已预留的扩展字段对齐）：
  title_sentiment       = pos - neg         (-1.0 ~ 1.0)
  title_sentiment_label = argmax → 1/0/-1   (1=正/0=中/-1=负)
  sentiment_confidence  = max(pos, neu, neg)(0.0 ~ 1.0)
  sentiment_volatility  = -Σ p·log3(p)      (0.0 ~ 1.0, 三类等概率时为 1)
"""

import math
import os
import threading
import logging
from typing import Any, Dict, List, Optional

from news_services.config import (
    FINBERT_DEVICE,
    FINBERT_MAX_TEXT_LEN,
    FINBERT_MODEL_NAME,
)

logger = logging.getLogger("finbert_client")


# 归一化熵的常数（三分类时分母为 log(3)）
_LOG3 = math.log(3.0)

# 模型加载超时（秒）—— 本地模型 391MB，磁盘加载 + torch 初始化需更长时间
_LOAD_TIMEOUT = 120


def _normalized_entropy(probs: List[float]) -> float:
    """计算三分类概率分布的归一化熵（0~1）。等概率时为 1，单类=1 时为 0"""
    if not probs:
        return 0.0
    h = 0.0
    for p in probs:
        if p > 1e-9:
            h -= p * math.log(p)
    return max(0.0, min(1.0, h / _LOG3))


class FinbertClient:
    """FinBERT 单例客户端（线程安全）"""

    _instance: Optional["FinbertClient"] = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_init_done", False):
            return
        self._init_done = True
        self._model = None
        self._tokenizer = None
        self._initialized = False  # 标记"是否尝试过初始化"
        self._available = False    # 标记"是否真正可用"
        self._init_lock = threading.Lock()
        self._infer_lock = threading.Lock()  # CPU 模式下避免多线程同时挤压模型
        # 标签映射：模型输出索引 → (label_int, slot_name)
        # 默认按 [positive, neutral, negative] 顺序；如模型不一致，warmup 时根据 id2label 校正
        self._label_order: List[str] = ["positive", "neutral", "negative"]

    # ─────────────────────────────────────────────────────────────
    #  模型加载与预热
    # ─────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """模型当前是否可用（不会触发加载）"""
        return self._available and self._model is not None

    def warmup(self) -> bool:
        """显式预热模型（推荐在 lifespan startup 调用，避免首次请求超时）
        返回是否加载成功；失败不抛异常，仅记录日志，上层应通过 is_available() 判断
        """
        return self._ensure_initialized()

    def reset_and_retry(self) -> bool:
        """重置失败状态，重新尝试加载（用于运维手动恢复）"""
        with self._init_lock:
            self._initialized = False
            self._available = False
            self._model = None
            self._tokenizer = None
        return self._ensure_initialized()

    def _do_load(self, result_holder: dict) -> None:
        """实际执行模型加载（在子线程中调用，便于超时控制）"""
        try:
            # 设置 HuggingFace 镜像源（HF-Mirror，中国大陆友好）
            os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
            # 缩短网络超时，避免单次请求挂死
            os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "10")

            import torch  # noqa: F401
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            logger.info(
                "[finbert] 开始加载模型: %s (device=%s, endpoint=%s)",
                FINBERT_MODEL_NAME, FINBERT_DEVICE,
                os.environ.get("HF_ENDPOINT", "default"),
            )
            tokenizer = AutoTokenizer.from_pretrained(FINBERT_MODEL_NAME)
            model = AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL_NAME)
            model.to(FINBERT_DEVICE)
            model.eval()

            # 根据 id2label 校正标签顺序
            id2label = getattr(model.config, "id2label", None) or {}
            order: List[str] = ["positive", "neutral", "negative"]
            if id2label:
                tmp: List[str] = []
                for i in range(len(id2label)):
                    raw = str(id2label.get(i, "")).lower()
                    if "pos" in raw:
                        tmp.append("positive")
                    elif "neg" in raw:
                        tmp.append("negative")
                    else:
                        tmp.append("neutral")
                if len(tmp) == 3 and set(tmp) == {"positive", "neutral", "negative"}:
                    order = tmp

            result_holder["tokenizer"] = tokenizer
            result_holder["model"] = model
            result_holder["label_order"] = order
            result_holder["ok"] = True
        except Exception as e:
            result_holder["error"] = str(e)
            result_holder["ok"] = False

    def _ensure_initialized(self) -> bool:
        if self._initialized:
            return self._available
        with self._init_lock:
            if self._initialized:
                return self._available

            result_holder: dict = {"ok": False}
            loader = threading.Thread(target=self._do_load, args=(result_holder,), daemon=True)
            loader.start()
            loader.join(timeout=_LOAD_TIMEOUT)

            if loader.is_alive():
                # 加载超时 —— 标记不可用，不阻塞主流程
                logger.error(
                    "[finbert] 模型加载超时（>%ds），降级为不可用，主流水线将自动旁路 FinBERT。"
                    "可能原因：网络问题（HuggingFace 不可达）。建议手动下载模型到本地后通过修改 "
                    "FINBERT_MODEL_NAME 指向本地路径，或设置环境变量 HF_ENDPOINT=<可用镜像>",
                    _LOAD_TIMEOUT,
                )
                self._initialized = True
                self._available = False
                self._model = None
                self._tokenizer = None
                return False

            if not result_holder.get("ok"):
                err = result_holder.get("error", "未知错误")
                logger.error(
                    "[finbert] 模型加载失败：%s。降级为不可用，主流水线将自动旁路 FinBERT。", err,
                )
                self._initialized = True
                self._available = False
                self._model = None
                self._tokenizer = None
                return False

            self._tokenizer = result_holder["tokenizer"]
            self._model = result_holder["model"]
            self._label_order = result_holder["label_order"]
            logger.info("[finbert] 模型加载完成，标签顺序: %s", self._label_order)
            self._initialized = True
            self._available = True
            return True

    # ─────────────────────────────────────────────────────────────
    #  批量推理
    # ─────────────────────────────────────────────────────────────

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        对一批文本做情感分析，返回与输入等长的结果列表。
        任一条失败返回 {} 占位（上层按 None 处理）。
        模型不可用时直接返回全空列表（不抛异常）。
        """
        if not texts:
            return []
        if not self._ensure_initialized() or self._model is None:
            return [{} for _ in texts]

        try:
            import torch

            with self._infer_lock:
                # 截断文本
                clean_texts = [(t or "")[:FINBERT_MAX_TEXT_LEN * 4] for t in texts]  # 字符级粗截断
                enc = self._tokenizer(
                    clean_texts,
                    padding=True,
                    truncation=True,
                    max_length=FINBERT_MAX_TEXT_LEN,
                    return_tensors="pt",
                )
                enc = {k: v.to(FINBERT_DEVICE) for k, v in enc.items()}

                with torch.no_grad():
                    logits = self._model(**enc).logits  # [N, 3]
                    probs = torch.softmax(logits, dim=-1).cpu().tolist()

            results: List[Dict[str, Any]] = []
            for prob in probs:
                # prob 顺序对应 self._label_order
                p_map = {self._label_order[i]: float(prob[i]) for i in range(len(prob))}
                pos = p_map.get("positive", 0.0)
                neu = p_map.get("neutral", 0.0)
                neg = p_map.get("negative", 0.0)

                score = round(pos - neg, 4)
                max_p = max(pos, neu, neg)
                if pos == max_p:
                    label = 1
                elif neg == max_p:
                    label = -1
                else:
                    label = 0
                entropy = round(_normalized_entropy([pos, neu, neg]), 4)

                results.append({
                    "title_sentiment":       max(-1.0, min(1.0, score)),
                    "title_sentiment_label": label,
                    "sentiment_confidence":  round(max_p, 4),
                    "sentiment_volatility":  entropy,
                })
            return results
        except Exception as e:
            logger.error("[finbert] 推理失败: %s", e)
            return [{} for _ in texts]
