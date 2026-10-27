import asyncio
import edge_tts
import pygame
import os
import time
import threading
import queue
import subprocess #启动播放器进程
import random
import re
import soundfile as sf

from .link import emit_chat, emit_sentence, emit_mouth, emit_state, emit_emote
from . import voice as voice_module
LOCK_FILE = 'atri_is_speaking.lock'

LOCK_PATH = os.path.dirname(os.path.abspath(__file__))


class AtriActor(threading.Thread):
    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.daemon = True #设置为守护线程，主程序退出它也退出
        self.running = True

    def add_sentence(self, item):
        self.queue.put(item)

    def run(self):
        #线程启动后一直在后台做的事情
        while self.running:
            try:
                text, tts_text, echo = self.queue.get(timeout=1)
                self._perform(text, tts_text, echo) #执行
                self.queue.task_done() #标记完成任务
            except queue.Empty:
                continue
            except Exception as e:
                print(f'Actor Error: {e}')
        
    def _perform(self, text, tts_text=None, echo=True):
        spoken, actions = split_emotes(text)

        if not spoken:
            # 整段都是括号动作，没有可朗读的内容
            if actions:
                emit_emote(actions)
            emit_chat('assistant', text)
            emit_mouth(0.0)
            emit_state('idle')
            return

        filename = f'temp_{int(time.time())}_{random.randint(100,999)}{voice_module.voice.suffix}'
        duration = 0.0
        envelope = []
        lead = 0.0
        sentence_sent = False

        try:
            voice_module.voice.synthesize(tts_text or spoken, filename) #生成音频（只读正文；GPT 模式会先翻译成日语）
            duration, envelope, lead = analyze_audio(filename) #时长 + 50ms 包络 + 开头静音

            with open(LOCK_FILE, 'w') as f : f.write('speaking') #上锁

            player_process = subprocess.Popen( #Popen是非阻塞的，代码会立刻往下走，需要chmod +x ffplay.exe
                # [f'{os.path.join(LOCK_PATH,"ffmpeg")}/ffplay.exe', '-nodisp', '-autoexit', '-hide_banner', filename],
                ['ffplay', '-nodisp', '-autoexit', '-hide_banner', filename],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # 音频开始播放的同时通知桌宠：表情、气泡、口型一起对齐
            if actions:
                emit_emote(actions)
            emit_sentence(spoken, duration, min(lead + 0.12, 0.6))
            emit_state('speaking')
            sentence_sent = True

            self._play_and_print(spoken, duration, envelope, player_process, echo)

            player_process.wait() #等待音频全部播完，防止字打完声音还在响，下一句就来了
        except Exception as exc:
            print(f'Actor Error: {exc}')
            if not sentence_sent:
                emit_chat('assistant', spoken) #没有声音时至少把气泡显示出来
        finally:
            emit_mouth(0.0)
            emit_state('idle')
            if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
            if os.path.exists(filename) : os.remove(filename)

    def _play_and_print(self, text, duration, envelope, player_process, echo=True):
        """按音频时长均匀打字，同时把音量包络推给桌宠。"""
        duration = max(duration, 0.1)
        chars_per_second = len(text) / duration
        started = time.time()
        printed = 0

        while True:
            elapsed = time.time() - started
            if player_process.poll() is not None or elapsed >= duration:
                break

            target = min(len(text), int(elapsed * chars_per_second))
            if echo:
                while printed < target:
                    print(text[printed], end='', flush=True)
                    printed += 1
            else:
                printed = target

            if envelope:
                index = min(len(envelope) - 1, int(elapsed / FRAME_SECONDS))
                emit_mouth(envelope[index])

            time.sleep(0.04)

        if echo and printed < len(text):
            print(text[printed:], end='', flush=True)

 



FRAME_SECONDS = 0.05

BRACKET_RE = re.compile(r'[（(【\[]([^（）()【】\[\]]*)[）)】\]]')


EMOTE_TAGS = [
    '星星眼', '比心', '脸红', '害羞', '生气', '难过', '开心', '惊讶',
    '无语', '吐舌', '口罩', '哭', '笑', '点头', '摇头', '低头', '转头',
    '歪头', '前倾', '后退',
]
EMOTE_TAGS_BY_LENGTH = sorted(EMOTE_TAGS, key=len, reverse=True)


def _split_tags(raw):
    """把括号内容拆成标签；模型偶尔连写成“脸红生气”，这里按词典拆开。"""
    tags = []
    for part in re.split(r'[\s,，、]+', raw):
        if not part:
            continue
        buffer = part
        while buffer:
            matched = next((tag for tag in EMOTE_TAGS_BY_LENGTH if buffer.startswith(tag)), None)
            if matched is None:
                tags.append(buffer)  # 不认识的自由描述保留，交给前端关键词兜底
                break
            tags.append(matched)
            buffer = buffer[len(matched):]
    return tags


def split_emotes(text):
    """把括号里的动作/情绪标签拆出来，返回 (要朗读的正文, 标签列表)。"""
    actions = []
    for match in BRACKET_RE.finditer(text):
        raw = match.group(1).strip()
        if raw:
            actions.extend(_split_tags(raw))
    spoken = BRACKET_RE.sub('', text)
    spoken = re.sub(r'[ \t]+', ' ', spoken).strip()
    return spoken, actions


def analyze_audio(filename):
    """返回 (duration, envelope, lead)，envelope 是每 50ms 一个的 0~1 音量值，lead 是开头静音秒数。"""
    try:
        data, sr = sf.read(filename, dtype='float32', always_2d=True)
        mono = data.mean(axis=1)
        duration = len(mono) / float(sr) if sr else 0.0
        frame = max(1, int(sr * FRAME_SECONDS))
        frame_count = max(1, len(mono) // frame)

        rms = []
        for index in range(frame_count):
            chunk = mono[index * frame:(index + 1) * frame]
            rms.append(float((chunk * chunk).mean()) ** 0.5)

        if rms:
            ordered = sorted(rms)
            peak = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
        else:
            peak = 0.0
        peak = max(peak, 1e-6)
        envelope = [min(1.0, value / peak) for value in rms]

        lead = 0.0
        for index, value in enumerate(envelope):
            if value > 0.12:
                lead = index * FRAME_SECONDS
                break
        return duration, envelope, lead
    except Exception as exc:
        print(f'[MOUTH] 音频分析失败: {exc}')
        return 0.0, [], 0.0

actor = AtriActor()
actor.start() #启动线程

#创建外部接口
def queue_speak(text, tts_text=None, echo=True):
    actor.add_sentence((text, tts_text, echo))

#所有对话都说完，关机
def wait_finish():
    actor.queue.join()



async def generate_voice(text, filename=None):
    if filename is None:
        filename = os.path.join(LOCK_PATH, 'ffmpeg', 'reply' + voice_module.voice.suffix)
    voice_module.voice.synthesize(text, filename)

def play_audio(filename=None):
    if filename is None:
        filename = os.path.join(LOCK_PATH, 'ffmpeg', 'reply' + voice_module.voice.suffix)
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
        # os.system(f"{os.path.join(LOCK_PATH,'ffmpeg')}/ffplay.exe -nodisp -autoexit -hide_banner {filename} >/dev/null 2>&1")
        os.system(f"ffplay -nodisp -autoexit -hide_banner {filename} >/dev/null 2>&1")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

def speak(text):
    filename = os.path.join(LOCK_PATH, 'ffmpeg', 'reply' + voice_module.voice.suffix)
    voice_module.voice.synthesize(text, filename)
    play_audio(filename)

if __name__ == "__main__":
    print("正在测试声音...")
    speak("こんにちは、アトリです。")
    # speak("你好，我是高性能机器人。")