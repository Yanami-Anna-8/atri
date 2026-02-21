import asyncio
import edge_tts
import pygame
import os
import time
import threading
import queue
import subprocess #启动播放器进程
import random

# 声音选择
VOICE = "zh-CN-XiaoyiNeural"
#VOICE = "ja-JP-NanamiNeural"
LOCK_FILE = 'atri_is_speaking.lock'

LOCK_PATH = os.path.dirname(os.path.abspath(__file__))


class AtriActor(threading.Thread):
    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.daemon = True #设置为守护线程，主程序退出它也退出
        self.running = True

    def add_sentence(self, text):
        self.queue.put(text)

    def run(self):
        #线程启动后一直在后台做的事情
        while self.running:
            try:
                text = self.queue.get(timeout=1) #取出一段话，没有就等待
                self._perform(text) #执行
                self.queue.task_done() #标记完成任务
            except queue.Empty:
                continue
            except Exception as e:
                print(f'Actor Error: {e}')
        
    def _perform(self, text):
        if not text.strip(): return

        filename = f'temp_{int(time.time())}_{random.randint(100,999)}.mp3'

        try:
            asyncio.run(self._generate_file(text, filename)) #生成音频
            with open(LOCK_FILE, 'w') as f : f.write('speaking') #上锁

            player_process = subprocess.Popen( #Popen是非阻塞的，代码会立刻往下走，需要chmod +x ffplay.exe
                [f'{os.path.join(LOCK_PATH,"ffmpeg")}/ffplay.exe', '-nodisp', '-autoexit', '-hide_banner', filename],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            typing_speed = random.uniform(0.1, 0.2) #每秒4-5个字
            for char in text:
                print(char, end='', flush=True)
                time.sleep(typing_speed)

                if player_process.poll() is not None:
                    typing_speed = 0 #语音结束后，全部输出不暂停
            
            player_process.wait() #等待音频全部播完，防止字打完声音还在响，下一句就来了
        finally:
            if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
            if os.path.exists(filename) : os.remove(filename)
    
    async def _generate_file(self, text, filename):
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(filename)
 

actor = AtriActor()
actor.start() #启动线程

#创建外部接口
def queue_speak(text):
    actor.add_sentence(text)

#所有对话都说完，关机
def wait_finish():
    actor.queue.join()



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