import queue
import select
import sys

from .link import link, emit_chat
from .mouth import queue_speak, wait_finish


class KeyBoard:
    def __init__(self, messages):
        self.messages = messages

    def _handle(self, user_input, from_frontend=False):
        if user_input.lower() in ['exit']:
            queue_speak('夏生先生，晚安，欸嘿嘿，今天就让高性能的我温暖你的内心吧')
            wait_finish()
            return 0
        if '关机' in user_input or '晚安' in user_input:
            queue_speak('晚安，主人。')
            wait_finish()
            return 0
        if not from_frontend:
            emit_chat('user', user_input)
        self.messages.append({'role': 'user', 'content': user_input})
        return 1

    def user_input(self):
        print('Me: ', end='', flush=True)
        while True:
            # 优先取聊天框发来的消息
            try:
                text = link.input_queue.get_nowait()
            except queue.Empty:
                text = None

            if text:
                print(text)
                return self._handle(text, from_frontend=True)

            # 终端输入作为后备
            if select.select([sys.stdin], [], [], 0.1)[0]:
                line = sys.stdin.readline().strip()
                if line:
                    return self._handle(line, from_frontend=False)