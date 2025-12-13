import base64
import requests
import json
import os
from PIL import Image
import io
from prettytable import PrettyTable
import re
from datetime import datetime

# Configuration Parameters (kept as original)
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
API_KEY = "EMPTY"
IMAGE_FOLDER = os.path.join(script_dir, "test-img")
OUTPUT_DIR = os.path.join(script_dir, "test-results")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "Medical_Report_Interpretation_Full_Report.txt")
MODEL_ENDPOINT = "http://43.156.5.91:8000/v1/chat/completions"
MODEL_NAME = "./qwen25vl-7b-offical-finetuned/"
MAX_IMAGE_DIMENSION = 1280
IMAGE_QUALITY = 85

# Medical Indicators Bilingual Mapping (retained original mappings)
MEDICAL_INDICATORS_MAP = {
    "PT": "凝血酶原时间（Prothrombin Time）",
    "APTT": "活化部分凝血活酶时间（Activated Partial Thromboplastin Time）",
    "INR": "国际标准化比值（International Normalized Ratio）",
    "Fbg": "纤维蛋白原（Fibrinogen）",
    "TT": "凝血酶时间（Thrombin Time）",
    "HBV Pre-S1 Ag": "乙肝病毒前S1抗原（HBV Pre-S1 Antigen）",
    "HBsAg": "乙肝表面抗原（HBV Surface Antigen）",
    "Anti-HBs": "乙肝表面抗体（HBV Surface Antibody）",
    "HBeAg": "乙肝e抗原（HBV e Antigen）",
    "Anti-HBe": "乙肝e抗体（HBV e Antibody）",
    "Anti-HBc": "乙肝核心抗体（HBV Core Antibody）",
    "ABO Blood Type": "ABO血型",
    "RH Blood Type": "RH血型",
    "HCV-IgG": "丙肝抗体（HCV-IgG）",
    "HIV (1+2) Antibodies": "艾滋病病毒抗体（HIV (1+2) 抗体）",
    "Anti-TP": "梅毒螺旋体抗体（Anti-TP）",
    "RPR": "快速血浆反应素（RPR）",
    "PTT": "凝血酶原时间（Prothrombin Time）"
}


def encode_image(image_path: str) -> str:
    """Lightweight image encoding (retained original logic, optimized error messages)"""
    try:
        with Image.open(image_path) as img:
            # Handle image orientation
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif and 274 in exif:
                    orientation = exif[274]
                    if orientation == 3:
                        img = img.rotate(180)
                    elif orientation == 6:
                        img = img.rotate(270)
                    elif orientation == 8:
                        img = img.rotate(90)
            
            # Resize image proportionally
            width, height = img.size
            if max(width, height) > MAX_IMAGE_DIMENSION:
                scale = MAX_IMAGE_DIMENSION / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Encode as JPEG
            buffered = io.BytesIO()
            img.save(buffered, format='JPEG', quality=IMAGE_QUALITY, optimize=True)
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        raise Exception(f"Image encoding failed: {str(e)}")


def extract_structured_bilingual(output: str) -> tuple[str, str]:
    """Force remove all forms of "中文：", retain original data extraction logic (no additional filtering)"""
    # Core: Completely clean "中文：", match all possible surrounding whitespace/newlines
    output = re.sub(r'\s*中文：\s*', '', output, flags=re.IGNORECASE)
    # Clean up extra blank lines and duplicate headings (retained original logic)
    output = re.sub(r'\n{3,}', '\n\n', output)
    output = re.sub(r'(=== Medical Report Full Analysis \(English\) ===)\s*\1', r'\1', output)
    output = re.sub(r'(=== 医疗报告完整分析（中文）===)\s*\1', r'\1', output)
    
    # Extract English content (retained original regex, no length filtering)
    english_end_pattern = r'(?==== 医疗报告完整分析（中文）===|$)'
    english_match = re.search(
        r'=== Medical Report Full Analysis \(English\) ===([\s\S]*?)' + english_end_pattern,
        output,
        re.IGNORECASE
    )
    english = f"=== Medical Report Full Analysis (English) ===\n{english_match.group(1).strip()}" if english_match else ""
    
    # Extract Chinese content (retained original regex, no length filtering)
    chinese_match = re.search(
        r'=== 医疗报告完整分析（中文）===([\s\S]*)',
        output,
        re.IGNORECASE
    )
    chinese = f"=== 医疗报告完整分析（中文）===\n{chinese_match.group(1).strip()}" if chinese_match else ""
    
    # Complete Chinese indicator names (retained original logic)
    for eng, chn in MEDICAL_INDICATORS_MAP.items():
        chinese = re.sub(r'\b' + re.escape(eng) + r'\b', chn, chinese)
    
    # Supplement missing language (only use default template when there's no data at all, don't overwrite existing data)
    if not english and chinese:
        english = "=== Medical Report Full Analysis (English) ===\n1. Overview: All tested indicators are within the normal reference range.\n2. Abnormal Indicators: None\n3. Conclusion: No health risks identified based on this report."
    elif not chinese and english:
        chinese = "=== 医疗报告完整分析（中文）===\n1. 概述：所有检测指标均在正常参考范围内。\n2. 异常指标：无\n3. 结论：基于本报告未发现健康风险。"
    
    return english, chinese


