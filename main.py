import os
from openai import OpenAI
import re
from utils.mouth import queue_speak, wait_finish
import readline
import json
import time
import utils.ear as ear
from utils.Microphone import Microphone
from utils.init import SYSTEM_PROMPT
from utils.api import use_api
from func import users_peaking, user_keyboard_input

MEMORY_FILE='memory/memory.json'
MEMORY_LIMIT = 20
SENTENCE_SPLIT = re.compile(r'([\n]+)') #分句正则

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return [{'role':'system', 'content':SYSTEM_PROMPT}]
    
    try:
        with open(MEMORY_FILE,'r',encoding='utf-8') as f:
            loaded_messages = json.load(f)

        if not loaded_messages:
            return [{'role':'system', 'content':SYSTEM_PROMPT}]
        return loaded_messages
    
    except Exception as e:
        print(f'记忆损坏，重置记忆: {e}')
        return [{'role':'system', 'content':SYSTEM_PROMPT}]
    
def save_memory(messages):
    #切片，防止耗费过高
    try:
        if len(messages) > MEMORY_LIMIT + 1:
            save_content = [messages[0]] + messages[-MEMORY_LIMIT:]
        else:
            save_content = messages
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            #ensure_ascil=False中文正常显示
            #indent=2打开json文件时能看懂
            json.dump(save_content, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'记忆保存失败{e}')


def chat_loop():
    print("----------ATRI,启动！---------------")

    print('----------读取历史记忆中... ---------')
    messages = load_memory()
    cs = 0
    if len(messages) < 1 :
        #print("ATRI: 啊~呜（打哈欠），夏生先生，早安")
        print('Atri: ',end='')
        queue_speak('啊~呜，夏生先生，早安')
    else:
        #print('ATRI: 欸，夏生先生，忙完了吗？快来继续和我聊天吧')
        print('Atri: ',end='')
        queue_speak('欸，夏生先生，忙完了吗？快来继续和我聊天吧')
    wait_finish()
    while(True):

        # if not os.path.exists("input.wav"):
        #     time.sleep(0.1) # 没文件就休息 0.1秒，别占满 CPU
        #     continue
        # user_input = ear.transcribe("input.wav")
        # print(f"Me (Voice): {user_input}")
        # os.remove("input.wav")
        # #user_input = input('\nMe:')

        # if not user_input or len(user_input.strip()) < 1:
        #     print(">> 没听清...")
        #     continue

        # # if user_input.lower() in ['exit']:
        # #     print('ATRI: 夏生先生，晚安，欸嘿嘿，今天就让高性能的我温暖你的内心吧')
        # #     speak('夏生先生，晚安，欸嘿嘿，今天就让高性能的我温暖你的内心吧')
        # #     break
        # if "关机" in user_input or "再见" in user_input:
        #     speak("晚安，主人。")
        #     break

        #messages.append({'role':'user', 'content':user_input})
        wait_finish()

        if cs == 0:
            print()
            cs+=1
        #键盘输入
        
        # state = user_keyboard_input(messages)
        # if not state : break

        #麦克风输入
        state = users_peaking(messages)
        if not state : break
        elif state == 1 : continue

        try:
            response = use_api(messages)

            # ai_reply = response.choices[0].message.content#获得回复
            # print(f'ATRI:{ai_reply}')
            print('ATRI: ',end='',flush=True)
            full_reply = ''
            current_sentene = ''

            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    #不再print内容，而是放到buffer中
                    current_sentene += content

                    parts = SENTENCE_SPLIT.split(current_sentene) #检测是否是一句完整的话,“你好啊”->["你好啊","!",""]

                    if len(parts) > 1 :
                        sentence = parts[0] + parts[1] #句子+标点
                        #扔进队列，双线程运行
                        queue_speak(sentence)
                        full_reply += sentence

                        current_sentene = ''.join(parts[2:]) #把剩余的也放到buffer

                    # print(content, end='', flush=True) #打出一个字
                    # full_reply += content
            #strip移除字符串头尾指定字符，一般为空格或者换行符
            if current_sentene.strip(): #如果有没说完的话，也扔进去
                queue_speak(current_sentene)
                full_reply += current_sentene
            # speak(full_reply)
            #print()
            wait_finish() #真正实现打断，这里就不用wait，但是先稳一下
            print()
            messages.append({'role':'assistant', 'content':full_reply})
            save_memory(messages)

            #把回复也加入记忆
            #messages.append({'role':'assistant', 'content':ai_reply})
        except Exception as e:
            print(f'呜呜，记忆缺失{e}')

if __name__ == '__main__':
    chat_loop()