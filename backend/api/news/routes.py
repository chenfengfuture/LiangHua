"""
================================================================================
api/news/routes.py — 新闻采集调度接口 & 后台任务管理
================================================================================

【模块职责】
  本文件是新闻系统的"控制中心"，负责：
    1. 启动/停止所有后台任务（APScheduler 采集 + LLM分析引擎 + 持久化线程）
    2. 对外暴露新闻系统管理相关的 REST 接口

【后台任务架构（三层 Redis 管道）】
  ┌─────────────────────────────────────────────────────────────────┐
  │  采集层（APScheduler, 每1分钟）                                   │
  │    AkShare 拉取 → MySQL + news:data:{id}(Redis) → pending_llm  │
  ├─────────────────────────────────────────────────────────────────┤
  │  LLM分析层（8线程常驻, news_llm_analyzer.py）                     │
  │    SPOP pending_llm → 批量LLM → 写回 news:data:{id} → pending_persist │
  ├─────────────────────────────────────────────────────────────────┤
  │  持久化层（单线程定时, news_persist.py）                           │
  │    每5秒: pop pending_persist → 读 Redis → CASE批量更新 MySQL     │
  └─────────────────────────────────────────────────────────────────┘

【启动入口】
  main.py 的 lifespan 事件中调用 start_scheduler()，统一拉起全部后台任务。
  服务关闭时调用 stop_scheduler() 优雅停止所有线程。

【REST 接口一览】
  GET  /api/news/              — 模块状态（队列大小、调度器状态）
  GET  /api/news/collect_all   — 手动触发一次全量采集（后台执行，立即返回）
  GET  /api/news/status        — 详细状态（采集、调度器、Redis队列、LLM、持久化）
  GET  /api/news/scheduler     — 定时任务详情（下次执行时间、触发器信息）
  POST /api/news/scheduler     — 暂停/恢复定时采集任务 {"action": "pause"/"resume"}
  GET  /api/news/clear_redis   — 清空采集时间缓存 + 待处理队列（不清news:data:*）
  GET  /api/news/analyzer_status — LLM分析引擎 + 持久化线程的实时状态

【依赖关系】
  utils/akshare.py         → collect_and_analyze()  全量采集入口
  utils/redis_client.py    → Redis 操作函数、Key常量
  api/news/news_llm_analyzer.py → NewsLLMAnalyzer 单例
  api/news/news_persist.py      → NewsPersistWorker 单例
================================================================================
"""

import threading
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from utils.akshare import collect_and_analyze
from utils.redis_client import (
    get_all_collect_status,
    NEWS_COLLECT_TIME_KEYS,
    NEWS_CCTV_TODONE_KEY,
    _get_client,
    pending_llm_size,
    pending_persist_size,
)
from utils.websocket_manager import ws_manager
from utils.daily_news_skill import fetch_daily_news_by_date, push_news_to_system, repair_daily_news as repair_daily_news_func

router = APIRouter(prefix="/api/news", tags=["news"])


# ═══════════════════════════════════════════════════════════════════
#  全局任务追踪（手动/定时采集的并发控制）
# ═══════════════════════════════════════════════════════════════════

_task_lock = threading.Lock()      # 保护下面三个变量的读写
_task_running = False              # 是否有采集任务正在运行
_task_start_time = None            # 当前任务开始时间（用于显示耗时）
_last_result = None                # 上次采集结果快照


# ═══════════════════════════════════════════════════════════════════
#  APScheduler 定时采集（全局单例）
# ═══════════════════════════════════════════════════════════════════

_scheduler = None                  # BackgroundScheduler 实例
_scheduler_running = False         # 调度器是否正在运行
_scheduler_job_id = "news_collect" # 定时任务的 job id，用于 pause/resume


# ───────────────────────────────────────────────────────────────────
#  启动 / 停止（被 main.py lifespan 调用）
# ───────────────────────────────────────────────────────────────────

