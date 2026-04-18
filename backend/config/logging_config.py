#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志配置模块

提供：
1. 统一的日志格式和级别配置
2. 文件日志和标准输出日志
3. 日志轮转配置
4. 不同环境的日志配置
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any


def setup_logging(
    log_dir: str = "logs",
    log_file: str = "lianghua.log",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True
) -> None:
    """
    设置全局日志配置
    
    Args:
        log_dir: 日志目录
        log_file: 日志文件名
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: 单个日志文件最大字节数
        backup_count: 备份文件数量
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
    """
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)
    
    # 配置日志级别
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 清除现有的日志处理器
    logging.getLogger().handlers.clear()
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 配置处理器
    handlers = []
    
    if enable_console:
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        handlers.append(console_handler)
    
    if enable_file:
        # 文件处理器（支持轮转）
        file_path = os.path.join(log_dir, log_file)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        handlers.append(file_handler)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # 设置第三方库的日志级别
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    logging.info(f"日志系统已初始化，级别: {log_level}，日志文件: {file_path if enable_file else '无'}")


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称
        level: 日志级别，为None时使用根日志器级别
        
    Returns:
        日志器实例
    """
    logger = logging.getLogger(name)
    
    if level:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(numeric_level)
    
    return logger


def log_exception(logger: logging.Logger, exception: Exception, context: str = "", level: str = "error") -> None:
    """
    记录异常日志
    
    Args:
        logger: 日志器
        exception: 异常对象
        context: 异常上下文
        level: 日志级别
    """
    error_msg = f"{context}: {type(exception).__name__}: {str(exception)}"
    
    if level.lower() == "error":
        logger.error(error_msg, exc_info=True)
    elif level.lower() == "warning":
        logger.warning(error_msg)
    elif level.lower() == "info":
        logger.info(error_msg)
    elif level.lower() == "debug":
        logger.debug(error_msg, exc_info=True)
    else:
        logger.error(error_msg, exc_info=True)


def configure_environment_logging(env: str = "production") -> None:
    """
    根据环境配置日志
    
    Args:
        env: 环境名称 (development, testing, production)
    """
    if env.lower() == "development":
        setup_logging(
            log_level="DEBUG",
            enable_console=True,
            enable_file=True
        )
    elif env.lower() == "testing":
        setup_logging(
            log_level="INFO",
            enable_console=False,
            enable_file=True
        )
    else:  # production
        setup_logging(
            log_level="WARNING",
            enable_console=False,
            enable_file=True,
            max_bytes=20 * 1024 * 1024,  # 20MB
            backup_count=10
        )