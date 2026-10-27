import os
import logging
import torch

# 1. 设置静默模式
logging.getLogger("funasr").setLevel(logging.ERROR)

model = None
MODEL_LOADED = False

def init_asr_model():
    """懒加载：只有被调用时，才真正把几百MB的模型载入显存"""
    global model, MODEL_LOADED
    if MODEL_LOADED: return # 防止重复加载

    print("---------- [EAR] 正在加载阿里 Paraformer 模型 (原生版)... ----------")
    try:
        from funasr import AutoModel
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"运行设备: {device}")

        model = AutoModel(
            model="paraformer-zh", 
            vad_model="fsmn-vad", 
            punc_model="ct-punc",
            device=device,
            disable_update=True
        )
        print("---------- [EAR] 阿里听觉模组已就绪 (FunASR Native) ----------")
        MODEL_LOADED = True
    except Exception as e:
        print(f"❌ 模型加载失败，请截图报错信息: {e}")
        MODEL_LOADED = False
        model = None

def transcribe(audio_path):
    # 推理逻辑保持不变
    if not MODEL_LOADED or model is None:
        return ""
    if not os.path.exists(audio_path):
        return ""
    try:
        res = model.generate(input=audio_path, batch_size_s=300)
        if len(res) > 0 and 'text' in res[0]:
            return res[0]['text'].strip()
        return ""
    except Exception as e:
        print(f"❌ 听觉故障: {e}")
        return ""