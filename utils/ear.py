import whisper
import os
import warnings

warnings.filterwarnings('ignore')#过滤警告

model = whisper.load_model('base')

print('耳朵已就位')

def transcribe(audio_path):
    if not os.path.exists(audio_path):
        print('找不到录制音频文件：{audio_path}')
        return ''
    try:
        #调用Whisper进行转录
        result = model.transcribe(audio_path, fp16=False)
        text = result['text'].strip()

        return text
    except Exception as e:
        print(f'听觉错误{e}')
        return ''
    
if __name__ == "__main__":
    print(">> 请手动放一个 'test.wav' 在当前目录来测试，或者直接等待 main.py 调用。")