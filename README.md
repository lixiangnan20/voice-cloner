# 🎙️ AI Voice Cloner (MVP v0.1)

基于 **VoxCPM2** 的零样本中文语音克隆工具 - 输入人声音频，克隆音色，朗读文本

## ✨ 功能特点

- **零样本克隆**：仅需30秒参考音频即可提取音色特征
- **高质量输出**：基于VoxCPM2（2B参数模型），生成48kHz高保真语音
- **中文支持**：专门优化的中文TTS合成
- **CPU友好**：无需GPU，支持普通电脑运行
- **简单易用**：一行命令完成语音克隆

## 📦 安装

### 环境要求

- Python 3.10 - 3.13
- Windows / Linux / macOS
- FFmpeg（Windows用户需单独安装，见下方说明）

### 快速安装

```bash
# 1. 克隆或下载本项目
cd voice-cloner

# 2. 创建虚拟环境（推荐）
python -m venv venv

# Windows激活:
venv\Scripts\activate

# Linux/Mac激活:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

> **首次安装会自动下载VoxCPM2模型权重（约2GB），请保持网络畅通**

### Windows额外配置：FFmpeg安装

**方法一（推荐）：使用choco包管理器**
```bash
choco install ffmpeg
```

**方法二：手动安装**
1. 访问 https://ffmpeg.org/download.html
2. 下载Windows版本并解压
3. 将 `bin` 目录添加到系统PATH环境变量

验证安装：
```bash
ffmpeg -version
```

## 🚀 使用方法

### 🌐 Web界面（推荐，更便捷）

#### 快速启动（Windows）

双击运行：
```
start-web.bat
```

或命令行启动：
```bash
# 1. 激活虚拟环境
venv\Scripts\activate

# 2. 启动Web服务器
python app.py
```

访问地址：**http://127.0.0.1:5000**

#### Web界面功能特点

✨ **现代化UI设计**
- 响应式布局，支持桌面和移动端
- 拖拽上传音频文件
- 实时进度显示
- 音频播放器集成
- 一键下载生成结果

🎯 **操作流程**
1. **步骤1 - 上传音频**：点击上传区域或拖拽音频文件（支持WAV/MP3/OGG/FLAC）
2. **步骤2 - 输入文本**：在文本框输入要朗读的中文内容（最多500字）
3. **步骤3 - 生成语音**：点击"开始克隆语音"按钮，等待约7秒
4. **查看结果**：在线试听生成的语音，可一键下载WAV文件

💡 **快捷操作**
- 使用示例文本按钮快速填充常用句子
- Ctrl+Enter快捷键快速开始克隆
- 字数实时统计

### 💻 命令行工具 (CLI)

```bash
# 克隆音色 + 文本转语音
python clone.py --audio reference.wav --text "你好世界" --output result.wav
```

### 参数说明

| 参数 | 缩写 | 说明 | 默认值 | 必填 |
|------|------|------|--------|------|
| `--audio` | `-a` | 参考音频文件路径（wav/mp3） | 无 | 否 |
| `--text` | `-t` | 待合成的中文文本 | 无 | ✅ 是 |
| `--output` | `-o` | 输出WAV文件路径 | 自动生成 | 否 |
| `--device` | `-d` | 推理设备 (cpu/cuda/mps) | cpu | 否 |
| `--cfg` | 无 | CFG引导尺度 (1-10) | 2.0 | 否 |
| `--steps` | `-s` | 推理步数 (5-30) | 10 | 否 |
| `--seed` | 无 | 随机种子 | 随机 | 否 |
| `--verbose` | `-v` | 显示详细日志 | 关闭 | 否 |

### 使用示例

#### 示例1: 完整的语音克隆流程
```bash
python clone.py \
  --audio my_voice.wav \
  --text "今天天气真好，适合出去散步。" \
  --output cloned_voice.wav
```

#### 示例2: 仅TTS（不克隆，使用默认音色）
```bash
python clone.py --text "你好，欢迎使用AI语音克隆工具！" -o output.wav
```

#### 示例3: 调整生成质量
```bash
# 更高质量但更慢（步数=20）
python clone.py -a ref.wav -t "测试文本" -o high_quality.wav --steps 20

# 更稳定但多样性较低（CFG=4.0）
python clone.py -a ref.wav -t "测试文本" -o stable.wav --cfg 4.0

