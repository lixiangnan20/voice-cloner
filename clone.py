# -*- coding: utf-8 -*-
"""
AI语音克隆工具 - 命令行接口（CLI）
使用方法：
  # 基础用法：克隆音色并朗读文本
  python clone.py --audio reference.wav --text "你好世界" --output result.wav

  # 仅TTS（不克隆，使用默认音色）
  python clone.py --text "你好世界" -o output.wav

  # 完整示例
  python clone.py \
    -a my_voice.wav \
    -t "今天天气真好，适合出去散步" \
    -o output.wav
"""

import os
import sys
import click


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════╗
║                                                  ║
║   🎙️ AI Voice Cloner (MVP v0.1)                 ║
║   基于VoxCPM2的零样本语音克隆工具                  ║
║                                                  ║
╚══════════════════════════════════════════════════╝
"""
    click.echo(banner)


@click.command()
@click.option(
    '--audio', '-a',
    type=click.Path(exists=True),
    help='参考音频文件路径（wav/mp3），用于提取音色特征'
)
@click.option(
    '--text', '-t',
    required=True,
    help='待合成的中文文本内容'
)
@click.option(
    '--output', '-o',
    default=None,
    help='输出WAV文件路径（默认自动生成带时间戳的文件名）'
)
@click.option(
    '--device', '-d',
    default='cpu',
    type=click.Choice(['cpu', 'cuda', 'mps'], case_sensitive=False),
    help='推理设备类型 (默认: cpu)'
)
@click.option(
    '--cfg',
    default=3.0,
    type=float,
    help='CFG引导尺度，值越高生成越稳定但多样性降低 (默认: 3.0)'
)
@click.option(
    '--steps', '-s',
    default=10,
    type=int,
    help='推理步数，越多质量越好但越慢 (默认: 10, 范围: 5-30)'
)
@click.option(
    '--seed',
    default=None,
    type=int,
    help='随机种子，用于复现结果（不指定则随机）'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='显示详细日志信息'
)
def main(
    audio,
    text,
    output,
    device,
    cfg,
    steps,
    seed,
    verbose
):
    """
    🎤 AI语音克隆工具 - 输入参考音频克隆音色，朗读文本生成语音

    示例:
      \b
      克隆语音:\n
      python clone.py -a voice.wav -t "你好世界" -o result.wav\n
      纯TTS:\n
      python clone.py -t "你好世界" -o result.wav
    """

    # 打印横幅
    if not verbose:
        print_banner()

    try:
        # 导入核心模块（延迟导入，加快启动速度）
        from tts_engine import TTSEngine
        from utils.logger import logger

        if verbose:
            logger.info(f"参数配置:")
            logger.info(f"  参考音频: {audio or '无（使用默认音色）'}")
            logger.info(f"  文本: {text[:100]}{'...' if len(text)>100 else ''}")
            logger.info(f"  输出路径: {output or '自动生成'}")
            logger.info(f"  设备类型: {device}")
            logger.info(f"  CFG值: {cfg}, 步数: {steps}")

        # 参数验证
        if steps < 5 or steps > 30:
            raise click.BadParameter("推理步数必须在5-30之间")

        if cfg < 1.0 or cfg > 10.0:
            raise click.BadParameter("CFG值必须在1.0-10.0之间")

        # 创建引擎实例
        engine = TTSEngine(device=device.lower())

        # 执行语音生成
        result = engine.generate(
            text=text,
            reference_audio_path=audio,
            output_path=output,
            cfg_value=cfg,
            inference_timesteps=steps,
            seed=seed,
        )

        # 输出结果
        if result['success']:
            click.echo("\n" + "=" * 50)
            click.echo("✅ 成功！")
            click.echo("=" * 50)
            click.echo(f"\n📁 输出文件: {result['output_file']}")
            click.echo(f"⏱️  音频时长: {result['duration']:.2f}秒")
            click.echo(f"🔊 采样率: {result['sample_rate']}Hz")

            if audio:
                click.echo(f"🎤 已使用参考音频进行音色克隆")
            else:
                click.echo(f"ℹ️  使用默认音色（未进行克隆）")

            sys.exit(0)

        else:
            click.echo("\n" + "=" * 50, err=True)
            click.echo("❌ 失败", err=True)
            click.echo("=" * 50, err=True)
            click.echo(f"\n错误: {result.get('error', '未知错误')}", err=True)
            sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\n\n⚠️ 用户中断操作", err=True)
        sys.exit(130)

    except Exception as e:
        click.echo(f"\n❌ 程序出错: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
