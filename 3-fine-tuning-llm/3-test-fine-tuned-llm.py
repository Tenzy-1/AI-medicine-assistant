"""
微调模型测试脚本
优化版本：改进了配置管理、重试机制、错误处理和日志记录
"""
from openai import OpenAI
import pandas as pd
from datetime import datetime
import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_fine_tuned_llm.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 配置参数（可通过环境变量覆盖）
CONFIG = {
    'openai_api_key': os.getenv('OPENAI_API_KEY', 'ollama'),
    'openai_api_base': os.getenv('OPENAI_API_BASE', 'http://43.156.36.231:80/v1'),
    'model_name': os.getenv('MODEL_NAME', '/workspace/qwen25-14b-offical-finetuned-bnb-4bit'),
    'max_tokens': int(os.getenv('MAX_TOKENS', '600')),
    'retry_times': int(os.getenv('RETRY_TIMES', '3')),  # 改进：默认3次重试
    'retry_delay': float(os.getenv('RETRY_DELAY', '2.0')),  # 重试延迟（秒）
    'timeout': int(os.getenv('API_TIMEOUT', '60')),  # API超时时间（秒）
    'temperature': float(os.getenv('TEMPERATURE', '0.6')),
    'output_dir': os.getenv('OUTPUT_DIR', 'medical_test_results'),
}

# 初始化客户端
client = OpenAI(
    api_key=CONFIG['openai_api_key'],
    base_url=CONFIG['openai_api_base'],
    timeout=CONFIG['timeout'],
)

MAX_TOKENS = CONFIG['max_tokens']
RETRY_TIMES = CONFIG['retry_times']
HEADER_SEPARATOR = "=" * 90  
CONTENT_SEPARATOR = "-" * 90  
INDENT = "  "  

test_questions = [
    {
        "id": 1,
        "question_en": "My choline level is high. What should I do?",
        "question_cn": "我检测出来胆碱高，应该怎么办？"
    },
    {
        "id": 2,
        "question_en": "My blood sugar is slightly elevated (fasting 6.5 mmol/L). How to adjust my lifestyle?",
        "question_cn": "我的血糖轻度升高（空腹6.5 mmol/L），该如何调整生活方式？"
    },
    {
        "id": 3,
        "question_en": "The liver function test shows elevated ALT (80 U/L). What are the possible reasons and suggestions?",
        "question_cn": "肝功能检查显示ALT升高（80 U/L），可能的原因和建议是什么？"
    },
    {
        "id": 4,
        "question_en": "My cholesterol level is 6.8 mmol/L. Should I take medication or just diet control?",
        "question_cn": "我的胆固醇值为6.8 mmol/L，需要吃药还是只需饮食控制？"
    },
    {
        "id": 5,
        "question_en": "Urine routine shows proteinuria (+). What further examinations are needed?",
        "question_cn": "尿常规显示蛋白尿（+），需要做哪些进一步检查？"
    },
    {
        "id": 6,
        "question_en": "My blood pressure is consistently around 145/95 mmHg. How to lower it naturally?",
        "question_cn": "我的血压持续在145/95 mmHg左右，如何自然降压？"
    },
    {
        "id": 7,
        "question_en": "Tumor marker CA19-9 is slightly elevated (45 U/mL). Is it necessary to worry about pancreatic cancer?",
        "question_cn": "肿瘤标志物CA19-9轻度升高（45 U/mL），需要担心胰腺癌吗？"
    },
    {
        "id": 8,
        "question_en": "My thyroid function shows TSH is high (5.2 mIU/L) but T3/T4 are normal. What does this mean?",
        "question_cn": "甲状腺功能检查显示TSH偏高（5.2 mIU/L）但T3/T4正常，这意味着什么？"
    },
    {
        "id": 9,
        "question_en": "I have mild anemia (hemoglobin 105 g/L). What foods should I eat to improve it?",
        "question_cn": "我有轻度贫血（血红蛋白105 g/L），应该吃什么食物改善？"
    },
    {
        "id": 10,
        "question_en": "ECG shows sinus tachycardia (heart rate 110 bpm). What are the possible causes and handling methods?",
        "question_cn": "心电图显示窦性心动过速（心率110次/分），可能的原因和处理方法是什么？"
    }
]


