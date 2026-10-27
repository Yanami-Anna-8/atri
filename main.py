import os
import re
import json
import time
from openai import OpenAI

from utils.mouth import queue_speak, wait_finish, actor
from utils.init import SYSTEM_PROMPT
from utils.api import use_api
from utils.link import link, emit_state, emit_notice
from utils.interaction import handle_client_message
from utils.voice import configure_voice
from func import user_keyboard_input, users_peaking

# 获取当前 main.py 所在的绝对目录路径 (即 my_dear 文件夹的路径)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 拼接出绝对路径：/home/airhead/my_dear/memory/memory.json
MEMORY_FILE = os.path.join(BASE_DIR, 'memory', 'memory.json')
MEMORY_LIMIT = 20
SENTENCE_SPLIT = re.compile(r'([\n]+)') 

# ... (load_memory 和 save_memory 保持原样不变) ...

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return [{'role':'system', 'content':SYSTEM_PROMPT}]
    
    try:
        with open(MEMORY_FILE,'r',encoding='utf-8') as f:
            loaded_messages = json.load(f)

        if not loaded_messages:
            return [{'role':'system', 'content':SYSTEM_PROMPT}]

        # 始终使用最新的 system prompt，避免改了 init.py 但旧记忆里还是旧人设
        if loaded_messages[0].get('role') == 'system':
            loaded_messages[0]['content'] = SYSTEM_PROMPT
        else:
            loaded_messages.insert(0, {'role':'system', 'content':SYSTEM_PROMPT})
        return loaded_messages
    
    except Exception as e:
        print(f'记忆损坏，重置记忆: {e}')
        return [{'role':'system', 'content':SYSTEM_PROMPT}]
    
def save_memory(messages):
    """保存记忆，并切片防止Token超限"""
    try:
        # 【新增】：在保存前，确保 memory 文件夹一定是存在的，不存在就自动建一个
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        
        if len(messages) > MEMORY_LIMIT + 1:
            save_content = [messages[0]] + messages[-MEMORY_LIMIT:]
        else:
            save_content = messages
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(save_content, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'记忆保存失败: {e}')

def choose_interaction_mode():
    """模块化：让用户选择交互方式"""
    print("===================================")
    print("请选择 ATRI 的交互模式:")
    print("[1] 键盘打字 (快速启动，无延迟)")
    print("[2] 语音对话 (需加载语音大模型，稍慢)")
    print("===================================")
    while True:
        choice = input("请输入 1 或 2: ").strip()
        if choice == '1':
            return 'keyboard'
        elif choice == '2':
            return 'voice'
        print("输入无效，请重新输入 1 或 2。")

def choose_voice():
    """选择语音后端；可用环境变量 ATRI_VOICE=edge/gpt 跳过交互。"""
    forced = os.environ.get('ATRI_VOICE', '').strip().lower()
    if forced in ('edge', 'gpt'):
        return forced

    print("===================================")
    print("请选择 ATRI 的声音:")
    print("[1] 默认中文 (edge-tts)")
    print("[2] 日语音色 (GPT-SoVITS，需先启动 api.py)")
    print("===================================")
    while True:
        choice = input("请输入 1 或 2: ").strip()
        if choice == '1':
            return 'edge'
        elif choice == '2':
            return 'gpt'
        print("输入无效，请重新输入 1 或 2。")


def chat_loop():
    link.on_message = handle_client_message
    link.start()
    mode = choose_interaction_mode()
    configure_voice(choose_voice())
    
    # 动态加载和初始化模型
    if mode == 'voice':
        import utils.ear as ear
        ear.init_asr_model()
        print("\n>> 提示: 请确保已在 Windows 端启动 mic_vad.py")

    print("\n----------ATRI,启动！---------------")
    print('----------读取历史记忆中... ---------')
    
    messages = load_memory()
    cs = 0
    opening = '啊~呜，夏生先生，早安' if len(messages) < 1 else '欸，夏生先生，忙完了吗？快来继续和我聊天吧'
    print('Atri: ', end='')
    queue_speak(opening)
    wait_finish()

    while True:
        wait_finish()
        if cs == 0:
            print()
            cs += 1

        # 策略分发：根据模式选择不同的输入流
        if mode == 'keyboard':
            state = user_keyboard_input(messages)
            if state == 0: break # 返回0代表要求退出
        else:
            state = users_peaking(messages)
            if state == 0: break
            elif state == 1: continue # 没听清，继续监听

        try:
            emit_state('thinking')
            response = use_api(messages)
            print('ATRI: ', end='', flush=True)
            full_reply = ''
            current_sentene = ''

            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    current_sentene += content
                    parts = SENTENCE_SPLIT.split(current_sentene)

                    if len(parts) > 1 :
                        sentence = parts[0] + parts[1]
                        queue_speak(sentence)
                        full_reply += sentence
                        current_sentene = ''.join(parts[2:]) 

            if current_sentene.strip(): 
                queue_speak(current_sentene)
                full_reply += current_sentene
            
            wait_finish() 
            print()
            
            emit_state('idle')
            messages.append({'role':'assistant', 'content':full_reply})
            save_memory(messages)

        except Exception as e:
            print(f'呜呜，网络或记忆故障: {e}')
            emit_notice(f'网络或记忆故障: {e}')
            emit_state('idle')

if __name__ == '__main__':
    try:
        chat_loop()
    finally:
        # 优雅退出：防止报错 Actor Error: cannot schedule new futures,然而实际上还是有可能出这个错误···
        actor.running = False
        link.stop()


    #欸，夏生先生，忙完了吗？快来继续和我聊天吧
    #ねえ、夏生さん、お仕事終わりましたか？早く続きを話しましょうよ
