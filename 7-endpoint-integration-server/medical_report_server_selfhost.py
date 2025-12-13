import base64
import os
from flask import Flask, request, jsonify
import requests
import json
from PIL import Image
import io
import sys

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

OPENROUTER_API_KEY = "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"
API_A_MODEL = "./qwen25vl-7b-offical-finetuned/"
API_VL_MODEL = "./qwen25vl-7b-offical-finetuned/"  
API_B_MODEL = "./qwen25-14b-unsloth-finetuned-bnb-4bit/"  
API_LLM_MODEL = "./qwen25-14b-unsloth-finetuned-bnb-4bit/"

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
LLM_API_BASE = "http://43.134.168.231/v1"
VL_API_BASE = "http://43.163.120.108:8000/v1"


def resize_image(image_data, max_size=1280):

    image = Image.open(image_data)
    
    width, height = image.size

    if width > height:
        new_width = min(width, max_size)
        new_height = int(height * (new_width / width))
    else:
        new_height = min(height, max_size)
        new_width = int(width * (new_height / height))

    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    img_byte_arr = io.BytesIO()
    resized_image.save(img_byte_arr, format=image.format or 'JPEG')
    img_byte_arr.seek(0)
    
    return img_byte_arr


def encode_image_to_base64(image_file):

    return base64.b64encode(image_file.read()).decode('utf-8')


def analyze_medical_report_image(base64_image):

    headers = {
        "Content-Type": "application/json",
    }
    # Only add Authorization header if using OpenRouter API
    if VL_API_BASE.startswith("https://openrouter.ai"):
        headers["Authorization"] = f"Bearer {OPENROUTER_API_KEY}"
    
    payload = {
        "model": API_VL_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请仔细分析这张医学检测报告图片，识别并列出其中的异常指标。如果没有发现异常指标，请明确说明'未发现异常指标'。请以简洁、专业的中文医学术语回答。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
    }
    
    response = requests.post(
        f"{VL_API_BASE}/chat/completions",
        headers=headers,
        data=json.dumps(payload)
    )
    
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API A请求失败，状态码 {response.status_code}: {response.text}")


def get_health_recommendations(analysis_result):

    headers = {
        "Content-Type": "application/json",
    }
    # Only add Authorization header if using OpenRouter API
    if LLM_API_BASE.startswith("https://openrouter.ai"):
        headers["Authorization"] = f"Bearer {OPENROUTER_API_KEY}"
    
    payload = {
        "model": API_LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"根据以下医学检测报告分析结果，提供相应的健康建议和注意事项：\n\n{analysis_result}\n\n请以简洁明了的中文给出实用的健康建议，包括饮食、运动和生活方式等方面的指导。"
            }
        ],
    }
    
    response = requests.post(
        f"{LLM_API_BASE}/chat/completions",
        headers=headers,
        data=json.dumps(payload)
    )
    
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API B请求失败，状态码 {response.status_code}: {response.text}")


@app.route('/analyze_medical_report', methods=['POST'])
def analyze_medical_report():

    print("收到医疗报告分析请求", file=sys.stderr)
    
    try:

        if 'image' not in request.files:
            print("请求中未提供图像文件", file=sys.stderr)
            return jsonify({"error": "No image file provided"}), 400
        
        image_file = request.files['image']
        
        if image_file.filename == '':
            print("提供了空的图像文件", file=sys.stderr)
            return jsonify({"error": "Empty image file provided"}), 400
        
        print(f"正在处理图像文件: {image_file.filename}", file=sys.stderr)

        image_data = io.BytesIO(image_file.read())
        print(f"调整图像大小，确保最长边不超过1280像素", file=sys.stderr)
        resized_image = resize_image(image_data, max_size=1280)

        print("将图像编码为base64", file=sys.stderr)
        base64_image = encode_image_to_base64(resized_image)
        print("图像已成功编码为base64", file=sys.stderr)
        

        print("将图像发送到API A进行医疗报告分析", file=sys.stderr)
        analysis_result = analyze_medical_report_image(base64_image)
        print(f"从API A收到分析结果: {analysis_result}", file=sys.stderr)
        print(f"分析结果长度: {len(analysis_result)} 字符", file=sys.stderr)
        

        print("将分析结果发送到API B获取健康建议", file=sys.stderr)
        health_recommendations = get_health_recommendations(analysis_result)
        print(f"从API B收到健康建议: {health_recommendations}", file=sys.stderr)
        print(f"健康建议长度: {len(health_recommendations)} 字符", file=sys.stderr)

        print("将分析结果和健康建议返回给客户端", file=sys.stderr)
        return jsonify({
            "analysis_result": analysis_result,
            "health_recommendations": health_recommendations
        }), 200
        
    except Exception as e:
        print(f"处理医疗报告时出错: {str(e)}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


@app.route('/analyze_medical_report', methods=['OPTIONS'])
def analyze_medical_report_options():
    """
    处理OPTIONS请求以支持跨域
    """
    return jsonify({"status": "ok"}), 200


@app.route('/health', methods=['GET'])
def health_check():
    """
    健康检查端点
    """
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    print("正在启动医疗报告分析服务器，端口80", file=sys.stderr)
    app.run(host='0.0.0.0', port=80, debug=True)
