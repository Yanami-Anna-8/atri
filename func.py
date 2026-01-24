import os

from utils.Microphone import Microphone
from utils.KeyBoard import KeyBoard

LOCK_PATH = os.path.dirname(os.path.abspath(__file__))


def users_peaking(messages):
    microphone = Microphone(os.path.join(LOCK_PATH, 'utils',"input.wav"), messages=messages)
    state = microphone.user_speak()
    return state

def user_keyboard_input(messages):
    keyboard_input = KeyBoard(messages=messages)
    state = keyboard_input.user_input()
    return state