def start_scheduler():
    """
    统一启动所有后台任务（项目启动时调用一次）：
      1. 启动 LLM 8线程分析引擎（常驻后台，消费 news:pending_llm）
      2. 启动持久化定时线程（每5秒，消费 news:pending_persist 写 MySQL）
      3. 启动 APScheduler（每1分钟触发全量采集）

    函数本身不阻塞主线程，所有任务均为后台 daemon 线程/调度器。
    """
    global _scheduler, _scheduler_running

    # ── 1. LLM 8线程分析引擎 ────────────────────────────────────────
    try:
        from api.news.news_llm_analyzer import get_news_analyzer
        analyzer = get_news_analyzer()
        analyzer.start_background()
        print("[startup] LLM 8线程分析器已启动")
    except Exception as e:
        print(f"[startup] LLM 分析器启动失败: {e}")

    # ── 2. 持久化定时线程 ───────────────────────────────────────────
    try:
        from api.news.news_persist import get_persist_worker
        worker = get_persist_worker()
        worker.start_background()
        print("[startup] 持久化定时线程已启动（每5秒批量写库）")
    except Exception as e:
        print(f"[startup] 持久化线程启动失败: {e}")

    # ── 3. APScheduler 采集定时任务 ──────────────────────────────────
    if _scheduler_running:
        print("[scheduler] 定时采集任务已在运行，跳过重复启动")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(
            _scheduled_collect,
            id=_scheduler_job_id,
            trigger="interval",
            minutes=1,
            max_instances=1,       # 同时只允许1个实例
            misfire_grace_time=60, # 错过执行的宽限时间（秒）
            coalesce=True,         # 多次未执行时合并为1次
        )
        _scheduler.start()
        _scheduler_running = True
        print("[scheduler] 新闻定时采集任务已启动（每 1 分钟检查一次）")
        
        # 启动后立即执行一次采集（一次性任务，避免阻塞启动流程）
        try:
            from datetime import datetime as dt
            _scheduler.add_job(
                _scheduled_collect,
                id="news_collect_immediate",
                trigger="date",
                run_date=dt.now(),
                misfire_grace_time=60,
            )
            print("[scheduler] 已添加立即采集任务，项目启动后立即执行")
        except Exception as e:
            print(f"[scheduler] 立即采集任务添加失败（不影响定时任务）: {e}")
    except Exception as e:
        print(f"[scheduler] 定时任务启动失败: {e}")


def stop_scheduler():
    """
    优雅停止所有后台任务（服务关闭时调用）。
    按照"LLM分析器 → 持久化线程 → APScheduler"的顺序停止。
    """
    global _scheduler, _scheduler_running

    # 停止 LLM 分析器
    try:
        from api.news.news_llm_analyzer import get_news_analyzer
        get_news_analyzer().stop()
        print("[shutdown] LLM 分析器已停止")
    except Exception:
        pass

    # 停止持久化线程
    try:
        from api.news.news_persist import get_persist_worker
        get_persist_worker().stop()
        print("[shutdown] 持久化线程已停止")
    except Exception:
        pass

    # 停止 APScheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
            print("[scheduler] 定时任务已停止")
        except Exception as e:
            print(f"[scheduler] 停止异常: {e}")
        _scheduler = None
    _scheduler_running = False


# ───────────────────────────────────────────────────────────────────
#  定时采集内部逻辑（APScheduler 回调）
# ───────────────────────────────────────────────────────────────────

def _scheduled_collect():
    """
    APScheduler 每分钟触发的采集逻辑。
    与手动 /collect_all 接口共享同一把锁，防止并发采集。
    """
    global _task_running, _task_start_time, _last_result

    with _task_lock:
        if _task_running:
            print("[scheduler] 跳过: 上次采集仍在执行")
            return
        _task_running = True
        _task_start_time = datetime.now()

    try:
        result = collect_and_analyze()
        with _task_lock:
            _last_result = result
    except Exception as e:
        print(f"[scheduler] 定时采集异常: {e}")
        with _task_lock:
            _last_result = {"error": str(e)}
    finally:
        with _task_lock:
            _task_running = False
            _task_start_time = None


# ═══════════════════════════════════════════════════════════════════
#  REST 接口
# ═══════════════════════════════════════════════════════════════════


@router.get("/")
def news_root():
    """
    新闻模块根路径，返回模块基本状态。

    GET /api/news/
    """
    return {
        "status": "ok",
        "message": "新闻采集模块已就绪（Redis三层架构）",
        "scheduler": "running" if _scheduler_running else "stopped",
        "pending_llm": pending_llm_size(),
        "pending_persist": pending_persist_size(),
    }


