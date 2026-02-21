from .mouth import queue_speak
import readline


class KeyBoard:
    def __init__(self, messages):
        self.messages = messages

    def user_input(self):
        user_input = input('Me: ')
        if user_input.lower() in ['exit']:
            #print('ATRI: 夏生先生，晚安，欸嘿嘿，今天就让高性能的我温暖你的内心吧')
            queue_speak('夏生先生，晚安，欸嘿嘿，今天就让高性能的我温暖你的内心吧')
            return 0
        if "关机" in user_input or "晚安" in user_input:
            queue_speak("晚安，主人。")
            return 0
        self.messages.append({'role':'user', 'content':user_input})
        return 1