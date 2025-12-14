"""
医疗测试结果可视化脚本
优化版本：添加了配置管理、错误处理和日志记录
"""
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
import logging
from pathlib import Path
from glob import glob

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('medical_visualization.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# -------------------------- Basic Configuration --------------------------
# Configure font for English display (no Chinese font required)
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display issue
# Increase default font sizes
plt.rcParams['font.size'] = 14
plt.rcParams['axes.titlesize'] = 18
plt.rcParams['axes.labelsize'] = 16
plt.rcParams['xtick.labelsize'] = 14
plt.rcParams['ytick.labelsize'] = 14
plt.rcParams['legend.fontsize'] = 14
plt.rcParams['figure.titlesize'] = 20

# Color Configuration (Professional color scheme for medical domain)
COLORS = {
    "success": "#2E8B57",  # SeaGreen (Success)
    "fail": "#DC143C",  # Crimson (Failure)
    "reason": "#4169E1",  # RoyalBlue (Cause dimension)
    "suggest": "#FF6347",  # Tomato (Suggestion dimension)
    "note": "#32CD32",  # LimeGreen (Precautions dimension)
    "defect1": "#FF8C00",  # Orange (Missing precautions)
    "defect2": "#9370DB",  # MediumPurple (Incomplete cause explanation)
    "defect3": "#20B2AA",  # LightSeaGreen (CN-EN inconsistency)
}

# 配置参数（可通过环境变量覆盖）
script_dir = Path(__file__).parent

# 处理路径：环境变量返回字符串，需要正确转换为Path
def get_path_from_env(env_var, default_path):
    """从环境变量获取路径，如果不存在则使用默认路径"""
    env_value = os.getenv(env_var)
    if env_value:
        return Path(env_value)
    return default_path

CONFIG = {
    'excel_path': None,  # 初始化为None，稍后设置
    'excel_pattern': os.getenv('EXCEL_PATTERN', 'medical_test_results_*.xlsx'),
    'output_dir': get_path_from_env('OUTPUT_DIR', script_dir / "medical_visualization_charts"),
    'dpi': int(os.getenv('DPI', '300')),
}

# 处理Excel路径：如果环境变量设置了，使用它；否则稍后自动查找
excel_path_env = os.getenv('EXCEL_PATH')
if excel_path_env:
    CONFIG['excel_path'] = Path(excel_path_env)
    if not CONFIG['excel_path'].exists():
        logger.warning(f"环境变量指定的Excel文件不存在: {CONFIG['excel_path']}，将尝试自动查找")

# 自动查找Excel文件（如果未指定或指定的文件不存在）
if CONFIG['excel_path'] is None or not CONFIG['excel_path'].exists():
    excel_files = list(script_dir.glob(CONFIG['excel_pattern']))
    if excel_files:
        # 选择最新的文件
        try:
            CONFIG['excel_path'] = max(excel_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"自动找到Excel文件: {CONFIG['excel_path']}")
        except (OSError, ValueError) as e:
            logger.error(f"无法访问Excel文件: {str(e)}")
            raise FileNotFoundError(f"无法访问找到的Excel文件: {str(e)}")
    else:
        error_msg = f"未找到Excel文件（模式: {CONFIG['excel_pattern']}），请设置EXCEL_PATH环境变量或确保文件存在于: {script_dir}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

# 最终验证Excel文件存在
if CONFIG['excel_path'] is None or not CONFIG['excel_path'].exists():
    raise FileNotFoundError(f"Excel文件不存在: {CONFIG['excel_path']}")

# Chart output directory
CONFIG['output_dir'].mkdir(parents=True, exist_ok=True)
EXCEL_PATH = CONFIG['excel_path']
OUTPUT_DIR = CONFIG['output_dir']


# -------------------------- Data Preprocessing --------------------------
def load_and_preprocess_data(excel_path: Path):
    """
    Load Excel test results and preprocess data
    
    Args:
        excel_path: Path to the Excel file
    
    Returns:
        Dictionary containing processed data
    """
    try:
        logger.info(f"读取Excel文件: {excel_path}")
        if not excel_path.exists():
            raise FileNotFoundError(f"Excel文件不存在: {excel_path}")
        
        # Read Excel file
        try:
            df = pd.read_excel(str(excel_path), sheet_name="Complete Test Results")
            logger.info(f"成功读取 {len(df)} 条测试记录")
            
            # 验证必需的列是否存在
            required_columns = ["Question ID", "Status", "Answer (Chinese)", "Answer (English)"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Excel文件缺少必需的列: {', '.join(missing_columns)}")
            
            if df.empty:
                raise ValueError("Excel文件为空，没有测试记录")
                
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"读取Excel文件时出错: {str(e)}")
            raise ValueError(f"无法读取Excel文件: {str(e)}")

        # 1. Count test status (success/fail)
        status_counts = df["Status"].value_counts()

        # 2. Analyze key information completeness (cause, suggestion, precautions)
        def count_keywords(text, keywords):
            """Check if text contains any of the specified keywords"""
            return 1 if any(keyword in str(text).lower() for keyword in keywords) else 0

        # Define keywords for each dimension
        keyword_map = {
            "reason": ["原因", "cause", "因素", "factor"],  # Cause dimension (bilingual support)
            "suggest": ["建议", "推荐", "措施", "suggest", "recommend", "step", "measure"],  # Suggestion dimension
            "note": ["注意", "风险", "避免", "note", "precaution", "avoid", "risk"]  # Precautions dimension
        }

        # Count dimension coverage for each answer (combine Chinese and English)
        for dim, keywords in keyword_map.items():
            df[f"has_{dim}"] = df.apply(
                lambda row: count_keywords(str(row["Answer (Chinese)"]) + str(row["Answer (English)"]), keywords),
                axis=1
            )

        # 3. Analyze CN-EN consistency (whether dimensions exist in both languages)
        df["consistent_reason"] = df["has_reason"]  # Considered consistent if present in either language
        df["consistent_suggest"] = df["has_suggest"]
        df["consistent_note"] = df["has_note"]

        # 4. Classify defect types (based on missing dimensions)
        def classify_defect(row):
            """Classify defect types based on answer quality"""
            defects = []
            try:
                # 安全地获取值，处理可能的NaN
                has_note = int(row.get("has_note", 0) or 0)
                has_reason = int(row.get("has_reason", 0) or 0)
                answer_cn = str(row.get("Answer (Chinese)", "") or "")
                answer_en = str(row.get("Answer (English)", "") or "")
                
                if has_note == 0:
                    defects.append("Missing Precautions")
                if has_reason == 1 and len([k for k in keyword_map["reason"] if k in answer_cn]) < 2:
                    defects.append("Incomplete Cause Explanation")
                # Check if cause dimension exists in English but not in Chinese (simplified consistency check)
                en_has_reason = any(k in answer_en.lower() for k in keyword_map["reason"][1:])
                if has_reason != (1 if en_has_reason else 0):
                    defects.append("CN-EN Inconsistency")
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"处理行数据时出错: {str(e)}")
                defects.append("Data Processing Error")
            
            return defects if defects else ["No Significant Defects"]

        df["defects"] = df.apply(classify_defect, axis=1)

        # Expand defects list for statistics
        all_defects = []
        defect_question_ids = []
        for idx, row in df.iterrows():
            try:
                # 确保defects是列表类型
                defects = row["defects"] if isinstance(row["defects"], list) else [row["defects"]]
                question_id = row.get("Question ID", idx + 1)  # 使用索引+1作为后备
                
                for defect in defects:
                    if defect and defect != "No Significant Defects":
                        all_defects.append(defect)
                        defect_question_ids.append(question_id)
            except (KeyError, AttributeError) as e:
                logger.warning(f"处理第 {idx + 1} 行数据时出错: {str(e)}")
                continue

        return {
            "df": df,
            "status_counts": status_counts,
            "defect_counts": pd.Series(all_defects).value_counts(),
            "defect_question_counts": pd.Series(defect_question_ids).value_counts()
        }
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {excel_path}")
        raise
    except Exception as e:
        logger.error(f"读取或处理数据时出错: {str(e)}", exc_info=True)
        raise