@router.get("/collect_all")
def collect_all():
    """
    手动触发一次全量新闻采集（立即返回，采集在后台执行）。

    GET /api/news/collect_all

    采集范围：company(个股) / cls(财联社) / global(全球) / cctv(新闻联播) / report(研报)
    采集结果：新闻写入 MySQL + Redis，id 推入 news:pending_llm，LLM 8线程自动消费。
    防并发：同一时刻只允许一个采集任务运行，重复请求直接返回 already_running。
    """
    global _task_running, _task_start_time, _last_result

    with _task_lock:
        if _task_running:
            elapsed = ""
            if _task_start_time:
                elapsed = f"（已运行 {(datetime.now() - _task_start_time).seconds}s）"
            return {
                "status": "already_running",
                "msg": f"采集任务正在执行中{elapsed}，请勿重复触发",
            }
        _task_running = True
        _task_start_time = datetime.now()
        _last_result = None

    def _background_task():
        global _task_running, _last_result
        try:
            result = collect_and_analyze()
            with _task_lock:
                _last_result = result
        except Exception as e:
            print(f"[news] 工作流异常: {e}")
            with _task_lock:
                _last_result = {"error": str(e)}
        finally:
            with _task_lock:
                _task_running = False
                _task_start_time = None

    t = threading.Thread(target=_background_task, name="news-collect-all", daemon=True)
    t.start()

    return {
        "status": "running",
        "msg": "新闻采集任务已启动（后台执行，LLM 8线程自动分析）",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "detail": "company / cls / global / cctv / report → Redis → LLM → MySQL",
    }


