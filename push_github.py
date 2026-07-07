# -*- coding: utf-8 -*-
"""
一键推送代码到GitHub
用法: python push_github.py
"""
import requests, base64, os, time, sys

# ===== 配置 =====
TOKEN = 'ghp_你的Token'  # 替换为你的GitHub Token
OWNER = 'lixiangnan20'
REPO = 'voice-cloner'
SKIP_DIRS = {'.git', '__pycache__', 'cache', 'venv', 'uploads', 'outputs', 'logs', 'env', '.venv'}
SKIP_EXT = ('.pyc', '.pyo', '.log', '.tmp', '.bak', '.json')
SKIP_FILES = {'test_40s.wav', 'test_40s_converted.wav', 'test_audio.wav', 'test_mp3.mp3', 'test_short.wav', 'push_github.py'}
# ================

HEADERS = {'Authorization': f'token {TOKEN}', 'Accept': 'application/vnd.github+json'}

def get_file_sha(relpath):
    """获取GitHub上已有文件的SHA（更新时需要）"""
    url = f'https://api.github.com/repos/{OWNER}/{REPO}/contents/{relpath}'
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 200:
        return r.json().get('sha')
    return None

def push_file(filepath, relpath):
    """推送/更新单个文件"""
    with open(filepath, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')

    # 检查文件是否已存在（需要SHA才能更新）
    sha = get_file_sha(relpath)

    url = f'https://api.github.com/repos/{OWNER}/{REPO}/contents/{relpath}'
    data = {
        'message': f'Update {relpath}',
        'content': content,
        'branch': 'main'
    }
    if sha:
        data['sha'] = sha  # 已存在的文件需要提供SHA

    r = requests.put(url, headers=HEADERS, json=data, timeout=60)
    return r.status_code in (200, 201), r.text[:100] if r.status_code not in (200, 201) else 'OK'

# 收集文件
files_to_push = []
for root, dirs, filenames in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for f in filenames:
        if f in SKIP_FILES or f.startswith('_') or f.endswith(SKIP_EXT):
            continue
        filepath = os.path.join(root, f)
        relpath = os.path.relpath(filepath, '.').replace(os.sep, '/')
        files_to_push.append((filepath, relpath))

print(f'共 {len(files_to_push)} 个文件\n')

success, failed = 0, 0
for i, (filepath, relpath) in enumerate(files_to_push, 1):
    ok, msg = push_file(filepath, relpath)
    print(f'[{i}/{len(files_to_push)}] {"✅" if ok else "❌"} {relpath} - {msg}')
    if ok:
        success += 1
    else:
        failed += 1
    time.sleep(0.5)

print(f'\n完成！成功: {success}, 失败: {failed}')
