import base64
import os
from flask import Flask, request, jsonify
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
from PIL import Image
import io
import sys
import logging
from functools import wraps, lru_cache
from time import time
from typing import Optional, Tuple
import hashlib
from threading import Lock
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('medical_server.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 从环境变量读取配置，如果没有则使用默认值
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    logger.error("错误: OPENROUTER_API_KEY 环境变量未设置，请在生产环境中设置此变量")
    raise ValueError("OPENROUTER_API_KEY 环境变量必须设置")

API_A_MODEL = os.getenv('API_A_MODEL', "qwen/qwen2.5-vl-32b-instruct:free")
API_B_MODEL = os.getenv('API_B_MODEL', "qwen/qwen3-30b-a3b:free")
OPENROUTER_API_BASE = os.getenv('OPENROUTER_API_BASE', "https://openrouter.ai/api/v1")

# 配置常量
MAX_IMAGE_SIZE = int(os.getenv('MAX_IMAGE_SIZE', '1280'))  # 最大图片尺寸
API_TIMEOUT = int(os.getenv('API_TIMEOUT', '300'))  # API请求超时时间（秒）
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))  # 最大重试次数
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 最大文件大小（10MB）
ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'  # 是否启用缓存
CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))  # 缓存过期时间（秒）
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '4'))  # 线程池最大工作线程数

# 创建带连接池的Session
session = requests.Session()
retry_strategy = Retry(
    total=MAX_RETRIES,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"]
)
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,
    pool_maxsize=20
)
session.mount("http://", adapter)
session.mount("https://", adapter)

# 改进的LRU缓存实现（生产环境建议使用Redis）
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size=1000, ttl=3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = Lock()
    
    def get(self, key):
        with self.lock:
            if key not in self.cache:
                return None
            # 检查是否过期
            if time() - self.timestamps[key] > self.ttl:
                del self.cache[key]
                del self.timestamps[key]
                return None
            # 移动到末尾（最近使用）
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def set(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # 删除最旧的项
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    del self.timestamps[oldest_key]
            self.cache[key] = value
            self.timestamps[key] = time()

cache = LRUCache(max_size=1000, ttl=CACHE_TTL) if ENABLE_CACHE else None

# 创建线程池用于并发处理
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


def resize_image(image_data, max_size=None):
    """
    调整图片大小，保持宽高比
    """
    if max_size is None:
        max_size = MAX_IMAGE_SIZE
    
    try:
        image = Image.open(image_data)
        width, height = image.size
        
        # 如果图片已经小于最大尺寸，直接返回
        if width <= max_size and height <= max_size:
            image_data.seek(0)
            return image_data
        
        # 计算新尺寸，保持宽高比
        if width > height:
            new_width = min(width, max_size)
            new_height = int(height * (new_width / width))
        else:
            new_height = min(height, max_size)
            new_width = int(width * (new_height / height))
        
        # 使用高质量重采样（LANCZOS提供最佳质量）
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 转换为RGB模式（如果不是的话），确保兼容性
        if resized_image.mode != 'RGB':
            resized_image = resized_image.convert('RGB')
        
        # 优化图片压缩：根据图片大小动态调整质量，使用更高效的压缩
        img_byte_arr = io.BytesIO()
        # 对于较小的图片使用更高质量，大图片使用较低质量以节省带宽
        # 使用渐进式JPEG和优化选项
        quality = 92 if max(width, height) < 800 else 88
        resized_image.save(
            img_byte_arr, 
            format='JPEG', 
            quality=quality, 
            optimize=True,
            progressive=True,  # 渐进式JPEG，加载更快
            subsampling='4:2:0'  # 色度子采样，减小文件大小
        )
        img_byte_arr.seek(0)
        
        logger.info(f"图片已调整: {width}x{height} -> {new_width}x{new_height}")
        return img_byte_arr
    except Exception as e:
        logger.error(f"调整图片大小失败: {str(e)}")
        raise


def encode_image_to_base64(image_file):
    """
    将图片文件编码为base64字符串
    """
    try:
        image_file.seek(0)
        return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"编码图片为base64失败: {str(e)}")
        raise


