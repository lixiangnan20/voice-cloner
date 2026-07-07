# AI Voice Cloner (MVP v0.1)
# 基于VoxCPM2的零样本语音克隆工具

"""
AI Voice Cloner - MVP Version 0.1
基于VoxCPM2的零样本中文语音克隆工具

功能特点：
- 输入30秒以内的人声音频，提取音色特征
- 使用VoxCPM2模型进行零样本音色克隆
- 生成具有相同音色的中文语音朗读
- 支持CPU推理，无需专用GPU硬件

快速开始：
    # 克隆语音示例
    python clone.py --audio reference.wav --text "你好世界" --output result.wav

    # 仅TTS（不克隆）
    python clone.py --text "你好世界" -o output.wav

技术栈：
- VoxCPM2: 2B参数多语言TTS模型
- PyTorch: 深度学习框架
- librosa: 音频处理库
"""

__version__ = "0.1.0"
__author__ = "AI Voice Cloner Team"
