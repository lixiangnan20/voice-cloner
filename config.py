# -*- coding: utf-8 -*-
"""
AI语音克隆工具 - 配置参数
"""

# 音频处理参数
TARGET_SAMPLE_RATE = 22050    # VoxCPM推荐采样率
MAX_AUDIO_DURATION = 60      # 最大参考音频时长（秒）
MIN_AUDIO_DURATION = 30      # 最小参考音频时长（秒）
AUDIO_CHANNELS = 1           # 单声道
BIT_DEPTH = 16               # 位深

# TTS参数
LANGUAGE = 'zh'              # 仅支持中文（MVP阶段）
MAX_TEXT_LENGTH = 500        # 最大文本长度
SUPPORTED_FORMATS = ['wav', 'mp3']  # 输入支持的格式
OUTPUT_FORMAT = 'wav'        # 输出格式

# 模型参数
MODEL_CACHE_DIR = './cache'  # 模型缓存目录
DEVICE = 'cpu'               # 推理设备（CPU模式）

# 日志级别
LOG_LEVEL = 'INFO'

# 文件上传配置
ALLOWED_AUDIO_EXTENSIONS = {'wav', 'mp3', 'ogg', 'flac'}
UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './outputs'
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

# Web服务配置
WEB_HOST = '127.0.0.1'
WEB_PORT = 5000
DEBUG_MODE = False
