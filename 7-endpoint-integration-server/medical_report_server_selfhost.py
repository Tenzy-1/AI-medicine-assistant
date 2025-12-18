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
    """设置跨域响应头"""
    response.headers.add('Access-Control-Allow-Origin', '*')  # 允许所有源跨域访问
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')  # 允许的请求头
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')  # 允许的请求方法
    return response

# API配置参数
OPENROUTER_API_KEY = "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"
API_A_MODEL = "./qwen25vl-7b-offical-finetuned/"  # 视觉语言模型（分析医疗报告图片）
API_VL_MODEL = "./qwen25vl-7b-offical-finetuned/"  # 视觉语言模型别名（兼容原有命名）
API_B_MODEL = "./qwen25-14b-unsloth-finetuned-bnb-4bit/"  # 大语言模型（生成健康建议）
API_LLM_MODEL = "./qwen25-14b-unsloth-finetuned-bnb-4bit/"  # 大语言模型别名（兼容原有命名）

# API基础地址
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"  # OpenRouter公共API地址
LLM_API_BASE = "http://43.134.168.231/v1"  # 大语言模型本地API地址
VL_API_BASE = "http://43.163.120.108:8000/v1"  # 视觉语言模型本地API地址


def resize_image(image_data, max_size=1280):
    """
    等比例调整图片大小，限制最长边不超过指定尺寸
    :param image_data: 图片字节流对象
    :param max_size: 图片最长边的最大像素值（默认1280）
    :return: 调整后的图片字节流
    """
    # 打开图片
    image = Image.open(image_data)
    
    # 获取原图尺寸
    width, height = image.size

    # 计算等比例缩放后的尺寸
    if width > height:
        new_width = min(width, max_size)
        new_height = int(height * (new_width / width))
    else:
        new_height = min(height, max_size)
        new_width = int(width * (new_height / height))

    # 使用LANCZOS算法调整图片大小（高质量缩放）
    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # 将调整后的图片写入字节流
    img_byte_arr = io.BytesIO()
    resized_image.save(img_byte_arr, format=image.format or 'JPEG')
    img_byte_arr.seek(0)  # 重置字节流指针到起始位置
    
    return img_byte_arr


def encode_image_to_base64(image_file):
    """
    将图片文件编码为Base64字符串
    :param image_file: 图片字节流对象
    :return: Base64编码后的字符串
    """
    return base64.b64encode(image_file.read()).decode('utf-8')


def analyze_medical_report_image(base64_image):
    """
    调用视觉语言模型分析医疗报告图片，提取异常指标
    :param base64_image: Base64编码的图片字符串
    :return: 模型返回的异常指标分析结果（中文）
    :raise Exception: API调用失败时抛出异常
    """
    # 构建请求头
    headers = {
        "Content-Type": "application/json",  # JSON格式请求体
    }
    # 仅当使用OpenRouter API时添加授权头
    if VL_API_BASE.startswith("https://openrouter.ai"):
        headers["Authorization"] = f"Bearer {OPENROUTER_API_KEY}"
    
    # 构建API请求体
    payload = {
        "model": API_VL_MODEL,  # 指定使用的模型
        "messages": [
            {
                "role": "user",  # 用户角色
                "content": [
                    {
                        "type": "text",  # 文本指令
                        "text": "请仔细分析这张医学检测报告图片，识别并列出其中的异常指标。如果没有发现异常指标，请明确说明'未发现异常指标'。请以简洁、专业的中文医学术语回答。"
                    },
                    {
                        "type": "image_url",  # 图片数据
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"  # Base64格式图片
                        }
                    }
                ]
            }
        ],
    }
    
    # 发送POST请求调用视觉语言模型API
    response = requests.post(
        f"{VL_API_BASE}/chat/completions",  # API端点地址
        headers=headers,
        data=json.dumps(payload)  # 将请求体转为JSON字符串
    )
    
    # 处理响应结果
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]  # 提取模型返回的分析结果
    else:
        raise Exception(f"视觉语言模型API请求失败，状态码 {response.status_code}: {response.text}")


