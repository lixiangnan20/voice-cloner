/**
 * Voice Cloner Web Interface - JavaScript
 * 处理文件上传、表单提交、结果展示等交互逻辑
 */

// ========== Global State ==========
let state = {
    audioFile: null,          // 上传的音频文件名
    audioFileName: '',        // 原始文件名
    isProcessing: false       // 是否正在处理中
};

// ========== DOM Elements ==========
const dropZone = document.getElementById('dropZone');
const audioInput = document.getElementById('audioInput');
const textInput = document.getElementById('textInput');
const charCount = document.getElementById('charCount');
const cloneBtn = document.getElementById('cloneBtn');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const resultSection = document.getElementById('resultSection');

// ========== Event Listeners ==========

// 文件选择变化
audioInput.addEventListener('change', handleFileSelect);

// 点击上传区域触发文件选择（解决label+hidden input兼容性问题）
dropZone.addEventListener('click', (e) => {
    // 避免重复触发（如果点击的是label）
    if (e.target.tagName !== 'INPUT') {
        audioInput.click();
    }
});

// 拖拽上传
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        audioInput.files = files;
        handleFileSelect();
    }
});

// 文本输入字数统计
textInput.addEventListener('input', () => {
    charCount.textContent = textInput.value.length;
});

// ========== Functions ==========

/**
 * 处理文件选择
 */
function handleFileSelect() {
    const file = audioInput.files[0];
    if (!file) return;

    // 显示加载状态
    showUploadLoading(true);

    // 创建FormData
    const formData = new FormData();
    formData.append('audio', file);

    // 上传文件到服务器
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 保存文件信息
            state.audioFile = data.data.filename;
            state.audioFileName = data.data.original_name;

            // 更新UI
            showAudioInfo(data.data);
            updateStep(1, 'completed');
            updateStep(2, 'active');

            console.log('✅ 音频上传成功:', data.data);
        } else {
            showError(data.error || '上传失败');
        }
    })
    .catch(error => {
        console.error('❌ 上传失败:', error);
        showError('网络错误，请重试');
    })
    .finally(() => {
        showUploadLoading(false);
    });
}

/**
 * 显示音频信息
 */
function showAudioInfo(info) {
    document.getElementById('audioInfo').style.display = 'block';
    document.getElementById('fileName').textContent = info.original_name;
    document.getElementById('duration').textContent = `${info.duration.toFixed(1)} 秒`;
    document.getElementById('sampleRate').textContent = `${info.sample_rate} Hz`;
    document.getElementById('channels').textContent = info.channels === 1 ? '单声道' : '立体声';

    // 隐藏上传区域提示
    dropZone.querySelector('.upload-text').textContent = '文件已上传 ✓';
}

/**
 * 移除已上传的音频
 */
function removeAudio() {
    state.audioFile = null;
    state.audioFileName = '';
    audioInput.value = '';

    document.getElementById('audioInfo').style.display = 'none';
    document.getElementById('audioPreview').style.display = 'none';
    dropZone.querySelector('.upload-text').textContent = '点击或拖拽上传音频文件';

    updateStep(1, 'active');
    updateStep(2, '');
}

/**
 * 设置示例文本
 */
function setText(text) {
    textInput.value = text;
    charCount.textContent = text.length;
}

/**
 * 插入示例文本（按钮调用）
 */
function insertExample() {
    const examples = [
        '大家好，欢迎使用AI语音克隆工具！这是一个基于VoxCPM模型的零样本语音克隆演示。',
        '今天天气真不错，适合出去走走。希望你能喜欢这个工具！',
        '人工智能正在改变我们的生活方式，语音合成技术让机器也能像人一样说话。',
        '你好世界！这是语音克隆测试文本，用于验证音色克隆效果。'
    ];

    const randomExample = examples[Math.floor(Math.random() * examples.length)];
    setText(randomExample);
}

/**
 * 开始语音克隆
 */
