from openai import OpenAI

client = OpenAI(
    api_key='sk-47748cd578454bfd8737ee86222bb817',
    base_url='https://api.deepseek.com'
)

def use_api(messages):
    response = client.chat.completions.create(
        model='deepseek-chat',
        messages=messages,
        temperature=1.3, #温度设置高，使其更具情感
        max_tokens=200,
        stream=True #开启流式
    )

    return response