@router.get("/status")
def collect_status():
    """
    查看采集系统全量状态，包括：
      - 采集任务是否运行
      - Redis 各板块采集时间
      - Redis 队列大小（pending_llm / pending_persist）
      - LLM 分析引擎状态
      - 持久化线程状态
      - 调度器状态与下次执行时间

    GET /api/news/status
    """
    global _task_running, _last_result

    with _task_lock:
        running = _task_running
        last_result = _last_result

    redis_status = get_all_collect_status()

    # 获取调度器下次执行时间
    next_run = None
    if _scheduler is not None and _scheduler_running:
        try:
            job = _scheduler.get_job(_scheduler_job_id)
            if job and job.next_run_time:
                next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    # LLM 分析器状态
    analyzer_info = {}
    try:
        from api.news.news_llm_analyzer import get_news_analyzer
        analyzer_info = get_news_analyzer().get_status()
    except Exception:
        pass

    # 持久化层状态
    persist_info = {}
    try:
        from api.news.news_persist import get_persist_worker
        persist_info = get_persist_worker().get_status()
    except Exception:
        pass

    return {
        "task_running": running,
        "redis_status": redis_status,
        "redis_queues": {
            "pending_llm": pending_llm_size(),
            "pending_persist": pending_persist_size(),
        },
        "analyzer": analyzer_info,
        "persist": persist_info,
        "last_result": last_result,
        "scheduler_status": "running" if _scheduler_running else "stopped",
        "scheduler_next_run": next_run,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ───────────────────────────────────────────────────────────────────
#  定时任务管理接口
# ───────────────────────────────────────────────────────────────────

class SchedulerRequest(BaseModel):
    action: str  # "pause"：暂停定时采集；"resume"：恢复


@router.get("/scheduler")
def scheduler_info():
    """
    查看定时采集任务详情。

    GET /api/news/scheduler
    返回：running 状态、触发器配置、下次执行时间等。
    """
    info = {
        "running": _scheduler_running,
        "interval": "1 分钟",
        "max_instances": 1,
        "job_id": _scheduler_job_id,
    }
    if _scheduler is not None and _scheduler_running:
        try:
            job = _scheduler.get_job(_scheduler_job_id)
            if job:
                info["next_run_time"] = (
                    job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                    if job.next_run_time else None
                )
                info["trigger"] = str(job.trigger)
        except Exception:
            pass
    return info


@router.post("/scheduler")
def scheduler_control(req: SchedulerRequest):
    """
    暂停或恢复定时采集任务。

    POST /api/news/scheduler
    Body: {"action": "pause"} 或 {"action": "resume"}

    注意：仅暂停/恢复 APScheduler 调度，不影响正在执行的采集任务和 LLM 分析。
    """
    if req.action == "pause":
        if not _scheduler_running:
            return {"status": "error", "msg": "定时任务未在运行"}
        try:
            _scheduler.pause_job(_scheduler_job_id)
            return {"status": "paused", "msg": "定时任务已暂停"}
        except Exception as e:
            return {"status": "error", "msg": f"暂停失败: {e}"}

    elif req.action == "resume":
        if not _scheduler_running:
            return {"status": "error", "msg": "定时任务未启动"}
        try:
            _scheduler.resume_job(_scheduler_job_id)
            return {"status": "resumed", "msg": "定时任务已恢复"}
        except Exception as e:
            return {"status": "error", "msg": f"恢复失败: {e}"}

    else:
        return {"status": "error", "msg": "action 必须为 pause 或 resume"}


# ───────────────────────────────────────────────────────────────────
#  Redis 缓存管理接口
# ───────────────────────────────────────────────────────────────────

@router.get("/clear_redis")
def clear_news_redis():
    """
    清空采集相关的 Redis 缓存（不影响 news:data:* 永久新闻数据）。

    GET /api/news/clear_redis

    清理范围：
      - news:last_collect_time:{section}（各板块采集时间戳，共5个）
      - news:cctv_today_done（CCTV 当日采集标记）
      - news:pending_llm（待LLM分析的 id Set）
      - news:pending_persist（待持久化的 id List）

    注意：news:data:{id}（新闻完整 JSON）永久保留，不会被清除。
    典型用途：重置采集状态，下次触发时重新全量拉取。
    """
    try:
        r = _get_client()
        if r is None:
            return {"status": "failed", "msg": "Redis 不可用"}

        # 清采集时间 key 和 CCTV 标记
        keys_to_delete = list(NEWS_COLLECT_TIME_KEYS.values()) + [NEWS_CCTV_TODONE_KEY]
        deleted_count = sum(1 for k in keys_to_delete if r.delete(k))

        # 清待处理队列
        from utils.redis_client import NEWS_PENDING_LLM_KEY, NEWS_PENDING_PERSIST_KEY
        queue_deleted = 0
        if r.delete(NEWS_PENDING_LLM_KEY):
            queue_deleted += 1
        if r.delete(NEWS_PENDING_PERSIST_KEY):
            queue_deleted += 1

        print(f"[news] Redis 缓存已清空 | 采集时间:{deleted_count}个 队列:{queue_deleted}个")

        return {
            "status": "success",
            "msg": "新闻 Redis 缓存已清空（news:data:* 永久保留，不受影响）",
            "deleted_collect_time_keys": deleted_count,
            "deleted_queue_keys": queue_deleted,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"status": "failed", "msg": "清理失败", "error": str(e)}


# ───────────────────────────────────────────────────────────────────
#  LLM 分析引擎 + 持久化线程状态接口
# ───────────────────────────────────────────────────────────────────

@router.get("/analyzer_status")
def analyzer_status():
    """
    查看 LLM 8线程分析引擎 + 持久化定时线程的实时状态。

    GET /api/news/analyzer_status

    返回：
      llm_analyzer  → 线程数、存活线程、pending_llm 队列大小、批次配置
      persist_worker → 运行状态、总持久化条数、pending_persist 队列大小、运行时长
    """
    result = {}

    try:
        from api.news.news_llm_analyzer import get_news_analyzer
        result["llm_analyzer"] = get_news_analyzer().get_status()
    except Exception as e:
        result["llm_analyzer"] = {"error": str(e)}

    try:
        from api.news.news_persist import get_persist_worker
        result["persist_worker"] = get_persist_worker().get_status()
    except Exception as e:
        result["persist_worker"] = {"error": str(e)}

    result["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return result


@router.post("/daily_news/repair")
def repair_daily_news(start_date: str, end_date: str = None, is_manual: bool = True):
    """
    修复历史每日新闻（批量导入指定日期范围）。
    
    POST /api/news/daily_news/repair?start_date=2026-04-01&end_date=2026-04-10&is_manual=true
    
    参数：
      start_date: 开始日期，格式 YYYY-MM-DD（必需）
      end_date: 结束日期，格式 YYYY-MM-DD（可选，默认与开始日期相同）
      is_manual: 是否为手动模式（可选，默认true）
        - true: 手动模式，推送WebSocket到前端
        - false: 自动模式，静默执行不推送
    
    返回：
      {
        "status": "success",
        "date_range": "2026-04-01 ~ 2026-04-10",
        "total_days": 10,
        "total_news": 150,
        "message": "成功导入150条新闻"
      }
    """
    try:
        result = repair_daily_news_func(start_date, end_date, is_manual)
        return {
            "status": "success",
            "date_range": f"{start_date} ~ {end_date or start_date}",
            "total_days": result.get("total_days", 1),
            "total_news": result.get("total_pushed", 0),
            "message": f"成功导入{result.get('total_pushed', 0)}条新闻"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