async function startClone() {
    // 验证输入
    if (!state.audioFile) {
        showError('请先上传参考音频文件');
        return;
    }

    const text = textInput.value.trim();
    if (!text) {
        showError('请输入要朗读的文本');
        textInput.focus();
        return;
    }

    if (text.length > 500) {
        showError('文本长度超过500字符限制');
        return;
    }

    // 防止重复提交
    if (state.isProcessing) return;

    state.isProcessing = true;
    updateStep(2, 'completed');
    updateStep(3, 'active');

    // 显示进度
    showProgress(true);
    setButtonLoading(true);

    try {
        const requestData = {
            audio_file: state.audioFile,
            text: text
        };

        console.log('🚀 开始语音克隆:', requestData);

        // 调用API
        const response = await fetch('/api/clone', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();

        if (data.success) {
            updateProgress(100, '生成完成！');
            updateStep(3, 'completed');

            // 显示结果
            setTimeout(() => {
                showResult(data.data);
            }, 500);
        } else {
            throw new Error(data.error || '克隆失败');
        }

    } catch (error) {
        console.error('❌ 克隆失败:', error);
        showError(error.message || '处理过程中出现错误');
        updateStep(3, '');

    } finally {
        state.isProcessing = false;
        showProgress(false);
        setButtonLoading(false);
    }
}

/**
 * 显示结果
 */
function showResult(data) {
    resultSection.style.display = 'block';

    // 填充数据
    document.getElementById('resultText').textContent = data.text;
    document.getElementById('resultSize').textContent = `${data.file_size_mb} MB`;
    document.getElementById('resultTime').textContent = data.created_at;

    // 设置播放器
    const audioPlayer = document.getElementById('resultAudio');
    audioPlayer.src = `/api/audio/${data.output_file}`;

    // 设置下载链接
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.href = `/api/download/${data.output_file}`;

    // 滚动到结果区域
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    console.log('✅ 结果显示完成:', data);
}

/**
 * 重置所有状态
 */
function resetAll() {
    removeAudio();
    textInput.value = '';
    charCount.textContent = '0';
    resultSection.style.display = 'none';

    updateStep(1, 'active');
    updateStep(2, '');
    updateStep(3, '');

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ========== UI Helper Functions ==========

/**
 * 显示/隐藏上传加载状态
 */
function showUploadLoading(show) {
    const uploadText = dropZone.querySelector('.upload-text');
    if (show) {
        uploadText.innerHTML = '<span class="loading-spinner"></span>正在上传...';
        dropZone.style.pointerEvents = 'none';
    } else {
        uploadText.textContent = '点击或拖拽上传音频文件';
        dropZone.style.pointerEvents = 'auto';
    }
}

/**
 * 显示/隐藏进度条
 */
function showProgress(show) {
    progressSection.style.display = show ? 'block' : 'none';
    if (show) {
        updateProgress(0, '正在预处理音频...');
    }
}

/**
 * 更新进度条
 */
function updateProgress(percent, text) {
    progressBar.style.width = `${percent}%`;
    progressText.textContent = text;

    // 根据阶段更新文字
    if (percent < 30) {
        progressText.textContent = '📁 正在预处理音频...';
    } else if (percent < 60) {
        progressText.textContent = '🎤 正在提取音色特征...';
    } else if (percent < 90) {
        progressText.textContent = '🔊 正在生成语音...';
    } else {
        progressText.textContent = '✅ 生成完成！';
    }
}

/**
 * 设置按钮加载状态
 */
function setButtonLoading(loading) {
    cloneBtn.disabled = loading;
    if (loading) {
        cloneBtn.innerHTML = '<span class="loading-spinner"></span>正在生成...';

        // 模拟进度更新
        simulateProgress();
    } else {
        cloneBtn.innerHTML = '<span class="btn-icon">🚀</span>开始克隆语音';
    }
}

/**
 * 模拟进度动画
 */
function simulateProgress() {
    let progress = 0;
    const interval = setInterval(() => {
        if (!state.isProcessing || progress >= 90) {
            clearInterval(interval);
            return;
        }

        progress += Math.random() * 15;
        progress = Math.min(progress, 89); // 最大到90%，等待实际完成
        updateProgress(progress, '');

    }, 800);
}

/**
 * 更新步骤指示器
 */
function updateStep(stepNum, status) {
    const step = document.getElementById(`step${stepNum}`);
    if (!step) return;

    step.classList.remove('active', 'completed');
    if (status === 'active') {
        step.classList.add('active');
    } else if (status === 'completed') {
        step.classList.add('completed');
    }
}

/**
 * 显示错误消息
 */
function showError(message) {
    alert(`⚠️ ${message}`);
    console.error('❌ 错误:', message);
}

// ========== Keyboard Shortcuts ==========
document.addEventListener('keydown', (e) => {
    // Ctrl+Enter 或 Cmd+Enter 提交
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (!state.isProcessing) {
            startClone();
        }
    }
});

// ========== Initialize ==========
console.log('🎤 Voice Cloner Web Interface Loaded');
console.log('💡 快捷键: Ctrl+Enter 快速开始克隆');