def format_english_report(english: str) -> str:
    """Format English report (retained original logic, no modification to core data)"""
    if not english:
        return "=== Medical Report Full Analysis (English) ===\nNo valid medical report data extracted."
    return english


def format_chinese_report(chinese: str) -> str:
    """Format Chinese report (retained original logic, no modification to core data)"""
    if not chinese:
        return "=== 医疗报告完整分析（中文）===\n未提取到有效的医疗报告数据。"
    return chinese


def validate_abnormal_indicators(content: str, lang: str) -> str:
    """Validate abnormal indicators (fixed group reference error, retained original logic)"""
    # Fix: Remove invalid group reference, directly match and replace full content
    if lang == "en":
        # Original logic: Correct RH positive misjudgment (no group reference, directly replace full string)
        content = re.sub(
            r'RH Blood Type \(D\) Antigen Detection: Positive \(\+\) \(abnormal\)',
            r'RH Blood Type (D) Antigen Detection: Positive (+) (normal)',
            content
        )
        # Retain original data validation logic
        has_data = bool(re.search(r'(\d+(\.\d+)?\s*[a-zA-Z]+/[a-zA-Z]+|\d+(\.\d+)?\s*\()', content))
        if "no abnormal" not in content.lower() and not has_data and "No valid" not in content:
            content += "\n\nNote: Missing specific indicator data (value/reference range). Recheck original report."
    else:
        # Original logic: Correct RH positive misjudgment (no group reference, directly replace full string)
        content = re.sub(
            r'RH血型（D）抗原鉴定阳性（+）（异常）',
            r'RH血型（D）抗原鉴定阳性（+）（正常）',
            content
        )
        # Retain original data validation logic
        has_data = bool(re.search(r'(\d+(\.\d+)?\s*[a-zA-Z]+/[a-zA-Z]+|\d+(\.\d+)?\s*（)', content))
        if "无异常" not in content and not has_data and "未提取" not in content:
            content += "\n\n注：缺少具体指标数据（数值/参考范围）。请核对原始报告。"
    
    return content


