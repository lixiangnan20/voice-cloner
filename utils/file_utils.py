# -*- coding: utf-8 -*-
"""
文件操作工具模块
"""

import os
from pathlib import Path
from typing import Optional
from utils.logger import logger


def ensure_dir(path: str) -> Path:
    """
    确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        Path对象
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def validate_file_exists(path: str) -> bool:
    """
    验证文件是否存在

    Args:
        path: 文件路径

    Returns:
        文件是否存在
    """
    return os.path.isfile(path)


def validate_audio_format(path: str, supported_formats: list = None) -> bool:
    """
    验证音频文件格式

    Args:
        path: 文件路径
        supported_formats: 支持的格式列表（不含点号）

    Returns:
        格式是否支持
    """
    if supported_formats is None:
        from config import SUPPORTED_FORMATS
        supported_formats = SUPPORTED_FORMATS

    ext = Path(path).suffix.lower().lstrip('.')
    return ext in supported_formats


def get_output_path(output: str, default_name: str = 'output.wav') -> str:
    """
    获取输出文件路径

    Args:
        output: 用户指定的输出路径
        default_name: 默认文件名

    Returns:
        标准化的输出路径
    """
    if not output:
        output = default_name

    # 确保有正确的扩展名
    from config import OUTPUT_FORMAT
    if not output.lower().endswith(f'.{OUTPUT_FORMAT}'):
        output = f"{output}.{OUTPUT_FORMAT}"

    # 确保目录存在
    output_dir = os.path.dirname(output)
    if output_dir:
        ensure_dir(output_dir)

    return output


def safe_filename(name: str) -> str:
    """
    将文本转换为安全的文件名

    Args:
        name: 原始文本

    Returns:
        安全的文件名（替换非法字符）
    """
    # 替换Windows文件名中的非法字符
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        name = name.replace(char, '_')

    # 限制长度
    if len(name) > 200:
        name = name[:200]

    return name.strip()
