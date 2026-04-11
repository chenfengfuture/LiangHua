"""
量华平台 - 每日收盘数据自动采集器（入口脚本）
========================================
核心逻辑在 utils/collector.py，本文件只负责：
  1. 命令行参数解析
  2. 定时调度（schedule）
  3. 日志配置

运行方式：
  python backend/daily_collector.py              # 作为定时服务常驻
  python backend/daily_collector.py --now        # 立即触发一次（测试用）
  python backend/daily_collector.py --symbols 300059,600519  # 只采集指定股票
  python backend/daily_collector.py --date 2026-03-25 --now  # 采集指定日期
"""

import sys
import os
import time
import logging
import argparse
from datetime import date, datetime

import schedule

from config.settings import COLLECT_SCHEDULE
from utils.collector import run_collect, is_trading_day
from utils.db import _init_pool


# ─── 日志 ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), 'daily_collector.log'),
            encoding='utf-8'
        ),
    ]
)
log = logging.getLogger('daily_collector')


# ─── 初始化 ──────────────────────────────────────────────────────────────────
# 确保使用采集器模式的连接池
_init_pool("collector")


# ─── 定时调度 ─────────────────────────────────────────────────────────────────
def _scheduled_job():
    """schedule 每天 15:50 触发，先判断是否交易日"""
    today = date.today()
    if not is_trading_day(today):
        log.info(f"[scheduler] {today} 非交易日，今日跳过")
        return
    log.info(f"[scheduler] {today} 交易日，启动采集任务...")
    result = run_collect(target_date=today)
    log.info(f"[scheduler] 采集结果: {result}")


def run_scheduler():
    """常驻进程，每天定时自动执行"""
    log.info("[scheduler] 定时采集器启动，每交易日自动采集日K数据")
    log.info(f"[scheduler] 今天 {date.today()} 是否交易日: {is_trading_day(date.today())}")

    schedule.every().day.at(COLLECT_SCHEDULE).do(_scheduled_job)

    while True:
        schedule.run_pending()
        time.sleep(30)


# ─── 命令行入口 ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='量华 - 每日收盘数据采集器')
    parser.add_argument('--now',     action='store_true',  help='立即触发一次采集（不等定时）')
    parser.add_argument('--date',    type=str, default='', help='指定采集日期 YYYY-MM-DD（配合 --now 使用）')
    parser.add_argument('--symbols', type=str, default='', help='只采集指定股票，逗号分隔，如 300059,600519')
    args = parser.parse_args()

    if args.now:
        target = date.today()
        if args.date:
            target = datetime.strptime(args.date, '%Y-%m-%d').date()
        sym_filter = [s.strip() for s in args.symbols.split(',') if s.strip()] or None
        result = run_collect(target_date=target, symbols_filter=sym_filter)
        print('\n结果汇总:')
        for k, v in result.items():
            if k != 'failed_list':
                print(f'  {k}: {v}')
        if result.get('failed_list'):
            print(f'  failed_symbols: {result["failed_list"]}')
    else:
        run_scheduler()
