import requests
import re
import json
import os
import base64
from pathlib import Path

# curl http://124.156.193.94:80/v1/models
# curl http://124.156.193.94:80/api/generate -d '{"model": "qwen2.5vl:32b", "prompt": "你好"}'
# curl http://124.156.193.94:80/api/generate -d '{"model": "qwen2.5vl:32b", "prompt": "你好"}'

# Ollama服务配置
OLLAMA_URL = "http://43.163.90.115:6399/api/generate"
PROMPT_TEMPLATE = "解读这个医学报告，仅用一句话指出其中异常指标，别的话不要说"

def natural_sort_key(s):
    """自定义自然排序的键函数"""
    return [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", s)]

def process_image_with_ollama(image_path):
    """
    使用Ollama服务处理单张图片
    """
    # 构造提示词
    prompt = PROMPT_TEMPLATE
    
    # 将图片编码为base64
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    # 准备请求数据
    payload = {
        "model": "qwen2.5vl:32b",
        "prompt": prompt,
        "stream": False,
        "images": [encoded_image]
    }
    
    try:
        # 发送请求到Ollama服务
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        print(f"处理图片 {image_path} 时返回: {result}")
        return result.get("response", "").strip()
    except Exception as e:
        print(f"处理图片 {image_path} 时出错: {e}")
        return ""

def process_all_images(image_dir="src_image", output_file="metadata.jsonl"):
    """
    处理目录中的所有图片并生成metadata.jsonl文件
    """
    # 获取所有jpg图片
    image_paths = list(Path(image_dir).glob("*.jpg"))
    image_paths.sort(key=lambda p: natural_sort_key(p.name))
    
    # 打开输出文件
    with open(output_file, "w", encoding="utf-8") as f:
        # 处理每张图片
        for i, image_path in enumerate(image_paths):
            filename = image_path.name
            
            # 使用Ollama处理图片
            additional_feature = process_image_with_ollama(str(image_path))
            
            # 创建JSON对象
            metadata = {
                "file_name": filename,
                "additional_feature": additional_feature
            }
            
            # 写入文件
            f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
            
            # 显示进度
            print(f"已处理 {i+1}/{len(image_paths)}: {filename}")
    
    print(f"处理完成，结果已保存到 {output_file}")

if __name__ == "__main__":
    process_all_images()
