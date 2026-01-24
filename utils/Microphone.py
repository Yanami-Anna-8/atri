import asyncio
import edge_tts
import pygame
import os
import time
import utils.ear as ear
from utils.mouth import speak

LOCK_PATH = os.path.dirname(os.path.abspath(__file__))

class Microphone:
    def __init__(self, path, messages):
        self.path = path
        self.messages = messages

    def user_speak(self):
        if not os.path.exists(self.path):
            time.sleep(0.1) # 没文件就休息 0.1秒，别占满 CPU
            return 1
            
        user_input = ear.transcribe(self.path)
        print(f"Me (Voice): {user_input}")
        os.remove(os.path.join(LOCK_PATH,"input.wav"))
        #user_input = input('\nMe:')

        if not user_input or len(user_input.strip()) < 1:
            print(">> 没听清...")
            return 1
            

        # if user_input.lower() in ['exit']:
        #     print('ATRI: 夏生先生，晚安，欸嘿嘿，今天就让高性能的我温暖你的内心吧')
        #     speak('夏生先生，晚安，欸嘿嘿，今天就让高性能的我温暖你的内心吧')
        #     break
        if "关机" in user_input or "再见" in user_input:
            speak("晚安，主人。")
            return 0

        self.messages.append({'role':'user', 'content':user_input})
        return 2