# -------------------------- Chart Generation Functions --------------------------
def plot_status_distribution(status_counts, output_path):
    """Chart 1: Test Success Rate & Status Distribution (Pie + Bar Chart)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Pie chart: Status proportion
    labels = status_counts.index.tolist()
    sizes = status_counts.values.tolist()
    colors = [COLORS["success"] if label == "success" else COLORS["fail"] for label in labels]
    wedges, texts, autotexts = ax1.pie(sizes, labels=[f"{label}\n{size} items" for label, size in zip(labels, sizes)],
                                       colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 14})
    ax1.set_title("Model Test Status Distribution", fontsize=18, fontweight='bold', pad=20)

    # Bar chart: Success rate statistics
    success_rate = (status_counts.get("success", 0) / status_counts.sum()) * 100
    fail_rate = 100 - success_rate
    ax2.bar(["Success", "Failure"], [success_rate, fail_rate], color=[COLORS["success"], COLORS["fail"]], alpha=0.8)
    ax2.set_ylabel("Percentage (%)", fontsize=16)
    ax2.set_title("Model Test Success Rate", fontsize=18, fontweight='bold', pad=20)
    # Add value labels on top of bars
    for i, v in enumerate([success_rate, fail_rate]):
        ax2.text(i, v + 1, f"{v:.1f}%", ha='center', va='bottom', fontsize=15, fontweight='bold')
    ax2.set_ylim(0, 110)

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=CONFIG['dpi'], bbox_inches='tight')
    plt.close()
    logger.info(f"图表1已保存: {output_path}")


def plot_answer_completeness(df, output_path):
    """Chart 2: Key Information Completeness of Answers (Stacked Bar Chart)"""
    fig, ax = plt.subplots(figsize=(12, 7))

    # Extract dimension coverage data for each question
    # 确保数据存在且有效
    if df.empty:
        logger.warning("数据框为空，无法生成图表")
        return
    
    question_ids = df["Question ID"].tolist()
    reason_data = df["has_reason"].fillna(0).astype(int).tolist()
    suggest_data = df["has_suggest"].fillna(0).astype(int).tolist()
    note_data = df["has_note"].fillna(0).astype(int).tolist()

    # Stacked bar chart
    width = 0.6
    ax.bar(question_ids, reason_data, width, label="Contains Cause Analysis", color=COLORS["reason"], alpha=0.8)
    ax.bar(question_ids, suggest_data, width, bottom=reason_data, label="Contains Intervention Suggestions",
           color=COLORS["suggest"], alpha=0.8)
    ax.bar(question_ids, note_data, width, bottom=[r + s for r, s in zip(reason_data, suggest_data)],
           label="Contains Precautions", color=COLORS["note"], alpha=0.8)

    # Chart configuration
    ax.set_xlabel("Question ID", fontsize=16)
    ax.set_ylabel("Number of Covered Dimensions (0-3)", fontsize=16)
    ax.set_title("Key Information Completeness by Question", fontsize=18, fontweight='bold', pad=20)
    ax.set_xticks(question_ids)
    ax.set_ylim(0, 3.5)
    ax.tick_params(axis='x', labelsize=14)
    ax.tick_params(axis='y', labelsize=14)
    ax.legend(loc='upper right', fontsize=14)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=CONFIG['dpi'], bbox_inches='tight')
    plt.close()
    logger.info(f"图表2已保存: {output_path}")


def plot_cn_en_consistency(df, output_path):
    """Chart 3: CN-EN Answer Consistency (Heatmap)"""
    fig, ax = plt.subplots(figsize=(10, 8))

    # Build consistency matrix (Question ID × Dimension)
    if df.empty:
        logger.warning("数据框为空，无法生成一致性热图")
        return
    
    question_ids = df["Question ID"].tolist()
    dimensions = ["Cause Analysis", "Intervention Suggestions", "Precautions"]
    
    # 安全地构建一致性矩阵
    consistency_matrix = []
    for qid in question_ids:
        qid_df = df[df["Question ID"] == qid]
        if not qid_df.empty:
            consistency_matrix.append([
                int(qid_df["consistent_reason"].iloc[0] if pd.notna(qid_df["consistent_reason"].iloc[0]) else 0),
                int(qid_df["consistent_suggest"].iloc[0] if pd.notna(qid_df["consistent_suggest"].iloc[0]) else 0),
                int(qid_df["consistent_note"].iloc[0] if pd.notna(qid_df["consistent_note"].iloc[0]) else 0)
            ])
        else:
            # 如果找不到对应的Question ID，使用默认值
            consistency_matrix.append([0, 0, 0])
    
    if not consistency_matrix:
        logger.warning("无法构建一致性矩阵，数据可能有问题")
        return

    # Plot heatmap
    im = ax.imshow(consistency_matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

    # Set axis labels
    ax.set_xticks(range(len(dimensions)))
    ax.set_xticklabels(dimensions, fontsize=14)
    ax.set_yticks(range(len(question_ids)))
    ax.set_yticklabels([f"Q{qid}" for qid in question_ids], fontsize=14)

    # Add value labels (0/1) in each cell
    for i in range(len(question_ids)):
        for j in range(len(dimensions)):
            text = ax.text(j, i, consistency_matrix[i][j], ha="center", va="center",
                           color="white" if consistency_matrix[i][j] == 1 else "black", fontweight='bold', fontsize=14)

    # Add color bar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Consistency (1=Matched, 0=Missing)", fontsize=14)
    cbar.ax.tick_params(labelsize=14)

    ax.set_title("CN-EN Answer Dimension Consistency Heatmap", fontsize=18, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=CONFIG['dpi'], bbox_inches='tight')
    plt.close()
    logger.info(f"图表3已保存: {output_path}")


def plot_defect_analysis(defect_counts, defect_question_counts, output_path):
    """Chart 4: Defect Type Statistics & Priority Optimization Questions (Pie + Bar Chart)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Pie chart: Defect type proportion
    if not defect_counts.empty:
        labels = defect_counts.index.tolist()
        sizes = defect_counts.values.tolist()
        colors = [COLORS["defect1"], COLORS["defect2"], COLORS["defect3"]][:len(labels)]
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 14})
        ax1.set_title("Answer Defect Type Distribution", fontsize=18, fontweight='bold', pad=20)
    else:
        ax1.text(0.5, 0.5, "No Significant Defects", ha='center', va='center', transform=ax1.transAxes, fontsize=16)
        ax1.set_title("Answer Defect Type Distribution", fontsize=18, fontweight='bold', pad=20)

    # Bar chart: Top 3 defect-prone questions
    if not defect_question_counts.empty:
        top3_defect_questions = defect_question_counts.nlargest(3)
        ax2.barh([f"Q{qid}" for qid in top3_defect_questions.index],
                 top3_defect_questions.values, color=COLORS["defect1"], alpha=0.8)
        ax2.set_xlabel("Number of Defects", fontsize=16)
        ax2.set_title("Top 3 Defect-Prone Questions", fontsize=18, fontweight='bold', pad=20)
        ax2.tick_params(axis='x', labelsize=14)
        ax2.tick_params(axis='y', labelsize=14)
        # Add value labels
        for i, v in enumerate(top3_defect_questions.values):
            ax2.text(v + 0.05, i, str(v), ha='left', va='center', fontweight='bold', fontsize=15)
    else:
        ax2.text(0.5, 0.5, "No Defective Questions", ha='center', va='center', transform=ax2.transAxes, fontsize=16)
        ax2.set_title("Top 3 Defect-Prone Questions", fontsize=18, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=CONFIG['dpi'], bbox_inches='tight')
    plt.close()
    logger.info(f"图表4已保存: {output_path}")


