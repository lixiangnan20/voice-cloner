# -*- coding: utf-8 -*-
"""
语音克隆核心模块
基于VoxCPM2实现零样本音色克隆功能
"""

import os
import time
import numpy as np
import soundfile as sf
from typing import Optional, Tuple
from tqdm import tqdm

# 设置HuggingFace镜像站 + 沙箱兼容配置
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'  # 禁用hf_transfer（避免临时文件操作）
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '120'

import config
from utils.logger import logger


class VoiceCloner:
    """
    音色克隆器核心类

    使用VoxCPM2模型实现零样本语音克隆，支持CPU推理
    """

    def __init__(self, device: str = None):
        """
        初始化语音克隆器

        Args:
            device: 推理设备 ('cpu', 'cuda', 'mps')，默认从配置读取
        """
        self.device = device or config.DEVICE
        self.model = None
        self.model_loaded = False
        self.sample_rate = None  # 模型输出采样率（加载后设置）

        logger.info(f"初始化VoiceCloner，设备: {self.device}")

    def load_model(self, load_denoiser: bool = False):
        """
        加载VoxCPM2模型

        Args:
            load_denoiser: 是否加载去噪器（提升质量但增加显存/内存占用）

        Note:
            首次调用会自动从HuggingFace下载模型权重（约2GB）
            后续运行会缓存到本地，无需重新下载
        """
        if self.model_loaded:
            logger.info("模型已加载，跳过")
            return

        logger.info("=" * 60)
        logger.info("正在加载VoxCPM2模型...")
        logger.info("=" * 60)

        start_time = time.time()

        try:
            from voxcpm import VoxCPM

            # 设置缓存目录到项目目录下
            cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
            os.makedirs(cache_dir, exist_ok=True)
            os.environ['HF_HUB_CACHE'] = cache_dir

            # 检查ModelScope下载的模型是否存在
            ms_model_path = os.path.join(cache_dir, 'OpenBMB', 'VoxCPM2')
            if os.path.isdir(ms_model_path):
                # 使用ModelScope下载的本地模型
                logger.info(f"使用ModelScope本地模型: {ms_model_path}")
                # 设置离线模式，避免HuggingFace尝试在线检查
                os.environ['HF_HUB_OFFLINE'] = '1'

            # 显示进度提示
            with tqdm(total=100, desc="加载模型", unit="%") as pbar:
                pbar.set_postfix({"状态": "初始化..."})
                pbar.update(10)

                # 优先使用本地模型路径
                model_path = ms_model_path if os.path.isdir(ms_model_path) else "openbmb/VoxCPM2"
                self.model = VoxCPM.from_pretrained(
                    model_path,
                    load_denoiser=load_denoiser,
                )

                pbar.update(70)
                pbar.set_postfix({"状态": "模型就绪"})

                # 获取模型输出采样率（VoxCPM2输出48kHz）
                self.sample_rate = self.model.tts_model.sample_rate
                logger.info(f"模型输出采样率: {self.sample_rate}Hz")

                pbar.update(20)
                pbar.set_postfix({"状态": "完成"})

            self.model_loaded = True
            elapsed = time.time() - start_time
            logger.info(f"✅ 模型加载成功！耗时: {elapsed:.1f}秒")
            logger.info("=" * 60)

        except ImportError as e:
            logger.error(f"❌ 导入VoxCPM失败: {e}")
            raise RuntimeError(
                "请先安装voxcpm包: pip install voxcpm\n"
                "安装后重启程序"
            )
        except Exception as e:
            logger.error(f"❌ 加载模型失败: {e}")
            raise RuntimeError(f"模型加载失败: {e}")

    def synthesize(
        self,
        text: str,
        reference_wav_path: str = None,
        reference_audio: np.ndarray = None,
        reference_sr: int = None,
        cfg_value: float = 3.0,
        inference_timesteps: int = 10,
        seed: int = None,
        output_path: str = None,
    ) -> Tuple[np.ndarray, int, str]:
        """
        核心方法：文本 + 参考音频 → 克隆语音合成

        Args:
            text: 待合成的中文文本（支持标点符号）
            reference_wav_path: 参考音频文件路径（优先级高于reference_audio）
            reference_audio: 参考音频numpy数组（需为16kHz单声道）
            reference_sr: 参考音频采样率（如果提供reference_audio）
            cfg_value: CFG引导尺度（越高越稳定，默认3.0）
            inference_timesteps: 推理步数（越多质量越好但越慢，默认10）
            seed: 随机种子（None表示随机）
            output_path: 输出文件路径（可选）

        Returns:
            (audio_data, sample_rate, output_path) 元组：
            - audio_data: 生成的音频数据（numpy数组）
            - sample_rate: 输出采样率（通常为48000Hz）
            - output_path: 实际输出路径

        Raises:
            ValueError: 参数无效或文本为空
            RuntimeError: 模型未加载或生成失败
        """
        # 验证模型已加载
        if not self.model_loaded or self.model is None:
            logger.warning("模型未加载，正在自动加载...")
            self.load_model()

        # 参数验证
        if not text or not text.strip():
            raise ValueError("合成文本不能为空")

        if len(text) > config.MAX_TEXT_LENGTH:
            logger.warning(
                f"文本长度({len(text)})超过限制({config.MAX_TEXT_LENGTH})，将截取前{config.MAX_TEXT_LENGTH}个字符"
            )
            text = text[:config.MAX_TEXT_LENGTH]

        logger.info("=" * 60)
        logger.info("开始语音合成...")
        logger.info(f"  文本内容: {text[:50]}{'...' if len(text) > 50 else ''}")
        logger.info(f"  文本长度: {len(text)} 字符")
        logger.info(f"  CFG值: {cfg_value}, 步数: {inference_timesteps}")
        if seed:
            logger.info(f"  随机种子: {seed}")
        logger.info("=" * 60)

        start_time = time.time()
        audio_output = None

        try:
            # 构建生成参数
            generate_params = {
                'text': text,
                'cfg_value': cfg_value,
                'inference_timesteps': inference_timesteps,
            }

            # 设置随机种子（用于复现结果）
            if seed is not None:
                generate_params['seed'] = seed

            # 参考音频处理
            if reference_wav_path and os.path.isfile(reference_wav_path):
                # 使用参考音频文件路径
                generate_params['reference_wav_path'] = reference_wav_path
                logger.info(f"  参考音频(文件): {reference_wav_path}")
            elif reference_audio is not None:
                # 使用传入的音频数组（需要先保存为临时文件）
                temp_ref_path = '_temp_reference.wav'
                sf.write(temp_ref_path, reference_audio, reference_sr or 16000)
                generate_params['reference_wav_path'] = temp_ref_path
                logger.info(f"  参考音频(数组): {len(reference_audio)} samples @ {reference_sr}Hz")
                logger.info(f"  已保存临时参考音频: {temp_ref_path}")
            else:
                # 无参考音频（纯TTS，不进行克隆）
                logger.warning("⚠️  未提供参考音频，将使用默认音色进行TTS")

            # 调用模型生成
            logger.info("\n正在生成音频... (这可能需要几秒到十几秒)")
            with tqdm(total=100, desc="合成中", unit="%") as pbar:
                pbar.set_postfix({"状态": "推理中"})
                pbar.update(20)

                audio_output = self.model.generate(**generate_params)

                pbar.update(80)
                pbar.set_postfix({"状态": "完成"})

            elapsed = time.time() - start_time
            duration_sec = len(audio_output) / self.sample_rate
            rtf = elapsed / duration_sec if duration_sec > 0 else float('inf')

            logger.info(f"\n✅ 语音合成完成！")
            logger.info(f"  生成时长: {duration_sec:.2f}秒")
            logger.info(f"  耗时: {elapsed:.2f}秒")
            logger.info(f"  RTF (实时因子): {rtf:.2f}")
            logger.info(f"  采样率: {self.sample_rate}Hz")
            logger.info("=" * 60)

            # 保存输出文件
            actual_output_path = output_path
            if output_path:
                actual_output_path = self._save_audio(audio_output, output_path)

            return audio_output, self.sample_rate, actual_output_path

        except Exception as e:
            logger.error(f"\n❌ 语音合成失败: {e}")
            raise RuntimeError(f"语音合成过程出错: {e}")

        finally:
            # 清理临时文件
            if reference_audio is not None:
                temp_file = '_temp_reference.wav'
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logger.debug("已清理临时参考音频文件")
                    except:
                        pass

    def _save_audio(self, audio: np.ndarray, path: str) -> str:
        """
        保存生成的音频到文件

        Args:
            audio: 音频数据
            path: 目标路径

        Returns:
            实际保存路径
        """
        # 确保目录存在
        output_dir = os.path.dirname(path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 确保有正确的扩展名
        if not path.lower().endswith('.wav'):
            path += '.wav'

        # 保存（保持原始采样率和精度）
        sf.write(path, audio, self.sample_rate)
        logger.info(f"音频已保存: {path}")

        return path

    def get_info(self) -> dict:
        """
        获取克隆器状态信息

        Returns:
            包含设备、模型状态等信息的字典
        """
        return {
            'device': self.device,
            'model_loaded': self.model_loaded,
            'sample_rate': self.sample_rate,
            'library': 'VoxCPM2',
            'version': '2.x',
        }


def test_cloner():
    """测试VoiceCloner基本功能"""
    print("\n" + "=" * 60)
    print("VoiceCloner 功能测试")
    print("=" * 60 + "\n")

    cloner = VoiceCloner(device='cpu')

    try:
        # 测试模型加载
        print("[1/3] 测试模型加载...")
        cloner.load_model()
        print("      ✅ 模型加载成功\n")

        # 测试信息获取
        print("[2/3] 测试信息查询...")
        info = cloner.get_info()
        for key, value in info.items():
            print(f"      {key}: {value}")
        print("      ✅ 信息查询成功\n")

        # 测试纯TTS（无克隆，仅验证模型可用）
        print("[3/3] 测试基础TTS（无克隆）...")
        audio, sr, path = cloner.synthesize(
            text="你好，这是一个语音克隆测试。",
            seed=42,
            output_path='_test_output.wav'
        )

        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            print(f"      ✅ TTS测试成功！")
            print(f"         输出: {path}")
            print(f"         大小: {size_kb:.1f} KB")
            print(f"         时长: {len(audio)/sr:.2f}秒")
            # 清理测试文件
            os.remove(path)
            print(f"         已清理测试文件\n")
        else:
            print(f"      ⚠️  未生成输出文件\n")

        print("=" * 60)
        print("所有测试通过！✅\n")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_cloner()
