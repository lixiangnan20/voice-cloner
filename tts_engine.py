# -*- coding: utf-8 -*-
"""
TTS引擎模块
整合音频处理和语音克隆，提供完整的文本转语音流程
"""

import os
import sys
import uuid
from typing import Optional

import config
from audio_processor import AudioProcessor
from voice_cloner import VoiceCloner
from utils.logger import logger
from utils.file_utils import (
    validate_file_exists,
    validate_audio_format,
    get_output_path,
)
from utils.audio_denoise import (
    preprocess_reference_audio,
    postprocess_output_audio,
)


class TTSEngine:
    """
    文本转语音引擎

    完整的克隆TTS流程：
    1. 加载并预处理参考音频
    2. 调用VoxCPM2模型进行音色克隆和语音合成
    3. 输出WAV格式音频文件
    """

    def __init__(self, device: str = None):
        """
        初始化TTS引擎

        Args:
            device: 推理设备，默认从配置读取
        """
        self.device = device or config.DEVICE
        self.audio_processor = AudioProcessor()
        self.cloner = VoiceCloner(device=self.device)

        logger.info(f"TTS引擎初始化完成 (设备: {self.device})")

    def generate(
        self,
        text: str,
        reference_audio_path: str = None,
        output_path: str = None,
        cfg_value: float = 3.0,
        inference_timesteps: int = 10,
        seed: int = None,
    ) -> dict:
        """
        执行完整的克隆TTS流程

        Args:
            text: 待合成的中文文本
            reference_audio_path: 参考音频文件路径（用于音色克隆）
            output_path: 输出文件路径（可选，默认自动生成）
            cfg_value: CFG引导尺度（默认3.0，越高越稳定）
            inference_timesteps: 推理步数（默认10，越多质量越好但越慢）
            seed: 随机种子（可选）

        Returns:
            包含生成结果的字典：
            {
                'success': bool,           # 是否成功
                'output_file': str,       # 输出文件路径
                'duration': float,        # 音频时长（秒）
                'sample_rate': int,       # 采样率
                'text': str,              # 合成的文本
                'reference_audio': str,   # 参考音频路径
                'error': str,             # 错误信息（失败时）
            }
        """
        result = {
            'success': False,
            'output_file': None,
            'duration': None,
            'sample_rate': None,
            'text': text,
            'reference_audio': reference_audio_path,
            'error': None,
        }

        try:
            # 验证输入参数
            if not text or not text.strip():
                raise ValueError("合成文本不能为空")

            # 处理参考音频（如果提供）- 使用 ffmpeg 降噪预处理
            ref_wav_path = None

            if reference_audio_path:
                # 验证参考音频文件
                if not validate_file_exists(reference_audio_path):
                    raise FileNotFoundError(f"参考音频文件不存在: {reference_audio_path}")

                if not validate_audio_format(reference_audio_path):
                    raise ValueError(
                        f"不支持的音频格式，支持: {config.SUPPORTED_FORMATS}"
                    )

                # ffmpeg 输入端降噪预处理（第1层降噪：highpass + afftdn + loudnorm）
                logger.info("\n" + "=" * 60)
                logger.info("步骤1/4: 参考音频降噪预处理 (ffmpeg)")
                logger.info("=" * 60)

                ref_wav_path = os.path.abspath(
                    os.path.join(config.UPLOAD_FOLDER, f"ref_{uuid.uuid4().hex}.wav")
                )
                os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
                ok, err = preprocess_reference_audio(reference_audio_path, ref_wav_path)
                if not ok:
                    raise RuntimeError(f"参考音频预处理失败: {err[-200:]}")
                logger.info(f"✅ 参考音频预处理完成: {ref_wav_path}")

            # 确定输出路径
            if not output_path:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f'clone_output_{timestamp}.wav'

            output_path = get_output_path(output_path)

            # 执行语音合成
            logger.info("\n" + "=" * 60)
            logger.info("步骤2/4: 执行语音合成 (VoxCPM2)")
            logger.info("=" * 60)

            audio_data, sample_rate, actual_output = self.cloner.synthesize(
                text=text,
                reference_wav_path=ref_wav_path,
                cfg_value=cfg_value,
                inference_timesteps=inference_timesteps,
                seed=seed,
                output_path=output_path,
            )

            # 输出端强化降噪（第3层：highpass + anlmdn + afftdn + 压缩归一化）
            logger.info("\n" + "=" * 60)
            logger.info("步骤3/4: 输出端强化降噪 (ffmpeg)")
            logger.info("=" * 60)

            if actual_output and os.path.exists(actual_output):
                denoised_file = actual_output.replace('.wav', '_denoised.wav')
                ok, _ = postprocess_output_audio(actual_output, denoised_file)
                if ok:
                    actual_output = denoised_file

            # 更新结果
            duration_sec = len(audio_data) / sample_rate

            result['success'] = True
            result['output_file'] = actual_output
            result['duration'] = duration_sec
            result['sample_rate'] = sample_rate

            # 步骤4：完成
            logger.info("\n" + "=" * 60)
            logger.info("步骤4/4: 完成！")
            logger.info("=" * 60)
            logger.info(f"\n🎉 语音生成成功！")
            logger.info(f"   📁 输出文件: {actual_output}")
            logger.info(f"   ⏱️  时长: {duration_sec:.2f}秒")
            logger.info(f"   🔊 采样率: {sample_rate}Hz")
            logger.info(f"   🎚️  CFG: {cfg_value}, 步数: {inference_timesteps}")
            if reference_audio_path:
                logger.info(f"   🎤 参考音频: {reference_audio_path}")
            else:
                logger.info(f"   🎤 使用默认音色（未克隆）")
            logger.info("")

            return result

        except Exception as e:
            error_msg = f"TTS生成失败: {e}"
            logger.error(error_msg)
            result['error'] = error_msg
            return result

    def generate_batch(self, texts: list, **kwargs) -> list:
        """
        批量生成多个文本的语音（MVP暂不实现）

        Args:
            texts: 文本列表
            **kwargs: 其他参数同generate()

        Returns:
            结果列表
        """
        results = []
        for i, text in enumerate(texts):
            logger.info(f"\n批量生成 [{i+1}/{len(texts)}]...")

            # 为每个文件生成不同的输出名
            if 'output_path' not in kwargs or not kwargs['output_path']:
                kwargs['output_path'] = f'batch_{i+1}.wav'

            result = self.generate(text=text, **kwargs)
            results.append(result)

        return results


def main():
    """测试TTSEngine"""
    print("\n" + "🎤" + " TTSEngine 测试 " + "🎤" + "\n")

    engine = TTSEngine(device='cpu')

    print("测试1: 基础TTS（无克隆）...")
    result = engine.generate(
        text="你好，这是AI语音克隆系统的测试。",
        seed=42
    )

    if result['success']:
        print(f"✅ 成功！输出: {result['output_file']}")
        if os.path.exists(result['output_file']):
            os.remove(result['output_file'])
            print("   已清理测试文件\n")
    else:
        print(f"❌ 失败: {result.get('error')}\n")


if __name__ == '__main__':
    main()
