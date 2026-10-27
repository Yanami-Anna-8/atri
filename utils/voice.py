"""语音后端：默认中文 edge-tts / 日语音色 GPT-SoVITS。

GPT-SoVITS 只接受日语文本，所以中文回复会先经过 DeepSeek 翻译；
预设台词则直接写日语，跳过翻译。
"""

import asyncio
import os
import re
import subprocess
import threading

import edge_tts
import requests

from .api import client

EDGE_VOICE = 'zh-CN-XiaoyiNeural'

# GPT-SoVITS api.py 启动参数里设置的参考音频
GPT_REF_WAV = 'cankao.wav'
GPT_REF_TEXT = 'これがキスなのですね。学習不足でした'
GPT_REF_LANG = 'ja'

JAPANESE_RE = re.compile(r'[\u3040-\u30ff]')


def is_japanese(text):
    return bool(JAPANESE_RE.search(text))


def _windows_host_ip():
    """WSL2 NAT 模式下，访问 Windows 宿主要用默认网关地址。"""
    try:
        output = subprocess.check_output(['ip', 'route', 'show', 'default'], text=True)
        for line in output.splitlines():
            if 'via' in line:
                return line.split('via', 1)[1].split()[0]
    except Exception:
        pass
    return '127.0.0.1'


class EdgeVoice:
    label = '默认中文（edge-tts）'
    suffix = '.mp3'

    def synthesize(self, text, filename):
        asyncio.run(self._run(text, filename))

    async def _run(self, text, filename):
        communicate = edge_tts.Communicate(text, EDGE_VOICE)
        await communicate.save(filename)


class GPTSoVITSVoice:
    label = '日语音色（GPT-SoVITS）'
    suffix = '.wav'

    def __init__(self):
        self.api_url = os.environ.get('GPT_SOVITS_URL') or f'http://{_windows_host_ip()}:9880'
        self._translation_cache = {}

    def synthesize(self, text, filename):
        # 预设台词本来就是日语，直接合成；中文回复先翻译
        japanese = text if is_japanese(text) else self.translate(text)
        response = requests.post(
            self.api_url,
            json={
                'refer_wav_path': GPT_REF_WAV,
                'prompt_text': GPT_REF_TEXT,
                'prompt_language': GPT_REF_LANG,
                'text': japanese,
                'text_language': 'ja',
            },
            timeout=180,
        )
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)

    def translate(self, text):
        cached = self._translation_cache.get(text)
        if cached:
            return cached
        response = client.chat.completions.create(
            model='deepseek-chat',
            messages=[
                {
                    'role': 'system',
                    'content': '你是翻译。把用户给的中文翻译成自然、口语化的日语。只输出日语译文，不要解释，不要加引号。',
                },
                {'role': 'user', 'content': text},
            ],
            temperature=0.3,
            max_tokens=300,
            stream=False,
        )
        japanese = response.choices[0].message.content.strip()
        if japanese:
            self._translation_cache[text] = japanese
        return japanese

    def warm_up(self):
        """后台预热：第一次推理可能要几十秒，提前打一发短句。"""
        def run():
            try:
                requests.post(
                    self.api_url,
                    json={
                        'refer_wav_path': GPT_REF_WAV,
                        'prompt_text': GPT_REF_TEXT,
                        'prompt_language': GPT_REF_LANG,
                        'text': 'こんにちは。',
                        'text_language': 'ja',
                    },
                    timeout=180,
                )
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()


edge_voice = EdgeVoice()
gpt_voice = GPTSoVITSVoice()

voice = edge_voice


def configure_voice(name):
    global voice
    voice = gpt_voice if name == 'gpt' else edge_voice
    if voice is gpt_voice:
        gpt_voice.warm_up()
    print(f'[VOICE] 当前音色: {voice.label}')
    return voice