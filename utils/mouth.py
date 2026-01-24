import asyncio
import edge_tts
import pygame
import os
import time

# 声音选择
VOICE = "zh-CN-XiaoyiNeural"
#VOICE = "ja-JP-NanamiNeural"
LOCK_FILE = 'atri_is_speaking.lock'

LOCK_PATH = os.path.dirname(os.path.abspath(__file__))

async def generate_voice(text, filename=os.path.join(LOCK_PATH,'ffmpeg','reply.mp3')):
    #print(filename)
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(filename)

def play_audio(filename=os.path.join(LOCK_PATH,'ffmpeg','reply.mp3')):
    """
    智能播放函数：
    1. 如果有声卡 (Windows/Mac)，用 pygame 播放。
    2. 如果是 WSL (无声卡)，尝试调用 Windows 系统命令播放。
    """
    if not os.path.exists(filename):
        return
    
    with open(LOCK_FILE, 'w') as f:
        f.write('speaking')
    try:
        #print('讲话：')
        os.system(f"{os.path.join(LOCK_PATH,'ffmpeg')}/ffplay.exe -nodisp -autoexit -hide_banner {filename} >/dev/null 2>&1")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

def speak(text):
    # 生成
    asyncio.run(generate_voice(text))
    # 播放
    play_audio()

if __name__ == "__main__":
    print("正在测试声音...")
    speak("こんにちは、アトリです。")
    # speak("你好，我是高性能机器人。")