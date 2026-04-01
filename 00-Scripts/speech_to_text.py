#!/usr/bin/env python3
"""
语音识别工具 - 使用阿里云 DashScope ASR 模型
"""

import sys
import os

# 检查文件
audio_file = "/home/kyj/.openclaw/media/inbound/file_68---bf31f94c-bc65-47c8-a29a-3cf9aa3d2e03.ogg"

if not os.path.exists(audio_file):
    print(f"❌ 文件不存在：{audio_file}")
    sys.exit(1)

print(f"📄 音频文件：{audio_file}")
print(f"📊 文件大小：{os.path.getsize(audio_file) / 1024:.1f} KB")
print()
print("💡 提示：阿里云 ASR API 需要公网可访问的 URL")
print()
print("解决方案：")
print("1. 将文件上传到临时存储（如阿里云 OSS）")
print("2. 使用本地语音识别库（如 faster-whisper）")
print("3. 使用 OpenClaw 的 tts 工具（如果支持语音识别）")
print()
print("当前配置：")
print("- 模型：qwen3-asr-flash")
print("- API Key：sk-e8b53592ebe841f28a03d4d54024761c")
print("- 语言：zh-CN")
