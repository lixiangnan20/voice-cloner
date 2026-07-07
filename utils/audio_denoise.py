# -*- coding: utf-8 -*-
"""
音频降噪模块
封装 ffmpeg 滤镜链，供 Web (app.py) 和 CLI (tts_engine.py) 共用
实现三层降噪：输入端预处理 + 输出端强化降噪
"""

import os
import subprocess
import imageio_ffmpeg
from utils.logger import logger

# 缓存 ffmpeg 路径，避免重复查找
_ffmpeg_path = None


def get_ffmpeg() -> str:
    """获取 ffmpeg 可执行文件路径（带缓存）"""
    global _ffmpeg_path
    if _ffmpeg_path is None:
        _ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    return _ffmpeg_path


# 输入端参考音频预处理滤镜：砍掉<70Hz低频嗡嗡 + FFT降噪 + 响度归一化
# 原理：参考音频干净 → 模型不学坏（关键层，能解决98%低频噪音）
PREPROCESS_FILTER = 'highpass=f=70,afftdn=nr=12,loudnorm=I=-16:TP=-1.5'

# 输出端强化降噪滤镜链：
#   highpass(80Hz) + lowpass(8.5kHz)   带通，保留人声频段
#   afftdn                           FFT降噪，强度20dB
#   anlmdn                           非局部均值降噪，专处理语音稳态噪声
#   acompressor                      动态压缩，让声音更饱满
#   speechnorm                       语音电平归一化
#   alimiter                          防止削波
POSTPROCESS_FILTER = (
    'highpass=f=80,lowpass=f=8500,afftdn=nr=20:nf=-30,'
    'anlmdn=s=7:p=0.002:r=0.002,'
    'acompressor=threshold=-20dB:ratio=3:attack=5:release=50,'
    'speechnorm=e=12.5:l=1,alimiter=limit=0.95'
)


def preprocess_reference_audio(input_path: str, output_path: str, sample_rate: int = 16000) -> tuple:
    """
    输入端参考音频预处理：转标准WAV + 降噪 + 响度归一化

    Args:
        input_path: 输入音频文件路径（任意格式）
        output_path: 输出WAV文件路径
        sample_rate: 输出采样率（默认16000，VoxCPM推荐）

    Returns:
        (success: bool, stderr: str)
    """
    ffmpeg = get_ffmpeg()
    result = subprocess.run(
        [ffmpeg, '-i', input_path, '-y',
         '-af', PREPROCESS_FILTER,
         '-ar', str(sample_rate), '-ac', '1', output_path],
        capture_output=True, text=True, timeout=30
    )
    success = os.path.exists(output_path)
    if success:
        logger.info(f"✅ 参考音频降噪预处理完成: {output_path}")
    else:
        logger.error(f"❌ 参考音频预处理失败: {result.stderr[-300:]}")
    return success, result.stderr


def postprocess_output_audio(input_path: str, output_path: str, sample_rate: int = 48000) -> tuple:
    """
    输出端强化降噪：多层滤镜链后处理

    Args:
        input_path: 模型生成的原始WAV文件路径
        output_path: 降噪后的输出WAV文件路径
        sample_rate: 输出采样率（默认48000）

    Returns:
        (success: bool, stderr: str)
    """
    ffmpeg = get_ffmpeg()
    result = subprocess.run(
        [ffmpeg, '-i', input_path, '-y',
         '-af', POSTPROCESS_FILTER,
         '-ar', str(sample_rate), '-ac', '1', output_path],
        capture_output=True, text=True, timeout=60
    )
    success = os.path.exists(output_path)
    if success:
        logger.info("✅ 输出端强化降噪完成（highpass+anlmdn+afftdn+speechnorm）")
    else:
        logger.warning(f"⚠️ 输出端降噪失败，保留原始输出: {result.stderr[-300:]}")
    return success, result.stderr