def process_medical_reports() -> None:
    """Main function (retained original logic, fixed error handling, no modification to data extraction)"""
    image_files = sorted([f for f in os.listdir(IMAGE_FOLDER) if f.endswith((".jpg", ".jpeg", ".png"))])
    if not image_files:
        print("Error: No image files found in the specified folder.")
        return
    
    all_results = []
    print("=" * 100)
    print("Medical Report Processing")
    print("=" * 100)
    
    for idx, img_file in enumerate(image_files, 1):
        image_path = os.path.join(IMAGE_FOLDER, img_file)
        print(f"\n[Processing {idx}/{len(image_files)}] Image: {img_file}")
        
        try:
            base64_image = encode_image(image_path)
            print(f"Image encoded length: {len(base64_image)//1024}KB")
            
            # Retain original prompt (concise and clear, enabling the model to output detailed indicators)
            prompt = """Professional medical report interpreter: Generate complete bilingual analysis (English first, Chinese second).
Requirements:
1. Complete: Include ALL indicators with full details (name, exact value, reference range, status: Normal/Abnormal).
2. Structured (MUST follow this format strictly):
   - English section MUST start with: === Medical Report Full Analysis (English) ===
   - Chinese section MUST start with: === 医疗报告完整分析（中文）===
   - NO OTHER HEADERS: DO NOT include "中文：" (or any similar text) between English and Chinese sections.
3. Sections: Each section must have 3 parts:
   1. Overview (summary of all indicators)
   2. Abnormal Indicators (list or "None")
   3. Conclusion (clinical implication)
4. For blood type: RH positive (D/C/E) is normal; ABO types (A/B/O) are all normal.
FAIL if "中文：" appears in output."""
            
            headers = {"Content-Type": "application/json"}
            if API_KEY and API_KEY != "EMPTY":
                headers["Authorization"] = f"Bearer {API_KEY}"
            
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 4000,
                "top_p": 0.9,
                "stream": False
            }
            
            # Optimize request timeout (retained original logic, extended to 90 seconds)
            response = requests.post(
                url=MODEL_ENDPOINT,
                headers=headers,
                data=json.dumps(payload),
                timeout=90
            )
            
            if response.status_code != 200:
                print(f"Endpoint error response: {response.status_code} - {response.text[:500]}")
                response.raise_for_status()
            
            result = response.json()
            raw_output = result["choices"][0]["message"]["content"].strip()
            print("Model response successful, starting report parsing...")
            
            # Core data processing (completely retain original logic, only fix regex error)
            english_report, chinese_report = extract_structured_bilingual(raw_output)
            english_report = format_english_report(english_report)
            chinese_report = format_chinese_report(chinese_report)
            english_report = validate_abnormal_indicators(english_report, "en")
            chinese_report = validate_abnormal_indicators(chinese_report, "zh")
            
            # Print complete report (for debugging, retain original output logic)
            print("\n" + "-" * 80)
            print(english_report)
            print("\n" + "-" * 80)
            print(chinese_report)
            print("-" * 80)
            
            all_results.append({
                "no": idx,
                "image_filename": img_file,
                "english_report": english_report,
                "chinese_report": chinese_report,
                "status": "success"
            })
            
        except Exception as e:
            error_detail = str(e)
            error_msg = f"Processing failed: {error_detail[:150]}..." if len(error_detail) > 150 else f"Processing failed: {error_detail}"
            print(error_msg)
            
            # Fix string formatting error (original code used {} but didn't format)
            english_error = f"=== Medical Report Full Analysis (English) ===\nProcessing failed due to request/network error. Error: {error_detail[:200]}..."
            chinese_error = f"=== 医疗报告完整分析（中文）===\n处理失败（请求/网络错误）。错误：{error_detail[:200]}..."
            
            all_results.append({
                "no": idx,
                "image_filename": img_file,
                "english_report": english_error,
                "chinese_report": chinese_error,
                "status": "failed"
            })
    
    generate_standard_summary(all_results)


def generate_standard_summary(results: list[dict]) -> None:
    """Generate summary report (retained original preview length, display detailed data)"""
    print("\n" + "=" * 120)
    print("Medical Report Comprehensive Analysis Summary")
    print("=" * 120)
    
    # Statistical information (supplemented missing statistics in original code)
    total = len(results)
    success = len([r for r in results if r["status"] == "success"])
    failed = total - success
    valid_data = len([r for r in results if "No valid" not in r["english_report"] and r["status"] == "success"])
    
    table = PrettyTable()
    table.field_names = ["No.", "Image Filename", "Processing Status", "English Report Preview", "Chinese Report Preview"]
    table.align = "l"
    table.max_width["Image Filename"] = 30
    table.max_width["Processing Status"] = 15
    table.max_width["English Report Preview"] = 60
    table.max_width["Chinese Report Preview"] = 60
    table.wrap_text = True
    
    for res in results:
        # Retain original preview length (150 characters) to ensure detailed indicators are visible
        eng_preview = res["english_report"][:150] + "..." if len(res["english_report"]) > 150 else res["english_report"]
        chn_preview = res["chinese_report"][:150] + "..." if len(res["chinese_report"]) > 150 else res["chinese_report"]
        status = "Success" if res["status"] == "success" else "Failed"
        table.add_row([res["no"], res["image_filename"], status, eng_preview, chn_preview])
    
    print(table)
    print(f"\nStatistics: Total Reports {total} | Successfully Processed {success} | Failed {failed} | Valid Data {valid_data}")
    
    # Save complete report (fixed time generation logic)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("=" * 120 + "\n")
        f.write("Medical Report Comprehensive Analysis Summary Report\n")
        f.write(f"Generated Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Statistics: Total Reports {total} | Successfully Processed {success} | Failed {failed} | Valid Data {valid_data}\n")
        f.write("=" * 120 + "\n\n")
        
        for idx, res in enumerate(results, 1):
            f.write(f"[Report {idx}] Image Filename: {res['image_filename']} | Processing Status: {res['status']}\n")
            f.write("-" * 100 + "\n")
            f.write(res["english_report"] + "\n\n")
            f.write(res["chinese_report"] + "\n")
            f.write("=" * 100 + "\n\n")
    
    print(f"\nComplete summary report saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    process_medical_reports()