# 可复现结果（固定随机种子）
python clone.py -a ref.wav -t "测试文本" -o reproducible.wav --seed 42
```

#### 示例4: GPU加速（如果有NVIDIA显卡）
```bash
python clone.py -a ref.wav -t "测试文本" -o output.wav --device cuda
```

#### 示例5: 详细日志模式（调试用）
```bash
python clone.py -v -a ref.wav -t "测试文本"
```

## 🔧 参考音频最佳实践

为了获得最佳克隆效果，请注意以下几点：

### ✅ 推荐做法
- **清晰录音**：无背景噪音、无回声
- **时长适中**：5-20秒最佳（最长不超过30秒）
- **正常语速**：不要过快或过慢
- **自然表达**：朗读或对话均可，避免夸张语气
- **单说话人**：只包含一个声音

### ❌ 避免情况
- 背景音乐或噪音
- 过短音频（<3秒）或过长音频（>30秒）
- 多人对话
- 极低音量或失真的录音
- 歌唱声（建议使用说话声）

### 支持的格式
- 输入：WAV, MP3
- 输出：WAV（48kHz 16bit PCM）

## 📂 项目结构

```
voice-cloner/
├── README.md              # 本文件
├── requirements.txt       # Python依赖列表
├── config.py             # 配置参数
├── clone.py              # 主程序入口（CLI）
├── audio_processor.py    # 音频预处理模块
├── voice_cloner.py       # 核心克隆模块（VoxCPM2封装）
├── tts_engine.py         # TTS引擎（完整流程整合）
└── utils/                # 工具模块
    ├── __init__.py
    ├── logger.py         # 日志工具
    └── file_utils.py     # 文件操作工具
```

## ⚡ 性能参考（CPU模式）

| 测试项目 | 数值 |
|---------|------|
| 模型加载时间 | ~10-20秒（首次） |
| 音频生成速度 | ~5-15秒/句（取决于长度和CPU性能） |
| 内存占用 | ~2-3 GB |
| RTF（实时因子） | ~0.5-1.5 |

*注：使用GPU可显著提升推理速度*

## 🛠️ 开发与调试

### 单独测试各模块

```bash
# 测试音频处理器
python audio_processor.py

# 测试语音克隆器
python voice_cloner.py

# 测试TTS引擎
python tts_engine.py
```

### 常见问题

#### Q1: ImportError: No module named 'voxcpm'
**A**: 请确保已安装所有依赖：`pip install -r requirements.txt`

#### Q2: 模型加载很慢/失败
**A**: 首次运行需要从HuggingFace下载约2GB模型权重。如果网络不稳定：
- 尝试使用代理
- 或手动从 [ModelScope](https://modelscope.cn/models/OpenBMB/VoxCPM2) 下载

#### Q3: 生成的音频质量不好
**A**:
1. 检查参考音频质量（清晰、无噪音、5-20秒）
2. 尝试增加 `--steps` 参数到15-25
3. 多生成几次选择最佳结果（VoxCPM有随机性）

#### Q4: Windows下FFmpeg相关错误
**A**: 请确保已正确安装FFmpeg并添加到PATH（见上方安装说明）

#### Q5: CPU模式下内存不足
**A**: VoxCPM2需要约2GB内存。如果内存不足：
- 关闭其他程序释放内存
- 或考虑升级到GPU版本

## 📄 许可证

本项目采用 MIT 许可证。

VoxCPM2 采用 Apache-2.0 许可证（详见 https://github.com/OpenBMB/VoxCPM）

## ⚠️ 免责声明

本工具仅供学习和研究用途。使用者应遵守当地法律法规：

- **禁止用于身份冒充、欺诈等非法活动**
- **AI生成内容应当明确标注**
- **尊重他人隐私权和肖像权**

开发者不对滥用本工具造成的任何后果承担责任。

## 🙏 致谢

- [VoxCPM](https://github.com/OpenBMB/VoxCPM) - 出色的开源多语言TTS模型
- [PyTorch](https://pytorch.org/) - 强大的深度学习框架
- [librosa](https://librosa.org/) - 专业音频处理库

---

**版本**: MVP v0.1
**更新日期**: 2026-07-06
**状态**: ✅ 可用（MVP阶段）

如有问题或建议，欢迎提Issue！