def get_cache_key(base64_image: str, prompt_type: str) -> str:
    """生成缓存键"""
    content = f"{base64_image[:100]}{prompt_type}"  # 使用图片前100字符和提示类型
    return hashlib.md5(content.encode()).hexdigest()

def get_from_cache(cache_key: str) -> Optional[str]:
    """从缓存获取结果"""
    if not ENABLE_CACHE or cache is None:
        return None
    result = cache.get(cache_key)
    if result:
        logger.info(f"从缓存获取结果: {cache_key[:8]}...")
    return result

def set_to_cache(cache_key: str, value: str):
    """设置缓存"""
    if not ENABLE_CACHE or cache is None:
        return
    cache.set(cache_key, value)

def make_api_request_with_retry(url, headers, payload, max_retries=MAX_RETRIES):
    """
    带重试机制的API请求（使用连接池）
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            response = session.post(
                url,
                headers=headers,
                json=payload,
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limit
                wait_time = 2 ** attempt
                logger.warning(f"API请求被限流，等待 {wait_time} 秒后重试 (尝试 {attempt + 1}/{max_retries})")
                import time
                time.sleep(wait_time)
                continue
            else:
                error_msg = f"API请求失败，状态码 {response.status_code}: {response.text[:500]}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            last_exception = Exception(f"API请求超时 (尝试 {attempt + 1}/{max_retries})")
            logger.warning(str(last_exception))
            if attempt < max_retries - 1:
                continue
        except requests.exceptions.RequestException as e:
            last_exception = Exception(f"API请求异常: {str(e)} (尝试 {attempt + 1}/{max_retries})")
            logger.warning(str(last_exception))
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                import time
                time.sleep(wait_time)
                continue
    
    raise last_exception or Exception("API请求失败，已达到最大重试次数")


def analyze_medical_report_image(base64_image):
    """
    分析医疗报告图片（带缓存）
    """
    # 检查缓存
    cache_key = get_cache_key(base64_image, "analysis")
    cached_result = get_from_cache(cache_key)
    if cached_result:
        return cached_result
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": API_A_MODEL,
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
    
    start_time = time()
    try:
        result = make_api_request_with_retry(
            f"{OPENROUTER_API_BASE}/chat/completions",
            headers,
            payload
        )
        elapsed_time = time() - start_time
        content = result["choices"][0]["message"]["content"]
        logger.info(f"API A请求成功，耗时 {elapsed_time:.2f} 秒")
        
        # 保存到缓存
        set_to_cache(cache_key, content)
        return content
    except Exception as e:
        elapsed_time = time() - start_time
        logger.error(f"API A请求失败，耗时 {elapsed_time:.2f} 秒: {str(e)}")
        raise


def get_health_recommendations(analysis_result):
    """
    获取健康建议（带缓存）
    """
    # 检查缓存（基于分析结果）
    cache_key = get_cache_key(analysis_result, "recommendations")
    cached_result = get_from_cache(cache_key)
    if cached_result:
        return cached_result
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": API_B_MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"根据以下医学检测报告分析结果，提供相应的健康建议和注意事项：\n\n{analysis_result}\n\n请以简洁明了的中文给出实用的健康建议，包括饮食、运动和生活方式等方面的指导。"
            }
        ],
    }
    
    start_time = time()
    try:
        result = make_api_request_with_retry(
            f"{OPENROUTER_API_BASE}/chat/completions",
            headers,
            payload
        )
        elapsed_time = time() - start_time
        content = result["choices"][0]["message"]["content"]
        logger.info(f"API B请求成功，耗时 {elapsed_time:.2f} 秒")
        
        # 保存到缓存
        set_to_cache(cache_key, content)
        return content
    except Exception as e:
        elapsed_time = time() - start_time
        logger.error(f"API B请求失败，耗时 {elapsed_time:.2f} 秒: {str(e)}")
        raise


def validate_image_file(image_file):
    """
    验证图片文件
    """
    if not image_file or image_file.filename == '':
        raise ValueError("未提供有效的图像文件")
    
    # 检查文件扩展名
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    file_ext = os.path.splitext(image_file.filename.lower())[1]
    if file_ext not in allowed_extensions:
        raise ValueError(f"不支持的文件格式: {file_ext}。支持的格式: {', '.join(allowed_extensions)}")
    
    # 检查文件大小
    image_file.seek(0, os.SEEK_END)
    file_size = image_file.tell()
    image_file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"文件大小超过限制: {file_size / 1024 / 1024:.2f}MB (最大: {MAX_FILE_SIZE / 1024 / 1024:.2f}MB)")
    
    return True


@app.route('/analyze_medical_report', methods=['POST'])
def analyze_medical_report():
    """
    分析医疗报告的主端点
    """
    request_start_time = time()
    logger.info("收到医疗报告分析请求")
    
    try:
        # 验证请求
        if 'image' not in request.files:
            logger.warning("请求中未提供图像文件")
            return jsonify({"error": "未提供图像文件"}), 400
        
        image_file = request.files['image']
        
        # 验证图片文件
        try:
            validate_image_file(image_file)
        except ValueError as e:
            logger.warning(f"图片验证失败: {str(e)}")
            return jsonify({"error": str(e)}), 400
        
        logger.info(f"正在处理图像文件: {image_file.filename}")
        
        # 读取并调整图片大小
        image_data = io.BytesIO(image_file.read())
        logger.info("调整图像大小")
        resized_image = resize_image(image_data, max_size=MAX_IMAGE_SIZE)
        
        # 编码为base64
        logger.info("将图像编码为base64")
        base64_image = encode_image_to_base64(resized_image)
        logger.info(f"图像已成功编码为base64，大小: {len(base64_image)} 字符")
       
        # 调用API A进行医疗报告分析
        logger.info("将图像发送到API A进行医疗报告分析")
        analysis_start = time()
        analysis_result = analyze_medical_report_image(base64_image)
        analysis_time = time() - analysis_start
        logger.info(f"从API A收到分析结果，长度: {len(analysis_result)} 字符，耗时: {analysis_time:.2f}秒")
        
        # 调用API B获取健康建议（在分析完成后）
        logger.info("将分析结果发送到API B获取健康建议")
        recommendation_start = time()
        health_recommendations = get_health_recommendations(analysis_result)
        recommendation_time = time() - recommendation_start
        logger.info(f"从API B收到健康建议，长度: {len(health_recommendations)} 字符，耗时: {recommendation_time:.2f}秒")
       
        # 返回结果
        total_time = time() - request_start_time
        logger.info(f"请求处理完成，总耗时: {total_time:.2f} 秒 (分析: {analysis_time:.2f}s, 建议: {recommendation_time:.2f}s)")
        
        return jsonify({
            "analysis_result": analysis_result,
            "health_recommendations": health_recommendations,
            "processing_time": round(total_time, 2),
            "analysis_time": round(analysis_time, 2),
            "recommendation_time": round(recommendation_time, 2),
            "cache_hit": False  # 可以扩展以显示缓存命中情况
        }), 200
        
    except ValueError as e:
        logger.error(f"请求验证失败: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        total_time = time() - request_start_time
        logger.error(f"处理医疗报告时出错 (耗时 {total_time:.2f} 秒): {str(e)}", exc_info=True)
        # 不暴露内部错误详情给客户端（安全考虑）
        error_message = "服务器内部错误，请稍后重试"
        if "OPENROUTER_API_KEY" in str(e):
            error_message = "API配置错误，请联系管理员"
        return jsonify({"error": error_message}), 500


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
    port = int(os.getenv('PORT', '80'))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"正在启动医疗报告分析服务器，端口 {port}")
    logger.info(f"配置信息: API_A_MODEL={API_A_MODEL}, API_B_MODEL={API_B_MODEL}")
    logger.info(f"最大图片尺寸: {MAX_IMAGE_SIZE}px, API超时: {API_TIMEOUT}s, 最大重试: {MAX_RETRIES}次")
    
    app.run(host='0.0.0.0', port=port, debug=debug)