def get_health_recommendations(analysis_result):
    """
    调用大语言模型根据异常指标分析结果生成健康建议
    :param analysis_result: 医疗报告异常指标分析结果
    :return: 模型返回的健康建议（中文）
    :raise Exception: API调用失败时抛出异常
    """
    # 构建请求头
    headers = {
        "Content-Type": "application/json",
    }
    # 仅当使用OpenRouter API时添加授权头
    if LLM_API_BASE.startswith("https://openrouter.ai"):
        headers["Authorization"] = f"Bearer {OPENROUTER_API_KEY}"
    
    # 构建API请求体
    payload = {
        "model": API_LLM_MODEL,  # 指定使用的模型
        "messages": [
            {
                "role": "user",  # 用户角色
                "content": f"根据以下医学检测报告分析结果，提供相应的健康建议和注意事项：\n\n{analysis_result}\n\n请以简洁明了的中文给出实用的健康建议，包括饮食、运动和生活方式等方面的指导。"
            }
        ],
    }
    
    # 发送POST请求调用大语言模型API
    response = requests.post(
        f"{LLM_API_BASE}/chat/completions",  # API端点地址
        headers=headers,
        data=json.dumps(payload)
    )
    
    # 处理响应结果
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]  # 提取模型返回的健康建议
    else:
        raise Exception(f"大语言模型API请求失败，状态码 {response.status_code}: {response.text}")


@app.route('/analyze_medical_report', methods=['POST'])
def analyze_medical_report():
    """
    医疗报告分析主接口（POST方法）
    接收图片文件，调用视觉模型分析异常指标，再调用语言模型生成健康建议
    返回格式：{"analysis_result": "异常指标分析", "health_recommendations": "健康建议"}
    """
    print("收到医疗报告分析请求", file=sys.stderr)
    
    try:
        # 检查请求中是否包含图片文件
        if 'image' not in request.files:
            print("请求中未提供图像文件", file=sys.stderr)
            return jsonify({"error": "未提供图像文件"}), 400
        
        image_file = request.files['image']
        
        # 检查图片文件是否为空
        if image_file.filename == '':
            print("提供了空的图像文件", file=sys.stderr)
            return jsonify({"error": "提供的图像文件为空"}), 400
        
        print(f"正在处理图像文件: {image_file.filename}", file=sys.stderr)

        # 将图片读取为字节流并调整大小
        image_data = io.BytesIO(image_file.read())
        print(f"调整图像大小，确保最长边不超过1280像素", file=sys.stderr)
        resized_image = resize_image(image_data, max_size=1280)

        # 将调整后的图片编码为Base64
        print("将图像编码为base64", file=sys.stderr)
        base64_image = encode_image_to_base64(resized_image)
        print("图像已成功编码为base64", file=sys.stderr)
        
        # 调用视觉语言模型分析医疗报告
        print("将图像发送到视觉语言模型API进行医疗报告分析", file=sys.stderr)
        analysis_result = analyze_medical_report_image(base64_image)
        print(f"从视觉语言模型API收到分析结果: {analysis_result}", file=sys.stderr)
        print(f"分析结果长度: {len(analysis_result)} 字符", file=sys.stderr)
        
        # 调用大语言模型生成健康建议
        print("将分析结果发送到大语言模型API获取健康建议", file=sys.stderr)
        health_recommendations = get_health_recommendations(analysis_result)
        print(f"从大语言模型API收到健康建议: {health_recommendations}", file=sys.stderr)
        print(f"健康建议长度: {len(health_recommendations)} 字符", file=sys.stderr)

        # 返回分析结果和健康建议给客户端
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
    处理OPTIONS预检请求以支持跨域
    浏览器发送跨域POST请求前会先发送OPTIONS请求验证
    """
    return jsonify({"status": "ok"}), 200


@app.route('/health', methods=['GET'])
def health_check():
    """
    服务健康检查端点
    用于监控服务是否正常运行，返回200表示健康
    """
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    print("正在启动医疗报告分析服务器，端口80", file=sys.stderr)
    # 启动Flask服务，监听所有网卡的80端口，开启调试模式
    app.run(host='0.0.0.0', port=80, debug=True)