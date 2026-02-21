import os
import logging
import torch

# 1. 设置静默模式 (防止满屏的日志)
# FunASR 的日志有点多，我们把它关了
logging.getLogger("funasr").setLevel(logging.ERROR)

print("---------- [EAR] 正在加载阿里 Paraformer 模型 (原生版)... ----------")

try:
    from funasr import AutoModel
    
    # 自动检测显卡
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"运行设备: {device}")

    # 2. 加载模型
    # 第一次运行会从阿里服务器下载模型，大概几百MB
    # 我们同时加载：语音识别(paraformer) + 语音活动检测(vad) + 标点符号(punc)
    model = AutoModel(
        model="paraformer-zh", 
        vad_model="fsmn-vad", 
        punc_model="ct-punc",
        # spk_model="cam++", # 只有需要识别"是谁在说话"时才需要这个，我们不需要，注释掉省显存
        device=device,
        disable_update=True # 禁止自动检查更新，加快启动速度
    )
    
    print("---------- [EAR] 阿里听觉模组已就绪 (FunASR Native) ----------")
    MODEL_LOADED = True

except Exception as e:
    print(f"❌ 模型加载失败，请截图报错信息: {e}")
    MODEL_LOADED = False
    model = None

def transcribe(audio_path):
    if not MODEL_LOADED or model is None:
        return ""
        
    if not os.path.exists(audio_path):
        return ""
    
    try:
        # 3. 推理
        # input: 音频文件路径
        # batch_size_s: 批处理大小，设小点省显存
        res = model.generate(input=audio_path, batch_size_s=300)
        
        # 4. 解析结果
        # res 的格式通常是List: [{'key': 'wav_name', 'text': '你好'}]
        if len(res) > 0 and 'text' in res[0]:
            text = res[0]['text']
            # 清理一下标点符号和空格
            return text.strip()
            
        return ""
        
    except Exception as e:
        print(f"❌ 听觉故障: {e}")
        return ""

if __name__ == "__main__":
    print(">> 正在进行自检...")
    # 如果你想测，哪怕没有录音，也可以传一个不存在的文件路径看会不会报错
    transcribe("input.wav")