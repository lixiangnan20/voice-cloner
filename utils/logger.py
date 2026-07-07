# -*- coding: utf-8 -*-
"""
日志工具模块
"""

import logging
import sys
from datetime import datetime


def setup_logger(name: str = 'voice_cloner', level: str = 'INFO') -> logging.Logger:
    """
    配置并返回日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper()))

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    # 格式化
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


# 全局日志实例
logger = setup_logger()
