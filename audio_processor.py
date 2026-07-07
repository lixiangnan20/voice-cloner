# -*- coding: utf-8 -*-
"""
音频预处理模块
负责音频文件的加载、格式转换、质量验证和标准化处理
"""

import os
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, Dict, Optional
from tqdm import tqdm

import config
from utils.logger import logger
from utils.file_utils import validate_audio_format


class AudioProcessor:
    """音频预处理器"""

    def __init__(self):
        self.target_sr = config.TARGET_SAMPLE_RATE
        self.max_duration = config.MAX_AUDIO_DURATION
        self.min_duration = config.MIN_AUDIO_DURATION

    def get_audio_info(self, path: str) -> Dict:
        """
        获取音频文件的基本信息（不加载完整音频数据）

        Args:
            path: 音频文件路径

        Returns:
            包含音频信息的字典：
            {
                'duration': float,      # 时长（秒）
                'sample_rate': int,     # 采样率
                'channels': int,        # 声道数
                'format': str           # 文件格式
            }
        """
        logger.info(f"正在获取音频信息: {path}")

        try:
            # 使用soundfile获取基本信息（快速，不需要加载全部数据）
            info = sf.info(path)

            result = {
                'duration': info.duration,
                'sample_rate': info.samplerate,
                'channels': info.channels,
                'format': info.format,
                'subtype': info.subtype
            }

            logger.info(f"音频信息获取成功: {result}")
            return result

        except Exception as e:
            logger.error(f"获取音频信息失败: {e}")
            raise ValueError(f"无法读取音频文件信息: {e}")

    def load_audio(self, path: str) -> Tuple[np.ndarray, int]:
        """
        加载音频文件（支持wav, mp3等格式）

        Args:
            path: 音频文件路径

        Returns:
            (audio_data, sample_rate) 元组
            - audio_data: numpy数组
            - sample_rate: 采样率

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持或无法读取
        """
        logger.info(f"正在加载音频文件: {path}")

        # 验证文件存在
        if not os.path.isfile(path):
            raise FileNotFoundError(f"音频文件不存在: {path}")

        # 验证文件格式
        if not validate_audio_format(path):
            ext = os.path.splitext(path)[1].lower()
            raise ValueError(f"不支持的音频格式: {ext}，支持的格式: {config.SUPPORTED_FORMATS}")

        try:
            # 使用librosa加载音频（自动归一化到[-1, 1]）
            audio, sr = librosa.load(path, sr=None, mono=True)
            logger.info(f"成功加载音频: 时长={len(audio)/sr:.2f}秒, 采样率={sr}Hz")
            return audio, sr

        except Exception as e:
            logger.error(f"加载音频失败: {e}")
            raise ValueError(f"无法读取音频文件: {e}")

    def validate_audio(self, audio: np.ndarray, sr: int) -> Dict:
        """
        验证音频质量和参数

        Args:
            audio: 音频数据
            sr: 采样率

        Returns:
            包含验证结果的字典：
            {
                'duration': float,      # 音频时长（秒）
                'sample_rate': int,     # 采样率
                'is_valid': bool,       # 是否有效
                'errors': list          # 错误信息列表
            }
        """
        result = {
            'duration': len(audio) / sr,
            'sample_rate': sr,
            'is_valid': True,
            'errors': []
        }

        # 检查时长
        duration = result['duration']
        if duration < self.min_duration:
            result['is_valid'] = False
            result['errors'].append(
                f"音频时长过短: {duration:.2f}秒 < 最小要求{self.min_duration}秒"
            )

        if duration > self.max_duration:
            result['errors'].append(
                f"警告: 音频时长较长: {duration:.2f}秒，将截取前{self.max_duration}秒"
            )
            # 不算错误，只是警告

        # 检查是否为空
        if len(audio) == 0:
            result['is_valid'] = False
            result['errors'].append("音频数据为空")

        # 检查是否有声音（非静音）
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 0.001:  # 很小的阈值
            result['errors'].append(
                "警告: 音频音量很小，可能是静音或有严重问题"
            )

        return result

    def preprocess(self, audio: np.ndarray, sr: int) -> Tuple[np.ndarray, int]:
        """
        预处理音频：重采样、转单声道、归一化

        Args:
            audio: 原始音频数据
            sr: 原始采样率

        Returns:
            (processed_audio, target_sample_rate) 元组
        """
        logger.info(f"正在预处理音频... 原始采样率: {sr}Hz -> 目标采样率: {self.target_sr}Hz")

        processed = audio.copy()

        # 1. 重采样（如果需要）
        if sr != self.target_sr:
            with tqdm(total=100, desc="重采样中", leave=False) as pbar:
                processed = librosa.resample(
                    y=processed,
                    orig_sr=sr,
                    target_sr=self.target_sr,
                    res_type='kaiser_best'
                )
                pbar.update(100)
            logger.info(f"重采样完成: {self.target_sr}Hz")

        # 2. 确保单声道（librosa默认已转为单声道）

        # 3. 归一化到[-1, 1]
        max_val = np.max(np.abs(processed))
        if max_val > 0:
            processed = processed / max_val

        # 4. 转换为float32（模型要求的格式）
        processed = processed.astype(np.float32)

        logger.info(f"预处理完成: 时长={len(processed)/self.target_sr:.2f}秒")

        return processed, self.target_sr

    def extract_segment(
        self,
        audio: np.ndarray,
        sr: int,
        target_duration: Optional[float] = None
    ) -> np.ndarray:
        """
        截取指定时长的片段作为参考音频

        策略：
        - 如果音频时长 <= target_duration，返回全部
        - 如果音频时长 > target_duration，截取中间部分（通常更稳定）

        Args:
            audio: 音频数据
            sr: 采样率
            target_duration: 目标时长（秒），默认使用配置中的最大值

        Returns:
            截取后的音频片段
        """
        if target_duration is None:
            target_duration = self.max_duration

        total_samples = len(audio)
        target_samples = int(target_duration * sr)

        if total_samples <= target_samples:
            logger.info(f"音频时长({total_samples/sr:.2f}秒) <= 目标时长({target_duration}秒)，使用完整音频")
            return audio

        # 截取中间部分（通常比开头结尾更稳定）
        start = (total_samples - target_samples) // 2
        end = start + target_samples

        segment = audio[start:end]
        logger.info(f"已截取中间{target_duration}秒作为参考音频（原始{total_samples/sr:.2f}秒）")

        return segment

    def save_audio(
        self,
        audio: np.ndarray,
        sr: int,
        path: str
    ) -> str:
        """
        保存音频文件（WAV格式）

        Args:
            audio: 音频数据
            sr: 采样率
            path: 输出文件路径

        Returns:
            实际保存的文件路径
        """
        logger.info(f"正在保存音频到: {path}")

        # 确保输出目录存在
        output_dir = os.path.dirname(path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 确保有正确的扩展名
        if not path.lower().endswith('.wav'):
            path += '.wav'

        # 保存为WAV格式（16bit PCM）
        sf.write(path, audio, sr, subtype='PCM_16')

        logger.info(f"音频保存完成: {path}, 时长={len(audio)/sr:.2f}秒")

        return path

    def process_file(self, input_path: str) -> Tuple[np.ndarray, int]:
        """
        完整的文件处理流程：加载 + 验证 + 预处理 + 截取

        Args:
            input_path: 输入音频文件路径

        Returns:
            (processed_audio, sample_rate) 元组

        Raises:
            Exception: 处理过程中的任何错误
        """
        logger.info("=" * 50)
        logger.info(f"开始处理音频文件: {input_path}")
        logger.info("=" * 50)

        # 1. 加载
        audio, sr = self.load_audio(input_path)

        # 2. 验证
        validation = self.validate_audio(audio, sr)

        if not validation['is_valid']:
            error_msg = "\n".join(validation['errors'])
            raise ValueError(f"音频验证失败:\n{error_msg}")

        if validation['errors']:
            for warn in validation['errors']:
                logger.warning(warn)

        logger.info(f"音频验证通过: 时长={validation['duration']:.2f}秒, 采样率={validation['sample_rate']}Hz")

        # 3. 预处理
        processed, new_sr = self.preprocess(audio, sr)

        # 4. 截取合适长度的参考片段
        reference = self.extract_segment(processed, new_sr)

        logger.info("=" * 50)
        logger.info(f"音频处理完成！参考音频时长: {len(reference)/new_sr:.2f}秒")
        logger.info("=" * 50)

        return reference, new_sr


def create_test_audio(duration: float = 10.0, sr: int = 22050, save_path: str = 'test_reference.wav') -> str:
    """
    创建测试用的正弦波音频（用于开发调试）

    注意：这只是简单的测试音频，实际克隆效果需要真实人声

    Args:
        duration: 音频时长（秒）
        sr: 采样率
        save_path: 保存路径

    Returns:
        保存的文件路径
    """
    logger.info(f"创建测试音频: {duration}秒, {sr}Hz")

    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # 440Hz正弦波（A4音符）+ 轻微调制模拟人声
    frequency = 440 + 50 * np.sin(2 * np.pi * 5 * t)  # 带调制的频率
    audio = 0.3 * np.sin(2 * np.pi * frequency * t)
    audio = audio.astype(np.float32)

    sf.write(save_path, audio, sr)

    logger.info(f"测试音频已保存: {save_path}")

    return save_path


if __name__ == '__main__':
    # 测试音频处理器
    print("测试音频处理器...")

    processor = AudioProcessor()

    # 创建测试音频
    test_file = create_test_audio()

    # 测试加载和处理
    try:
        audio, sr = processor.process_file(test_file)
        print(f"\n✅ 测试通过!")
        print(f"   - 音频时长: {len(audio)/sr:.2f}秒")
        print(f"   - 采样率: {sr}Hz")
        print(f"   - 数据类型: {audio.dtype}")
        print(f"   - 数据范围: [{audio.min():.4f}, {audio.max():.4f}]")

        # 清理测试文件
        os.remove(test_file)
        print("\n   已清理临时文件")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
