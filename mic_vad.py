import pyaudio
import audioop
import wave
import os
import time

THRESHOLD = 1000 #阈值：说话音量
SILENCE_LIMIT = 1.0 #沉默多久算说完一句话
CHUNK = 1024 #每个缓冲区帧数
FORMAT = pyaudio.paInt16 #16位深度
CHANNELS = 1 #单声道
RATE = 44100 #采样率
WAVE_OUTPUT_FILENAME = '\\\wsl.localhost\\Ubuntu-24.04\\home\\hao\\atri\\utils\\input.wav'
LOCK_FILE = 'atri_is_speaking.lock' #互斥锁

def  record_auto():
    p = pyaudio.PyAudio()
    #打开音频流
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHANNELS)

    print(f'\n监听中... (阈值：{THRESHOLD})')

    audio_frames = []
    started = False
    silence_start_time = None

    while True:
        #检查锁文件：如果ATRI说话， 暂停监听
        if os.path.exists(LOCK_FILE):
            print('ATRI is speaking...')
            time.sleep(0.1)
            #重置状态
            audio_frames = []
            started = False
            continue

        try:
            data = stream.read(CHUNK, exception_on_overflow=False) #读取帧数（数据块数量）， 数据溢出继续读取
            rms = audioop.rms(data, 2) #计算音量
        except:
            continue

        if rms > THRESHOLD:
            if not started:
                print('检测到人声，开始录音...')
                started = True
            audio_frames.append(data)
            silence_start_time = None #重置静音计时

        elif started:
            #已经开始了，声音较小
            audio_frames.append(data)
            if silence_start_time is None:
                silence_start_time = time.time()

            elif time.time() - silence_start_time > SILENCE_LIMIT:
                print('说话结束，生成文件...')
                break

    stream.stop_stream()
    stream.close()
    p.terminate()

    if audio_frames:
        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(audio_frames))
        wf.close()

if __name__ == '__main__':
    if os.path.exists(WAVE_OUTPUT_FILENAME): os.remove(WAVE_OUTPUT_FILENAME)

    while True:
        try:
            #只有当input.wav不存在时，才开始录下一句
            if not os.path.exists(WAVE_OUTPUT_FILENAME):
                record_auto()
            else:
                time.sleep(0.1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f'Error:{e}')