def clean_irrelevant_content(text):
    irrelevant_patterns = [
        "指令:", "Instruction:", "I have noticed", "A patient has",
        "Question:", "问题:", "Example:", "例如:", "{MAX_TOKENS}"
    ]
    for pattern in irrelevant_patterns:
        if pattern in text:
            if text.startswith(pattern):
                text = text.split(pattern)[-1].strip()
            else:
                text = text.split(pattern)[0].strip()
    text = text.replace("{", "").replace("}", "").strip()
    return text if text and text.strip() != " " else "No valid Chinese answer provided"

def get_medical_response(question_en: str, question_cn: str, retry: int = 0) -> Dict[str, str]:
    """
    获取医疗咨询响应（改进版：更好的错误处理和重试机制）
    
    Args:
        question_en: 英文问题
        question_cn: 中文问题
        retry: 当前重试次数
    
    Returns:
        包含status、english_answer和chinese_answer的字典
    """
    full_question = f"{question_en}（{question_cn}）"
    
    try:
        logger.debug(f"发送请求 (重试 {retry}/{RETRY_TIMES}): {full_question[:50]}...")
        
        response = client.chat.completions.create(
            model=CONFIG['model_name'],
            messages=[
                {
                    "role": "assistant",
                    "content": "You are a professional medical consultant specializing in abnormal physical exams. "
                              "STRICT RULES: "
                              "1. English Answer: 3-4 key points (causes + core suggestions + precautions), no redundancy, complete sentences. "
                              "2. Separator: '---Chinese Version---' (exact wording). "
                              "3. Chinese Answer: Accurate translation of English, concise, complete, no extra content. "
                              f"4. Ensure completeness within {MAX_TOKENS} tokens, no truncated sentences."
                },
                {"role": "user", "content": full_question}
            ],
            stream=False,
            temperature=CONFIG['temperature'],
            max_tokens=MAX_TOKENS,
        )
        
        if not response.choices or not response.choices[0].message:
            raise ValueError("API响应格式异常：缺少choices或message")
        
        answer = response.choices[0].message.content.strip()
        
        if not answer:
            raise ValueError("API返回空答案")
        
        # 解析答案
        separator = "---Chinese Version---"
        
        if separator in answer:
            en_part, cn_part = answer.split(separator, 1)
            en_part = en_part.strip()
            cn_part = cn_part.strip()
        else:
            # 尝试自动检测中英文分界
            cn_start_idx = None
            for i, char in enumerate(answer):
                if '\u4e00' <= char <= '\u9fff':
                    cn_start_idx = i
                    break
            if cn_start_idx:
                en_part = answer[:cn_start_idx].strip()
                cn_part = answer[cn_start_idx:].strip()
            else:
                en_part = answer
                cn_part = "No corresponding Chinese translation"
       
        # 清理无关内容
        cn_part = clean_irrelevant_content(cn_part)
        en_part = en_part if en_part else "No valid English answer provided"
        
        # 验证答案完整性
        if not any(k in en_part.lower() for k in ["cause", "suggest", "recommend", "note", "step"]):
            en_part += " Core recommendations: Consult a healthcare provider for personalized evaluation and follow-up."
        if not any(k in cn_part for k in ["原因", "建议", "推荐", "注意", "步骤"]):
            cn_part += " 核心建议：咨询医疗专业人员进行个性化评估和随访。"
        
        logger.debug(f"成功获取响应 (重试 {retry})")
        
        return {
            "status": "success",
            "english_answer": en_part,
            "chinese_answer": cn_part
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"请求失败 (重试 {retry}/{RETRY_TIMES}): {error_msg[:100]}")
        
        if retry < RETRY_TIMES:
            delay = CONFIG['retry_delay'] * (retry + 1)  # 指数退避
            logger.info(f"等待 {delay:.1f} 秒后重试...")
            time.sleep(delay)
            return get_medical_response(question_en, question_cn, retry + 1)
        
        logger.error(f"请求最终失败 (已重试 {RETRY_TIMES} 次): {error_msg}")
        return {
            "status": "failed",
            "english_answer": f"Failed after {RETRY_TIMES + 1} attempts: {error_msg[:200]}",
            "chinese_answer": f"经{RETRY_TIMES + 1}次尝试失败：{error_msg[:200]}"
        }

def format_full_answer(answer, prefix):

    lines = answer.split('\n')
    formatted_lines = [f"{prefix}{line.strip()}" for line in lines if line.strip()]
    return '\n'.join(formatted_lines) if formatted_lines else f"{prefix}No relevant content"