# -------------------------- Main Execution Function --------------------------
def generate_all_charts():
    """Generate all 4 core visualization charts"""
    try:
        logger.info("=" * 80)
        logger.info("开始生成可视化图表")
        logger.info("=" * 80)
        
        # 1. Data preprocessing
        data = load_and_preprocess_data(EXCEL_PATH)
        
        if not data or "df" not in data or data["df"].empty:
            logger.error("数据预处理失败或数据为空")
            raise ValueError("无法生成图表：数据为空")

        # 2. Generate all charts
        try:
            plot_status_distribution(
                data["status_counts"],
                OUTPUT_DIR / "1_Model_Test_Status_and_Success_Rate.png"
            )
        except Exception as e:
            logger.error(f"生成图表1时出错: {str(e)}", exc_info=True)

        try:
            plot_answer_completeness(
                data["df"],
                OUTPUT_DIR / "2_Answer_Key_Information_Completeness.png"
            )
        except Exception as e:
            logger.error(f"生成图表2时出错: {str(e)}", exc_info=True)

        try:
            plot_cn_en_consistency(
                data["df"],
                OUTPUT_DIR / "3_CN-EN_Answer_Consistency_Heatmap.png"
            )
        except Exception as e:
            logger.error(f"生成图表3时出错: {str(e)}", exc_info=True)

        try:
            plot_defect_analysis(
                data["defect_counts"],
                data["defect_question_counts"],
                OUTPUT_DIR / "4_Defect_Type_and_Priority_Optimization.png"
            )
        except Exception as e:
            logger.error(f"生成图表4时出错: {str(e)}", exc_info=True)

        logger.info("=" * 80)
        logger.info("所有图表生成完成!")
        logger.info(f"保存目录: {OUTPUT_DIR}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"生成图表过程中发生错误: {str(e)}", exc_info=True)
        raise


# -------------------------- Execution Entry --------------------------
if __name__ == "__main__":
    try:
        generate_all_charts()
    except KeyboardInterrupt:
        logger.warning("用户中断程序")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}", exc_info=True)
        sys.exit(1)