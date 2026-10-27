"""点击互动和聊天框输入：预设语音不经过 AI，也不写入记忆。"""

import random

from . import voice as voice_module
from .link import link
from .mouth import queue_speak


HEAD_LINES = [
    ('诶？夏生先生，摸头也是没用的哦……不过，谢谢啦。',
     'え？夏生さん、頭を撫でても何も出ませんよ……でも、ありがとうございます。'),
    ('唔……头发会乱的啦！不过，只有这一次哦。',
     'う……髪が乱れちゃいます！でも、今回だけですからね。'),
    ('真是的，把我当小孩子吗……嘛，感觉还不坏。',
     'もう、子供扱いしないでください……まあ、悪くないですけど。'),
]
FACE_LINES = [
    ('呀！做、做什么啦！脸会被戳坏的！',
     'やっ！な、何をするんですか！顔が壊れちゃいます！'),
    ('哼，就算戳我的脸，我也不会承认你厉害的！',
     'ふん、頬をつついたって、私は高性能なんですから。'),
    ('喂！高性能机器人的脸可不是玩具哦！',
     'ちょっと！高性能ロボットの顔は玩具じゃないんですよ！'),
]


def handle_client_message(event):
    event_type = event.get('type')

    if event_type == 'user_message':
        text = (event.get('text') or '').strip()
        if text:
            link.input_queue.put(text)
        return

    if event_type != 'poke':
        return

    target = event.get('target')
    if target == 'head':
        lines = HEAD_LINES
    elif target == 'face':
        lines = FACE_LINES
    else:
        return

    zh_text, ja_text = random.choice(lines)
    if voice_module.voice.suffix == '.wav':
        # 日语音色：气泡显示中文，TTS 直接读日语，跳过翻译，也不往终端打印
        queue_speak(zh_text, ja_text, echo=False)
    else:
        queue_speak(zh_text, echo=False)