def batch_test_and_summary(test_questions):

    results = []
    total = len(test_questions)

    print("\n" + HEADER_SEPARATOR)
    print(f"[START] Medical LLM Batch Test (Total Questions: {total}, Max Tokens: {MAX_TOKENS})")
    print(HEADER_SEPARATOR + "\n")
    
    for idx, item in enumerate(test_questions, 1):
        qid = item["id"]
        q_en = item["question_en"]
        q_cn = item["question_cn"]

        print(CONTENT_SEPARATOR)
        print(f"[Question {idx:2d}/{total}] | ID: {qid:2d}")
        print(f"{INDENT}English Query: {q_en}")
        print(f"{INDENT}Chinese Query: {q_cn}")
        print(f"{INDENT}[Processing...]", end="\r")
        

        response = get_medical_response(q_en, q_cn)
  
        status = response["status"].upper()
        print(f"{INDENT}[Status: {status:6s}]")
        
        print(f"\n{INDENT}English Answer:")
        formatted_en = format_full_answer(response["english_answer"], INDENT * 2)
        print(formatted_en)
        
        print(f"\n{INDENT}Chinese Answer:")
        formatted_cn = format_full_answer(response["chinese_answer"], INDENT * 2)
        print(formatted_cn)
        
        print(CONTENT_SEPARATOR + "\n")

        results.append({
            "Question ID": qid,
            "Question (English)": q_en,
            "Question (Chinese)": q_cn,
            "Status": status.lower(),
            "Answer (English)": response["english_answer"],
            "Answer (Chinese)": response["chinese_answer"],
            "Test Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    

    # 使用配置的输出目录
    script_dir = Path(__file__).parent
    # CONFIG['output_dir']是字符串，需要正确处理绝对路径和相对路径
    output_dir_str = CONFIG['output_dir']
    if Path(output_dir_str).is_absolute():
        output_dir = Path(output_dir_str)
    else:
        output_dir = script_dir / output_dir_str
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"medical_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    output_path = output_dir / filename
    
    logger.info(f"保存结果到: {output_path}")
    try:
        with pd.ExcelWriter(str(output_path), engine='openpyxl') as writer:
            df = pd.DataFrame(results)
            if df.empty:
                logger.warning("没有结果数据可保存")
                return
            
            df.to_excel(writer, sheet_name='Complete Test Results', index=False)
            ws = writer.sheets['Complete Test Results']

            column_widths = {
                "A": 12,   # Question ID
                "B": 50,   # Question (English)
                "C": 40,   # Question (Chinese)
                "D": 10,   # Status
                "E": 120,  # Answer (English) 
                "F": 90,   # Answer (Chinese) 
                "G": 20    # Test Time
            }
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width
        
        logger.info(f"结果已成功保存到: {output_path}")
    except Exception as e:
        logger.error(f"保存Excel文件时出错: {str(e)}", exc_info=True)
        raise
    

    success_cnt = len([r for r in results if r["Status"] == "success"])
    fail_cnt = total - success_cnt
    success_rate = (success_cnt / total) * 100
    
    print(HEADER_SEPARATOR)
    print("[SUMMARY] Batch Test Completion")
    print(HEADER_SEPARATOR)
    print(f"Total Questions Tested: {total:2d}")
    print(f"Successfully Answered: {success_cnt:2d} ({success_rate:5.1f}%)")
    print(f"Failed to Answer:    {fail_cnt:2d} ({100-success_rate:5.1f}%)")
    print(f"Complete Results Saved To: {output_path}")
    print(HEADER_SEPARATOR + "\n")

if __name__ == "__main__":
    try:
        logger.info("=" * 80)
        logger.info("开始微调模型测试")
        logger.info(f"模型: {CONFIG['model_name']}")
        logger.info(f"API地址: {CONFIG['openai_api_base']}")
        logger.info(f"最大Token数: {MAX_TOKENS}")
        logger.info(f"重试次数: {RETRY_TIMES}")
        logger.info("=" * 80)
        
        batch_test_and_summary(test_questions)
        
        logger.info("=" * 80)
        logger.info("测试完成")
        logger.info("=" * 80)
        
    except KeyboardInterrupt:
        logger.warning("用户中断测试")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        sys.exit(1)