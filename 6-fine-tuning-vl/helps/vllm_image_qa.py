import base64
import requests
import json
from pathlib import Path

def encode_image(image_path):
    """将图片编码为 base64 字符串"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def call_vllm_service(image_path, prompt, server_ip, port):
    """调用 vllm 服务进行图片 QA"""
    # 专门使用 /v1/chat/completions 端点，并增加超时时间
    url = f"http://{server_ip}:{port}/v1/chat/completions"
    print(f"尝试端点: {url}")
    
    # 编码图片
    encoded_image = encode_image(image_path)
    
    # 构建请求数据（使用标准的OpenAI格式）
    data = {
        "model": "qwen25vl-7b-offical-finetuned",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.2
    }
    
    # 发送 POST 请求，增加超时时间到360秒
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=data, headers=headers, timeout=360)
        if response.status_code == 200:
            result = response.json()
            # 提取消息内容
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            return result
        else:
            print(f"端点 {url} 返回状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"请求端点 {url} 失败: {e}")
    except json.JSONDecodeError as e:
        print(f"解析端点 {url} 响应失败: {e}")
    
    return None

def main():
    # 配置参数
    script_dir = Path(__file__).parent
    # 使用Path对象处理相对路径，更可靠
    image_path = (script_dir.parent / "test-img" / "scan_item10-_71.jpg").resolve()
    prompt = "解读这个医学报告，仅用一句话指出其中异常指标"
    server_ip = "124.156.193.94"
    port = 80
    
    print("正在调用 vllm 服务进行图片 QA...")
    print(f"图片路径: {image_path}")
    print(f"提示词: {prompt}")
    print(f"服务器地址: {server_ip}:{port}")
    
    # 调用服务
    result = call_vllm_service(image_path, prompt, server_ip, port)
    
    # 打印结果
    if result:
        print("\nvllm 服务返回结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n调用失败，未能获取结果")

if __name__ == "__main__":
    main()
