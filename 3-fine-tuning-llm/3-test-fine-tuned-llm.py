from openai import OpenAI
import pandas as pd
from datetime import datetime
import os
import time

openai_api_key = "ollama"
openai_api_base = "http://43.156.36.231:80/v1"


client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)


MAX_TOKENS = 600
RETRY_TIMES = 1
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

def get_medical_response(question_en, question_cn, retry=0):
    full_question = f"{question_en}（{question_cn}）"
    try:
        response = client.chat.completions.create(
            model="/workspace/qwen25-14b-offical-finetuned-bnb-4bit",
            messages=[
                {
                    "role": "assistant",
                    "content": "You are a professional medical consultant specializing in abnormal physical exams. "
                              "STRICT RULES: "
                              "1. English Answer: 3-4 key points (causes + core suggestions + precautions), no redundancy, complete sentences. "
                              "2. Separator: '---Chinese Version---' (exact wording). "
                              "3. Chinese Answer: Accurate translation of English, concise, complete, no extra content. "
                              "4. Ensure completeness within {MAX_TOKENS} tokens, no truncated sentences."
                },
                {"role": "user", "content": full_question}
            ],
            stream=False,
            temperature=0.6,
            max_tokens=MAX_TOKENS,
        )
        answer = response.choices[0].message.content.strip()
        separator = "---Chinese Version---"
        
        if separator in answer:
            en_part, cn_part = answer.split(separator, 1)
            en_part = en_part.strip()
            cn_part = cn_part.strip()
        else:
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
       
        cn_part = clean_irrelevant_content(cn_part)
        en_part = en_part if en_part else "No valid English answer provided"
        
        if not any(k in en_part.lower() for k in ["cause", "suggest", "recommend", "note", "step"]):
            en_part += " Core recommendations: Consult a healthcare provider for personalized evaluation and follow-up."
        if not any(k in cn_part for k in ["原因", "建议", "推荐", "注意", "步骤"]):
            cn_part += " 核心建议：咨询医疗专业人员进行个性化评估和随访。"
        
        return {
            "status": "success",
            "english_answer": en_part,
            "chinese_answer": cn_part
        }
    except Exception as e:
        error_msg = str(e)[:100]
        if retry < RETRY_TIMES:
            print(f"{INDENT}[Retry {retry+1}/{RETRY_TIMES}] Retrying due to error: {error_msg[:50]}...")
            time.sleep(1)
            return get_medical_response(question_en, question_cn, retry+1)
        return {
            "status": "failed",
            "english_answer": f"Failed after {RETRY_TIMES+1} attempts: {error_msg}",
            "chinese_answer": f"经{RETRY_TIMES+1}次尝试失败：{error_msg}"
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
    

    # Use absolute path based on current script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "medical_test_results")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"medical_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    output_path = os.path.join(output_dir, filename)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df = pd.DataFrame(results)
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
    batch_test_and_summary(test_questions)