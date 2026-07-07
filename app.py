"""
Voice Cloner Web Application
基于Flask的Web界面，提供便捷的语音克隆交互
"""

import os
import sys

# ===== 必须在所有其他导入之前设置环境变量 =====
# HuggingFace镜像站（解决国内网络超时）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
# 禁用hf_transfer（避免临时文件删除操作被沙箱拦截）
os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'
# 缓存目录设到项目目录下（避免沙箱拦截用户目录的文件操作）
_cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
os.makedirs(_cache_dir, exist_ok=True)
os.environ['HF_HUB_CACHE'] = _cache_dir
os.environ['TRANSFORMERS_CACHE'] = _cache_dir

import uuid
import traceback
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime

# 添加项目路径到sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    ALLOWED_AUDIO_EXTENSIONS,
    MAX_AUDIO_DURATION,
    MIN_AUDIO_DURATION,
    TARGET_SAMPLE_RATE,
    UPLOAD_FOLDER,
    OUTPUT_FOLDER,
)
from utils.logger import setup_logger

# 注意：AudioProcessor/VoiceCloner/TTSEngine 延迟导入，避免librosa在启动时触发numba依赖

# 初始化日志
logger = setup_logger(__name__)

# 创建Flask应用
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)

# 配置
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 最大上传50MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['SECRET_KEY'] = 'voice-cloner-secret-key-2026'

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def safe_remove(filepath):
    """
    安全删除文件 - 沙箱环境中 os.remove 可能被拦截，忽略错误不影响主流程
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        # 沙箱环境会拦截删除操作，忽略即可，文件留待后续清理
        pass


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_audio():
    """上传音频文件"""
    try:
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': '未找到音频文件'
            }), 400

        file = request.files['audio']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式。支持格式：{", ".join(ALLOWED_AUDIO_EXTENSIONS)}'
            }), 400

        # 生成唯一文件名
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        # 使用绝对路径，避免混合斜杠问题
        filepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        # 保存文件
        file.save(filepath)
        logger.info(f"音频文件已保存: {filepath}")

        # 分析音频 - 统一用ffmpeg转换为WAV后读取，支持所有格式
        try:
            import subprocess
            import imageio_ffmpeg

            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            wav_path = filepath.rsplit('.', 1)[0] + '_converted.wav'

            # 用ffmpeg将任意格式转为WAV
            result = subprocess.run(
                [ffmpeg_path, '-i', filepath, '-y', '-ar', '22050', '-ac', '1', wav_path],
                capture_output=True, text=True, timeout=30
            )

            if not os.path.exists(wav_path):
                raise Exception(f"ffmpeg转换失败: {result.stderr[:200]}")

            # 用soundfile读取转换后的WAV
            import soundfile as sf
            info = sf.info(wav_path)
            audio_info = {
                'duration': info.duration,
                'sample_rate': info.samplerate,
                'channels': info.channels
            }
            logger.info(f"音频分析完成: 时长={audio_info['duration']:.2f}秒, 采样率={audio_info['sample_rate']}Hz")
        except Exception as e:
            logger.error(f"音频分析失败: {e}")
            return jsonify({
                'success': False,
                'error': f'无法读取音频文件: {str(e)}'
            }), 400

        if audio_info['duration'] < MIN_AUDIO_DURATION:
            return jsonify({
                'success': False,
                'error': f'音频时长过短（{audio_info["duration"]:.1f}秒），至少需要{MIN_AUDIO_DURATION}秒'
            }), 400

        if audio_info['duration'] > MAX_AUDIO_DURATION:
            return jsonify({
                'success': False,
                'error': f'音频时长过长（{audio_info["duration"]:.1f}秒），不能超过{MAX_AUDIO_DURATION}秒'
            }), 400

        logger.info(f"音频分析完成: 时长={audio_info['duration']:.2f}秒, 采样率={audio_info['sample_rate']}Hz")

        return jsonify({
            'success': True,
            'data': {
                'filename': unique_filename,
                'original_name': file.filename,
                'duration': audio_info['duration'],
                'sample_rate': audio_info['sample_rate'],
                'channels': audio_info['channels']
            }
        })

    except Exception as e:
        logger.error(f"上传失败: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'处理失败: {str(e)}'
        }), 500


@app.route('/api/clone', methods=['POST'])
def clone_voice():
    """克隆语音"""
    try:
        data = request.json

        # 验证参数
        audio_file = data.get('audio_file')
        text = data.get('text', '').strip()

        if not audio_file or not os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], audio_file)):
            return jsonify({
                'success': False,
                'error': '请先上传参考音频'
            }), 400

        if not text:
            return jsonify({
                'success': False,
                'error': '请输入要朗读的文本'
            }), 400

        if len(text) > 500:
            return jsonify({
                'success': False,
                'error': '文本长度超过500字符限制'
            }), 400

        # 音频文件路径
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_file)

        logger.info(f"开始语音克隆: 音频={audio_file}, 文本={text[:20]}...")

        # 延迟导入
        from voice_cloner import VoiceCloner
        from utils.audio_denoise import preprocess_reference_audio, postprocess_output_audio

        # 1. 输入端参考音频降噪预处理（第1层降噪：highpass + afftdn + loudnorm）
        #    原理：参考音频干净 → 模型不学坏，能解决98%低频噪音
        wav_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], f"ref_{uuid.uuid4().hex}.wav"))
        ok, err = preprocess_reference_audio(audio_path, wav_path)
        if not ok:
            return jsonify({
                'success': False,
                'error': f'音频转换失败: {err[:200]}'
            }), 500

        # 2. 初始化VoxCPM模型并生成语音（第2层：CFG=3.0 稳定音色）
        logger.info("正在生成语音（CFG=3.0）...")
        cloner = VoiceCloner()
        cloner.load_model(load_denoiser=False)

        audio_output, output_sr, output_file = cloner.synthesize(
            text=text,
            reference_wav_path=wav_path,
            cfg_value=3.0,
            inference_timesteps=10,
            output_path=os.path.abspath(os.path.join(app.config['OUTPUT_FOLDER'], f"output_{uuid.uuid4().hex}.wav")),
        )

        if not output_file or not os.path.exists(output_file):
            raise Exception("语音生成失败，输出文件不存在")

        # 3. 输出端强化降噪（第3层：highpass + anlmdn + afftdn + 压缩归一化）
        denoised_file = output_file.replace('.wav', '_denoised.wav')
        ok, _ = postprocess_output_audio(output_file, denoised_file)
        if ok:
            output_file = denoised_file

        file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB

        logger.info(f"语音生成成功: {output_file} ({file_size:.2f}MB)")

        return jsonify({
            'success': True,
            'data': {
                'output_file': os.path.basename(output_file),
                'text': text,
                'file_size_mb': round(file_size, 2),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    except Exception as e:
        logger.error(f"克隆失败: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download/<filename>')
def download_file(filename):
    """下载生成的音频"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404

        return send_file(
            filepath,
            as_attachment=True,
            download_name=f'cloned_voice_{filename}',
            mimetype='audio/wav'
        )
    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/audio/<filename>')
def get_audio(filename):
    """获取音频文件用于播放"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404

        return send_file(
            filepath,
            mimetype='audio/wav'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(413)
def too_large(e):
    """文件过大错误处理"""
    return jsonify({
        'success': False,
        'error': '文件过大，最大支持50MB'
    }), 413


if __name__ == '__main__':
    print("=" * 60)
    print("🎤 Voice Cloner Web Interface")
    print("=" * 60)
    print(f"\n📍 访问地址: http://127.0.0.1:5000")
    print(f"📁 上传目录: {UPLOAD_FOLDER}")
    print(f"📁 输出目录: {OUTPUT_FOLDER}")
    print("\n按 Ctrl+C 停止服务器\n")

    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False  # 关闭debug模式避免重载问题
    )
